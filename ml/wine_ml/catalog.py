"""Map catalog positions (CSV dump) to their reference photos in the Strapi uploads.

The CSV dump stores the *original* photo file name, while the Strapi uploads
directory stores files as ``<transliterated name>_<hash10>.<ext>`` (plus derived
``thumbnail_/small_/medium_/large_`` copies). Both sides are reduced to a
normalized key; several transliteration conventions coexist in the uploads
(``belyj``/``belyy``, ``Lvicza``, ``ovoshhi``/``schastya``, ``sukhoe``), so the
key also canonicalizes those spellings.

Resolution per wine (recorded in ``mapping``):
- ``exact``          - one file (or byte-identical copies) under the key;
- ``fuzzy``          - no exact key; one clearly closest key (typo, different spelling);
- ``product_shot``   - a generic name (``Screenshot_7``) reused by unrelated uploads
                       (banners, event photos): the single bottle-on-white image wins;
- ``newest_reupload``- several look-alike product shots (the same bottle uploaded
                       again): the newest file wins;
- ``shared_photo``   - one photo named for several wines: indexed for each of them
                       (they become catalog "twins" and are reported separately).
Everything else goes to ``excluded`` with a reason.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

CSV_FIELDS = {
    "name": "Название вина",
    "category": "Категория",
    "color": "Цвет",
    "region": "Регион",
    "grapes": "Сорт винограда",
    "description": "Описание",
    "winery": "Винодельня",
}
SLUG_FIELD = "Slug"
PHOTO_FIELD = "Название фото"

DERIVED_PREFIXES = ("thumbnail_", "small_", "medium_", "large_")
IMAGE_EXTS = {".webp", ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"}

_TRANSLIT = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p",
     "r", "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"],
))
# Spelling variants seen in the uploads -> one canonical form (applied to both sides)
_CANON = [("shh", "sch"), ("kh", "h"), ("x", "h"), ("cz", "ts"), ("j", "y"), ("yo", "e")]
_HASH_SUFFIX = re.compile(r"_[0-9a-f]{10}$")

FUZZY_MIN, FUZZY_GAP = 0.9, 0.05       # accept a fuzzy key only if it is close and clearly the best
PRODUCT_BORDER_WHITE = 0.85            # share of near-white border pixels in a product shot
REUPLOAD_MAX_DIFF = 25.0               # mean abs difference of thumbnails for "same bottle" uploads


def name_key(stem: str) -> str:
    """Case-, separator-, alphabet- and transliteration-insensitive key of a file stem."""
    s = re.sub(r"[^a-z0-9]", "", "".join(_TRANSLIT.get(c, c) for c in stem.lower()))
    for a, b in _CANON:
        s = s.replace(a, b)
    return s


def strip_hash(stem: str) -> str:
    """Remove Strapi's ``_<hash10>`` suffix (it can be applied more than once)."""
    while _HASH_SUFFIX.search(stem):
        stem = _HASH_SUFFIX.sub("", stem)
    return stem


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _on_white(path: Path, max_side: int = 96) -> Image.Image:
    with Image.open(path) as im:
        im = im.convert("RGBA")
        im.thumbnail((max_side, max_side))
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.getchannel("A"))
        return bg


def is_product_shot(path: Path) -> bool:
    """Bottle-on-white/transparent studio shot (not a banner or an event photo)."""
    try:
        im = _on_white(path)
    except OSError:
        return False
    if im.width > 1.6 * im.height:  # wide banners
        return False
    a = np.asarray(im)
    border = np.concatenate([a[:2].reshape(-1, 3), a[-2:].reshape(-1, 3),
                             a[:, :2].reshape(-1, 3), a[:, -2:].reshape(-1, 3)])
    return float((border.min(axis=1) > 225).mean()) >= PRODUCT_BORDER_WHITE


def _look_alike(paths: list[Path]) -> bool:
    thumbs = []
    for p in paths:
        im = _on_white(p).convert("L")
        thumbs.append(np.asarray(im.resize((32, 64)), dtype=np.float32))
    return all(np.abs(t - thumbs[0]).mean() < REUPLOAD_MAX_DIFF for t in thumbs[1:])


def index_uploads(files: list[Path]) -> dict[str, list[Path]]:
    idx: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        if f.name.startswith(DERIVED_PREFIXES) or f.suffix.lower() not in IMAGE_EXTS:
            continue
        key = name_key(strip_hash(f.stem))
        if key:
            idx[key].append(f)
    return idx


def _fuzzy_key(key: str, keys: list[str]) -> str | None:
    from wine_ml.text_match import fuzzy_sim

    scored = sorted(((fuzzy_sim(key, k), k) for k in keys), reverse=True)[:2]
    if not scored or scored[0][0] < FUZZY_MIN:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < FUZZY_GAP:
        return None
    return scored[0][1]


def resolve_file(candidates: list[Path]) -> tuple[Path | None, str]:
    """(file, method) for the upload files found under one photo name; (None, '') if unresolved."""
    if not candidates:
        return None, ""
    if len(candidates) == 1 or len({_file_digest(c) for c in candidates}) == 1:
        return sorted(candidates)[0], "exact"
    products = [c for c in candidates if is_product_shot(c)]
    if len(products) == 1:
        return products[0], "product_shot"
    if len(products) > 1 and _look_alike(products):
        return max(products, key=lambda p: (p.stat().st_mtime, p.name)), "newest_reupload"
    return None, ""


def build_catalog(rows: list[dict], upload_files: list[Path]) -> tuple[list[dict], list[dict]]:
    """Return (wines, excluded).

    wines: one dict per resolved slug with catalog fields, ``src_file`` and ``mapping``.
    excluded: ``{slug, photo, reason}``; reason is ``file_not_found`` | ``ambiguous_file``.
    """
    by_slug: dict[str, dict] = {}
    for r in rows:
        slug = r[SLUG_FIELD].strip()
        if slug and slug not in by_slug:
            by_slug[slug] = r

    slugs_by_photo: dict[str, set[str]] = defaultdict(set)
    for slug, r in by_slug.items():
        slugs_by_photo[r[PHOTO_FIELD].strip()].add(slug)

    idx = index_uploads(upload_files)
    keys = list(idx)
    wines, excluded = [], []
    for slug, r in sorted(by_slug.items()):
        photo = r[PHOTO_FIELD].strip()
        key = name_key(photo.rsplit(".", 1)[0] if "." in photo else photo)
        candidates, via_fuzzy = (idx.get(key, []) if key else []), False
        if key and not candidates:
            fk = _fuzzy_key(key, keys)
            candidates, via_fuzzy = (idx[fk], True) if fk else ([], False)
        if not candidates:
            excluded.append({"slug": slug, "photo": photo, "reason": "file_not_found"})
            continue
        src, method = resolve_file(candidates)
        if src is None:
            excluded.append({"slug": slug, "photo": photo, "reason": "ambiguous_file"})
            continue
        if len(slugs_by_photo[photo]) > 1:
            method = "shared_photo"
        elif via_fuzzy and method == "exact":
            method = "fuzzy"
        wine = {k: (r.get(col) or "").strip() or None for k, col in CSV_FIELDS.items()}
        wine["name"] = wine["name"] or slug
        wine.update(slug=slug, src_file=src, mapping=method)
        wines.append(wine)
    return wines, excluded

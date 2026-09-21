"""Build the list of unambiguously mapped catalog positions.

The CSV dump stores the *original* photo file name, while the Strapi uploads
directory stores files as ``<slugified name>_<hash10>.<ext>`` (plus derived
``thumbnail_/small_/medium_/large_`` copies). We match both sides on a
normalized key and keep only positions where the mapping is unique.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path

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
_HASH_SUFFIX = re.compile(r"_[0-9a-f]{10}$")


def name_key(stem: str) -> str:
    """Case-, separator- and alphabet-insensitive key of a file stem."""
    s = "".join(_TRANSLIT.get(c, c) for c in stem.lower())
    return re.sub(r"[^a-z0-9]", "", s)


def strip_hash(stem: str) -> str:
    """Remove Strapi's ``_<hash10>`` suffix (it can be applied more than once)."""
    while _HASH_SUFFIX.search(stem):
        stem = _HASH_SUFFIX.sub("", stem)
    return stem


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_uploads(files: list[Path]) -> dict[str, list[Path]]:
    idx: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        if f.name.startswith(DERIVED_PREFIXES) or f.suffix.lower() not in IMAGE_EXTS:
            continue
        key = name_key(strip_hash(f.stem))
        if key:
            idx[key].append(f)
    return idx


def build_catalog(rows: list[dict], upload_files: list[Path]) -> tuple[list[dict], list[dict]]:
    """Return (wines, excluded).

    wines: one dict per unambiguous slug with catalog fields and ``src_file``.
    excluded: ``{slug, photo, reason}``; reason is one of
    ``shared_photo`` | ``file_not_found`` | ``ambiguous_file``.
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
    wines, excluded = [], []
    for slug, r in sorted(by_slug.items()):
        photo = r[PHOTO_FIELD].strip()
        if len(slugs_by_photo[photo]) > 1:
            excluded.append({"slug": slug, "photo": photo, "reason": "shared_photo"})
            continue
        stem = photo.rsplit(".", 1)[0] if "." in photo else photo
        candidates = idx.get(name_key(stem), []) if name_key(stem) else []
        if not candidates:
            excluded.append({"slug": slug, "photo": photo, "reason": "file_not_found"})
            continue
        if len(candidates) > 1 and len({_file_digest(c) for c in candidates}) > 1:
            excluded.append({"slug": slug, "photo": photo, "reason": "ambiguous_file"})
            continue
        wine = {k: (r.get(col) or "").strip() or None for k, col in CSV_FIELDS.items()}
        wine["name"] = wine["name"] or slug
        wine.update(slug=slug, src_file=sorted(candidates)[0])
        wines.append(wine)
    return wines, excluded

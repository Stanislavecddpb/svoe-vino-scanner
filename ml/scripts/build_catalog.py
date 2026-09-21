"""CSV dump + Strapi uploads -> data/catalog/{wines.jsonl, excluded.csv, images/}.

Usage:
  python ml/scripts/build_catalog.py \
      --csv data/raw/strapi_output0709.csv \
      --uploads data/raw/strapi/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads \
      --out data/catalog
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image

from wine_ml.catalog import build_catalog


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=Path("data/raw/strapi_output0709.csv"))
    ap.add_argument("--uploads", type=Path, default=Path(
        "data/raw/strapi/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads"))
    ap.add_argument("--out", type=Path, default=Path("data/catalog"))
    args = ap.parse_args()

    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    files = [p for p in args.uploads.iterdir() if p.is_file()]
    wines, excluded = build_catalog(rows, files)

    images_dir = args.out / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    kept = []
    for w in wines:
        src: Path = w.pop("src_file")
        try:
            with Image.open(src) as im:
                im.verify()
        except Exception:
            excluded.append({"slug": w["slug"], "photo": src.name, "reason": "unreadable_image"})
            continue
        dst = images_dir / f"{w['slug']}{src.suffix.lower()}"
        if not dst.exists():
            shutil.copy2(src, dst)
        w["image_file"] = dst.name
        w["source_upload"] = src.name
        kept.append(w)

    with (args.out / "wines.jsonl").open("w", encoding="utf-8") as f:
        for w in kept:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    with (args.out / "excluded.csv").open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["slug", "photo", "reason"])
        wr.writeheader()
        wr.writerows(sorted(excluded, key=lambda e: (e["reason"], e["slug"])))

    print(f"csv rows: {len(rows)}, unique slugs: {len(kept) + len(excluded)}")
    print(f"kept: {len(kept)}")
    print("excluded:", dict(Counter(e["reason"] for e in excluded)))


if __name__ == "__main__":
    main()

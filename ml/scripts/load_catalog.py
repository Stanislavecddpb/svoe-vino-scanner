"""data/catalog/wines.jsonl -> wines table (upsert; removes wines no longer in the catalog).

Usage: python ml/scripts/load_catalog.py [--catalog data/catalog]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from wine_ml.db import connect, delete_wines_not_in, upsert_wines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    args = ap.parse_args()
    wines = [json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")]
    with connect() as conn:
        upsert_wines(conn, wines)
        removed = delete_wines_not_in(conn, [w["slug"] for w in wines])
    print(f"upserted {len(wines)} wines, removed {removed} stale")


if __name__ == "__main__":
    main()

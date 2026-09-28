"""Precompute "Аналоги из других виноделен" for every catalog wine -> table wine_analogs.

Usage: python ml/scripts/build_analogs.py [--k 8]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from tqdm import tqdm

from wine_ml.analogs import AnalogFinder
from wine_ml.db import connect


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()

    wines = [json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")]
    t0 = time.perf_counter()
    finder = AnalogFinder(wines)
    rows = []
    for w in tqdm(wines, unit="wine"):
        for rank, a in enumerate(finder.analogs(w["slug"], args.k), start=1):
            rows.append((w["slug"], rank, a["slug"], a["score"], a["reason"]))
    with connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM wine_analogs")
        cur.executemany("INSERT INTO wine_analogs (slug, rank, analog_slug, score, reason) VALUES (%s, %s, %s, %s, %s)", rows)
        conn.commit()
    no_analogs = len(wines) - len({r[0] for r in rows})
    print(f"{len(rows)} analogs for {len(wines)} wines in {time.perf_counter() - t0:.0f}s; wines without analogs: {no_analogs}")


if __name__ == "__main__":
    main()

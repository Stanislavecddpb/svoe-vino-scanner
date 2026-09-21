"""List catalog twins (different wines with the same reference photo) -> data/catalog/twins.csv.

Uses the 'full' view embeddings already in the index.
Usage: python ml/scripts/find_twins.py [--threshold 0.99]
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from wine_ml.config import MODEL_NAME
from wine_ml.db import connect, fetch_embeddings
from wine_ml.twins import TWIN_THRESHOLD, twin_groups


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--threshold", type=float, default=TWIN_THRESHOLD)
    args = ap.parse_args()

    wines = {json.loads(l)["slug"]: json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")}
    with connect() as conn:
        slugs, vecs = fetch_embeddings(conn, args.model, ["full"])
    pos = {s: i for i, s in enumerate(slugs)}
    groups = twin_groups(slugs, vecs, args.threshold)

    out = args.catalog / "twins.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["group", "slug", "name", "winery", "category", "color", "max_cos"])
        for g, members in enumerate(groups, start=1):
            idx = [pos[s] for s in members]
            sim = vecs[idx] @ vecs[idx].T
            np.fill_diagonal(sim, -1)
            for s, row in zip(members, sim):
                w = wines.get(s, {})
                wr.writerow([g, s, w.get("name"), w.get("winery"), w.get("category"), w.get("color"), f"{row.max():.4f}"])
    n = sum(len(g) for g in groups)
    print(f"{len(groups)} twin groups, {n} wines (cos >= {args.threshold}) -> {out}")


if __name__ == "__main__":
    main()

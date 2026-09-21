"""Offline accuracy evaluation against the pgvector index.

Synthetic mode (default): each indexed reference image is turned into
``--n-aug`` synthetic field photos (wine_ml.augment) and searched against the
full index. This is a stand-in until labeled field photos exist; numbers are
indicative, not the real accuracy.

Labeled mode: ``--labels file.tsv --images-dir DIR`` with rows
``image_path<TAB>slug`` (header optional) evaluates real photos.

Search math is identical to the web VectorEngine (cosine on L2-normalized
vectors), done in numpy to avoid a round trip per query.

Usage:
  python ml/scripts/evaluate.py --n-aug 2
  python ml/scripts/evaluate.py --labels labels.tsv --images-dir photos/
"""
from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

from wine_ml.augment import field_like
from wine_ml.config import DEVICE, MODEL_NAME
from wine_ml.db import connect, fetch_embeddings
from wine_ml.embedder import Embedder
from wine_ml.preprocess import normalize_image

HARD_THRESHOLD = 0.9  # reference whose nearest *other* reference is this similar = near-duplicate


def load_queries(args, slugs: list[str], catalog: Path) -> list[tuple[str, callable]]:
    """List of (true_slug, loader) pairs; loader returns the raw query PIL image."""
    if args.labels:
        out = []
        for line in args.labels.read_text(encoding="utf-8").splitlines():
            parts = line.rstrip("\r").split("\t")
            if len(parts) < 2 or parts[0] in ("image_path", "query_id"):
                continue
            path, slug = parts[0], parts[-1]
            out.append((slug, lambda p=args.images_dir / path: Image.open(p)))
        return out

    wines = {json.loads(l)["slug"]: json.loads(l) for l in (catalog / "wines.jsonl").open(encoding="utf-8")}
    rng = random.Random(args.seed)
    chosen = sorted(slugs)
    if args.limit:
        chosen = rng.sample(chosen, min(args.limit, len(chosen)))
    out = []
    for slug in chosen:
        path = catalog / "images" / wines[slug]["image_file"]
        for k in range(args.n_aug):
            seed = rng.randint(0, 2**31)
            out.append((slug, lambda p=path, s=seed: field_like(Image.open(p), random.Random(s))))
    return out


def summarize(rows: list[dict], hard: set[str], margin_thr: float) -> dict:
    def block(rs: list[dict]) -> dict:
        if not rs:
            return {"n": 0}
        top1 = np.mean([r["rank"] == 1 for r in rs])
        top5 = np.mean([1 <= r["rank"] <= 5 for r in rs])
        correct = [r for r in rs if r["rank"] == 1]
        confident = [r for r in rs if r["margin"] >= margin_thr]
        return {
            "n": len(rs),
            "top1": round(float(top1), 4),
            "top5": round(float(top5), 4),
            "mean_margin_correct": round(float(np.mean([r["margin"] for r in correct])), 4) if correct else None,
            "mean_top1_score": round(float(np.mean([r["score1"] for r in rs])), 4),
            "confident_share": round(len(confident) / len(rs), 4),
            "confident_top1": round(float(np.mean([r["rank"] == 1 for r in confident])), 4) if confident else None,
        }

    return {
        "all": block(rows),
        "near_duplicates": block([r for r in rows if r["slug"] in hard]),
        "distinct": block([r for r in rows if r["slug"] not in hard]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--device", default=DEVICE)
    ap.add_argument("--n-aug", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0, help="evaluate a random subset of wines")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--margin", type=float, default=0.03, help="confidence margin threshold")
    ap.add_argument("--labels", type=Path)
    ap.add_argument("--images-dir", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("reports"))
    args = ap.parse_args()

    with connect() as conn:
        slugs, index = fetch_embeddings(conn, args.model)
    if not slugs:
        raise SystemExit(f"index is empty for model {args.model}; run build_index.py first")
    slug_pos = {s: i for i, s in enumerate(slugs)}

    sim = index @ index.T
    np.fill_diagonal(sim, -1)
    nearest_other = sim.max(axis=1)
    hard = {s for s, v in zip(slugs, nearest_other) if v >= HARD_THRESHOLD}

    queries = load_queries(args, slugs, args.catalog)
    queries = [(s, f) for s, f in queries if s in slug_pos]
    print(f"index: {len(slugs)} wines ({len(hard)} near-duplicates at cos>={HARD_THRESHOLD}); "
          f"queries: {len(queries)}")

    emb = Embedder(args.model, args.device)
    rows, t_embed = [], 0.0
    for i in tqdm(range(0, len(queries), args.batch), unit="batch"):
        chunk = queries[i:i + args.batch]
        images = [normalize_image(load()) for _, load in chunk]
        t0 = time.perf_counter()
        q = emb.embed(images, batch_size=args.batch)
        t_embed += time.perf_counter() - t0
        scores = q @ index.T
        order = np.argsort(-scores, axis=1)
        for (slug, _), sc, od in zip(chunk, scores, order):
            rank = int(np.where(od == slug_pos[slug])[0][0]) + 1
            rows.append({"slug": slug, "rank": rank, "pred": slugs[od[0]],
                         "score1": float(sc[od[0]]), "margin": float(sc[od[0]] - sc[od[1]]),
                         "top5": [slugs[j] for j in od[:5]]})

    report = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "mode": "labeled" if args.labels else f"synthetic x{args.n_aug}",
        "index_size": len(slugs),
        "near_duplicate_refs": len(hard),
        "margin_threshold": args.margin,
        "embed_ms_per_image": round(1000 * t_embed / max(len(rows), 1), 1),
        "metrics": summarize(rows, hard, args.margin),
        "errors_sample": [r for r in rows if r["rank"] != 1][:50],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    tag = args.model.split("/")[-1] + ("-labeled" if args.labels else "-synthetic")
    (args.out / f"eval-{tag}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    m = report["metrics"]
    lines = [f"# Eval: {args.model} ({report['mode']})", "",
             f"Index: {len(slugs)} wines, near-duplicate refs (cos≥{HARD_THRESHOLD}): {len(hard)}. "
             f"Embed: {report['embed_ms_per_image']} ms/img (batched).", "",
             "| subset | n | Top-1 | Top-5 | mean margin (correct) | confident share | Top-1 when confident |",
             "|---|---|---|---|---|---|---|"]
    for name, b in m.items():
        if b["n"]:
            lines.append(f"| {name} | {b['n']} | {b['top1']:.1%} | {b['top5']:.1%} | "
                         f"{b['mean_margin_correct']} | {b['confident_share']:.1%} | {b['confident_top1']} |")
    (args.out / f"eval-{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

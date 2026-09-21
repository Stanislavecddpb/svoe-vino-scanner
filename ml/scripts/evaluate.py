"""Offline accuracy evaluation against the pgvector index.

Synthetic mode (default): each indexed wine's reference image is turned into
``--n-aug`` synthetic field photos (wine_ml.augment) and searched against the
full index. This is a stand-in until labeled field photos exist; numbers are
indicative, not the real accuracy.

Labeled mode: ``--labels file.tsv --images-dir DIR`` with rows
``image_path<TAB>slug`` (header optional) evaluates real photos.

Search math matches the web VectorEngine: cosine on L2-normalized vectors,
a wine's score = (1 - w) * full + w * best label view (``--views``, ``--label-weight``).

Catalog twins (different wines with the same reference photo, see
wine_ml/twins.py) are reported separately and excluded from the main rows.

Query embeddings are cached in reports/cache/, so comparing index variants
(e.g. ``--views full`` vs all views) re-uses exactly the same queries.

With ``--ocr`` the visual Top-k is re-ranked by label text exactly like the
service (wine_ml.text_match.rerank); OCR results are cached too. Use
``--hires`` for OCR: at the default 768 px the synthetic labels are too small
to read, which understates OCR (see docs/PRESENTATION.md).

Usage:
  python ml/scripts/evaluate.py --views full --tag baseline
  python ml/scripts/evaluate.py --tag multiview
  python ml/scripts/evaluate.py --limit 300 --hires --ocr --sweep      # tune OCR_ALPHA / OCR_BETA
  python ml/scripts/evaluate.py --limit 300 --hires --ocr --tag ocr
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
from wine_ml.config import DEVICE, MODEL_NAME, OCR_ALPHA, OCR_BETA
from wine_ml.db import connect, fetch_embeddings
from wine_ml.preprocess import normalize_image
from wine_ml.text_match import rerank
from wine_ml.twins import TWIN_THRESHOLD, twin_groups
from wine_ml.views import LABEL_WEIGHT, VIEWS

HARD_THRESHOLD = 0.9  # nearest *other* reference this similar = near-duplicate


def load_queries(args, wines_in_index: list[str]) -> list[tuple[str, callable]]:
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

    catalog = {json.loads(l)["slug"]: json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")}
    max_side = 2048 if args.hires else 768
    rng = random.Random(args.seed)
    chosen = sorted(wines_in_index)
    if args.limit:
        chosen = rng.sample(chosen, min(args.limit, len(chosen)))
    out = []
    for slug in chosen:
        path = args.catalog / "images" / catalog[slug]["image_file"]
        for _ in range(args.n_aug):
            seed = rng.randint(0, 2**31)
            out.append((slug, lambda p=path, s=seed: field_like(Image.open(p), random.Random(s), max_side=max_side)))
    return out


def embed_queries(args, queries) -> tuple[np.ndarray, float]:
    """Query embeddings (cached for synthetic mode) and embed ms/image."""
    cache = None
    if not args.labels:
        cache = args.out / "cache" / (f"q-{args.model.split('/')[-1]}-seed{args.seed}"
                                      f"-n{args.n_aug}-limit{args.limit}{'-hires' if args.hires else ''}.npz")
        if cache.exists():
            z = np.load(cache, allow_pickle=False)
            if list(z["slugs"]) == [s for s, _ in queries]:
                print(f"query embeddings from cache: {cache}")
                return z["emb"], float(z["embed_ms"])

    from wine_ml.embedder import Embedder

    emb = Embedder(args.model, args.device)
    out, t_embed = [], 0.0
    for i in tqdm(range(0, len(queries), args.batch), unit="batch"):
        chunk = queries[i:i + args.batch]
        images = [normalize_image(load()) for _, load in chunk]
        t0 = time.perf_counter()
        out.append(emb.embed(images, batch_size=args.batch))
        t_embed += time.perf_counter() - t0
    q = np.concatenate(out)
    ms = 1000 * t_embed / max(len(queries), 1)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, emb=q, slugs=np.array([s for s, _ in queries]), embed_ms=ms)
    return q, ms


def combine_views(per_view: dict[str, np.ndarray], label_weight: float) -> np.ndarray:
    """(n_queries, n_wines) score = (1 - w) * full + w * best label view; full only if no label views.

    Same formula as the web VectorEngine. Plain max over views over-rewards
    chance matches of label crops on whole-bottle photos; the blend helps both
    close-ups and bottle shots (see reports/ACCURACY.md).
    """
    labels = [s for v, s in per_view.items() if v != "full"]
    if not labels:
        return per_view["full"]
    best_label = np.maximum.reduce(labels)
    return (1 - label_weight) * per_view["full"] + label_weight * best_label


def ocr_queries(args, queries) -> list[list[dict]]:
    """OCR items per query (cached for synthetic mode); images are regenerated deterministically."""
    cache = None
    if not args.labels:
        cache = args.out / "cache" / f"ocr-seed{args.seed}-n{args.n_aug}-limit{args.limit}{'-hires' if args.hires else ''}.json"
        if cache.exists():
            z = json.loads(cache.read_text(encoding="utf-8"))
            if z["slugs"] == [s for s, _ in queries]:
                print(f"OCR from cache: {cache}")
                return z["ocr"]

    from wine_ml.config import resolve_device
    from wine_ml.ocr import OcrEngine

    engine = OcrEngine(resolve_device(args.device))
    t0 = time.perf_counter()
    out = [engine.read(load()) for _, load in tqdm(queries, unit="img", desc="ocr")]
    print(f"OCR: {1000 * (time.perf_counter() - t0) / max(len(queries), 1):.0f} ms/img")
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"slugs": [s for s, _ in queries], "ocr": out}, ensure_ascii=False), encoding="utf-8")
    return out


def rank_rows(queries, scores: np.ndarray, wines: list[str], catalog: dict, ocr: list | None,
              k: int, alpha: float, beta: float) -> list[dict]:
    """Rank of the true wine per query; with OCR the visual Top-k is re-ranked by text (same code as /rerank)."""
    pos = {s: i for i, s in enumerate(wines)}
    order = np.argsort(-scores, axis=1)
    rows = []
    for qi, ((slug, _), sc, od) in enumerate(zip(queries, scores, order)):
        ranked = [wines[j] for j in od]
        final = [float(sc[j]) for j in od[:2]]
        if ocr is not None:
            cands = [{**{f: catalog[wines[j]].get(f) for f in ("name", "winery", "grapes", "category")},
                      "slug": wines[j], "visual": float(sc[j])} for j in od[:k]]
            rr = rerank(ocr[qi], cands, alpha, beta)
            ranked = [c["slug"] for c in rr] + ranked[k:]
            final = [rr[0]["final"], rr[1]["final"]]
        rank = ranked.index(slug) + 1 if slug in pos else len(wines) + 1
        rows.append({"slug": slug, "rank": rank, "pred": ranked[0], "score1": float(sc[od[0]]),
                     "margin": final[0] - final[1], "top5": ranked[:5]})
    return rows


def summarize(rows: list[dict], margin_thr: float) -> dict:
    if not rows:
        return {"n": 0}
    correct = [r for r in rows if r["rank"] == 1]
    confident = [r for r in rows if r["margin"] >= margin_thr]
    return {
        "n": len(rows),
        "top1": round(float(np.mean([r["rank"] == 1 for r in rows])), 4),
        "top5": round(float(np.mean([1 <= r["rank"] <= 5 for r in rows])), 4),
        "top10": round(float(np.mean([1 <= r["rank"] <= 10 for r in rows])), 4),
        "mean_margin_correct": round(float(np.mean([r["margin"] for r in correct])), 4) if correct else None,
        "mean_top1_score": round(float(np.mean([r["score1"] for r in rows])), 4),
        "confident_share": round(len(confident) / len(rows), 4),
        "confident_top1": round(float(np.mean([r["rank"] == 1 for r in confident])), 4) if confident else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--device", default=DEVICE)
    ap.add_argument("--views", default=",".join(VIEWS), help="index views to search (comma-separated)")
    ap.add_argument("--label-weight", type=float, default=LABEL_WEIGHT,
                    help="score = (1-w)*full + w*best label view (same as web LABEL_WEIGHT)")
    ap.add_argument("--ocr", action="store_true", help="re-rank the visual Top-k by label text (OCR)")
    ap.add_argument("--rerank-k", type=int, default=10)
    ap.add_argument("--alpha", type=float, default=OCR_ALPHA, help="final = visual + alpha*text - beta*conflicts")
    ap.add_argument("--beta", type=float, default=OCR_BETA)
    ap.add_argument("--sweep", action="store_true", help="with --ocr: print a grid over alpha/beta and exit")
    ap.add_argument("--hires", action="store_true",
                    help="synthetic queries at up to 2048 px (label text readable for OCR) instead of 768 px")
    ap.add_argument("--n-aug", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0, help="evaluate a random subset of wines")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--margin", type=float, default=0.03, help="confidence margin threshold")
    ap.add_argument("--labels", type=Path)
    ap.add_argument("--images-dir", type=Path, default=Path("."))
    ap.add_argument("--tag", default="", help="suffix for report file names")
    ap.add_argument("--out", type=Path, default=Path("reports"))
    args = ap.parse_args()
    views = [v.strip() for v in args.views.split(",") if v.strip()]

    if "full" not in views:
        raise SystemExit("--views must include 'full'")
    with connect() as conn:
        per_view_index = {v: fetch_embeddings(conn, args.model, [v]) for v in views}
    full_slugs, full = per_view_index["full"]
    if not full_slugs:
        raise SystemExit(f"index is empty for model {args.model}; run build_index.py first")
    for v, (s, _) in per_view_index.items():
        if s != full_slugs:
            raise SystemExit(f"view '{v}' is not indexed for every wine; run build_index.py --views {v}")

    sim = full @ full.T
    np.fill_diagonal(sim, -1)
    hard = {s for s, v in zip(full_slugs, sim.max(axis=1)) if v >= HARD_THRESHOLD}
    twins = {s for g in twin_groups(full_slugs, full, TWIN_THRESHOLD) for s in g}

    queries = load_queries(args, full_slugs)
    wine_set = set(full_slugs)
    queries = [(s, f) for s, f in queries if s in wine_set]
    print(f"index: {len(wine_set)} wines x views {views}, label weight {args.label_weight}; "
          f"near-duplicates: {len(hard)}, twins: {len(twins)}; queries: {len(queries)}")

    q, embed_ms = embed_queries(args, queries)
    scores = combine_views({v: q @ x.T for v, (_, x) in per_view_index.items()}, args.label_weight)
    catalog = {json.loads(l)["slug"]: json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")}
    ocr = ocr_queries(args, queries) if args.ocr else None

    if args.sweep:
        clean_idx = [i for i, (s, _) in enumerate(queries) if s not in twins]
        print("alpha  beta  | top1   top5   | near-dup top1")
        for alpha in (0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3):
            for beta in (0.0, 0.01, 0.02, 0.05):
                rows = rank_rows(queries, scores, full_slugs, catalog, ocr, args.rerank_k, alpha, beta)
                c = [rows[i] for i in clean_idx]
                m, nd = summarize(c, args.margin), summarize([r for r in c if r["slug"] in hard], args.margin)
                print(f"{alpha:<5}  {beta:<4}  | {m['top1']:.1%}  {m['top5']:.1%}  | {nd['top1']:.1%}")
        return

    rows = rank_rows(queries, scores, full_slugs, catalog, ocr, args.rerank_k, args.alpha, args.beta)
    clean = [r for r in rows if r["slug"] not in twins]
    metrics = {
        "all_without_twins": summarize(clean, args.margin),
        "near_duplicates": summarize([r for r in clean if r["slug"] in hard], args.margin),
        "distinct": summarize([r for r in clean if r["slug"] not in hard], args.margin),
        "twins": summarize([r for r in rows if r["slug"] in twins], args.margin),
    }
    mode = ("labeled" if args.labels else f"synthetic x{args.n_aug}" + (" hires" if args.hires else "")) + (f", OCR rerank top-{args.rerank_k} a={args.alpha} b={args.beta}" if args.ocr else "")
    report = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "model": args.model, "views": views, "mode": mode,
        "index_wines": len(wine_set), "near_duplicate_refs": len(hard), "twin_refs": len(twins),
        "margin_threshold": args.margin, "embed_ms_per_image": round(embed_ms, 1),
        "metrics": metrics,
        "errors_sample": [r for r in clean if r["rank"] != 1][:50],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    tag = args.model.split("/")[-1] + ("-labeled" if args.labels else "-synthetic") + (f"-{args.tag}" if args.tag else "")
    (args.out / f"eval-{tag}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Eval: {args.model} ({mode}), views: {', '.join(views)}, label weight {args.label_weight}", "",
             f"Index: {len(wine_set)} wines; near-duplicates (cos≥{HARD_THRESHOLD}): {len(hard)}; "
             f"twins (cos≥{TWIN_THRESHOLD}, excluded from the main rows): {len(twins)}. "
             f"Embed: {report['embed_ms_per_image']} ms/img (batched).", "",
             "| subset | n | Top-1 | Top-5 | Top-10 | mean margin (correct) | confident share | Top-1 when confident |",
             "|---|---|---|---|---|---|---|---|"]
    for name, b in metrics.items():
        if b["n"]:
            lines.append(f"| {name} | {b['n']} | {b['top1']:.1%} | {b['top5']:.1%} | {b['top10']:.1%} | "
                         f"{b['mean_margin_correct']} | {b['confident_share']:.1%} | {b['confident_top1']} |")
    (args.out / f"eval-{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

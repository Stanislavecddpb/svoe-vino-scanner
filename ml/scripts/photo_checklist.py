"""Shooting checklist for a real labeled test set -> data/photo_kit/{checklist.csv, checklist.html}.

Picks wines from the largest wineries (most likely to be on store shelves):
per winery two near-duplicate pairs (both bottles of a label series - the
hard case) plus two visually distinct wines. Twins (same reference photo for
different wines) are skipped: no method can tell them apart.

checklist.html is self-contained (thumbnails embedded) - open it on a phone
in the store; the "снято" ticks are kept in the browser.

Usage: python ml/scripts/photo_checklist.py [--wineries 20] [--per-winery 6]
"""
from __future__ import annotations

import argparse
import base64
import csv
import html
import io
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from wine_ml.config import MODEL_NAME
from wine_ml.db import connect, fetch_embeddings


def thumb_b64(path: Path, h: int = 180) -> str:
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.getchannel("A"))
    bg.thumbnail((h, h))
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()


def pick(wines: dict, slugs: list[str], vecs: np.ndarray, twins: set[str],
         n_wineries: int, per_winery: int, rng: random.Random) -> list[tuple[dict, str, str]]:
    """[(wine, group label, pair id)] ordered by winery."""
    pos = {s: i for i, s in enumerate(slugs)}
    by_winery = defaultdict(list)
    for s in slugs:
        if s not in twins:
            by_winery[wines[s]["winery"]].append(s)
    top = [w for w, _ in Counter({w: len(v) for w, v in by_winery.items()}).most_common(n_wineries)]
    out = []
    for winery in top:
        members = by_winery[winery]
        idx = [pos[s] for s in members]
        sim = vecs[idx] @ vecs[idx].T
        np.fill_diagonal(sim, -1)
        used, chosen = set(), []
        # most similar pairs first (label series), each wine used once
        pairs = sorted(((sim[i, j], i, j) for i in range(len(idx)) for j in range(i + 1, len(idx))), reverse=True)
        n_pairs = 0
        for s, i, j in pairs:
            if n_pairs >= (per_winery - 2) // 2 or s < 0.9:
                break
            if i in used or j in used:
                continue
            used |= {i, j}
            n_pairs += 1
            pid = f"{winery[:12]}#{n_pairs}"
            chosen += [(members[i], "серия", pid), (members[j], "серия", pid)]
        rest = [k for k in range(len(idx)) if k not in used and sim[k].max() < 0.9]
        rng.shuffle(rest)
        for k in rest[: per_winery - len(chosen)]:
            chosen.append((members[k], "отдельное", ""))
        out += [(wines[s], g, p) for s, g, p in chosen]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    ap.add_argument("--out", type=Path, default=Path("data/photo_kit"))
    ap.add_argument("--wineries", type=int, default=20)
    ap.add_argument("--per-winery", type=int, default=6)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    wines = {json.loads(l)["slug"]: json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")}
    twins = {r["slug"] for r in csv.DictReader((args.catalog / "twins.csv").open(encoding="utf-8"))}
    with connect() as conn:
        slugs, vecs = fetch_embeddings(conn, MODEL_NAME, ["full"])
    rows = pick(wines, slugs, vecs, twins, args.wineries, args.per_winery, random.Random(args.seed))

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "checklist.csv").open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["winery", "name", "category", "color", "group", "pair", "slug"])
        for w, g, p in rows:
            wr.writerow([w["winery"], w["name"], w["category"], w["color"], g, p, w["slug"]])

    cards, current = [], None
    for w, g, p in rows:
        if w["winery"] != current:
            current = w["winery"]
            cards.append(f'<h2>{html.escape(current)}</h2>')
        tag = f'<span class="tag s">серия {html.escape(p.split("#")[-1])}</span>' if g == "серия" else '<span class="tag">отдельное</span>'
        cards.append(
            f'<label class="card"><input type="checkbox" data-slug="{html.escape(w["slug"])}">'
            f'<img src="data:image/jpeg;base64,{thumb_b64(args.catalog / "images" / w["image_file"])}" alt="">'
            f'<div><b>{html.escape(w["name"])}</b><br><small>{html.escape(w["category"] or "")}'
            f' · {html.escape(w["color"] or "")}</small><br>{tag}<br><code>{html.escape(w["slug"])}</code></div></label>')
    page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Съёмка вин — чек-лист</title>
<style>
body{{margin:0;padding:16px;font-family:system-ui,sans-serif;background:#fdf9ed;color:#2c2a28;max-width:720px;margin:auto}}
h1{{color:#8f3d42;font-size:22px}} h2{{font-size:17px;margin:24px 0 8px;color:#8f3d42}}
.card{{display:flex;gap:12px;align-items:center;background:#fff;border-radius:12px;padding:8px;margin:6px 0}}
.card img{{width:60px;height:90px;object-fit:contain}} .card input{{width:22px;height:22px;flex:none}}
.card:has(input:checked){{opacity:.45}} code{{font-size:11px;color:#857e79;word-break:break-all}}
.tag{{font-size:11px;background:#eee;border-radius:99px;padding:1px 8px}} .tag.s{{background:#f8ecc9;color:#8f3d42}}
.tip{{background:#f8ecc9;border-radius:12px;padding:10px 12px;font-size:14px;line-height:1.45}}
</style></head><body>
<h1>Чек-лист съёмки: {len(rows)} вин</h1>
<div class="tip"><b>Как снимать</b>: 2–3 фото на бутылку — крупный план этикетки прямо; под углом ~30°; бутылка на полке с соседями.
Без вспышки, как обычный покупатель. Имя файла любое — в таблицу пишем имя файла и slug (серый текст под названием).
«Серия N» — пары почти одинаковых этикеток: снимайте обе бутылки пары, это самые важные фото.
Вина, которых нет в списке и в каталоге, тоже полезны (5–10 шт.): в таблице slug = <code>-</code>.</div>
<p id="cnt"></p>
{"".join(cards)}
<script>
const KEY='wine-photo-kit', done=new Set(JSON.parse((()=>{{try{{return localStorage.getItem(KEY)}}catch(e){{return null}}}})()||'[]'));
const boxes=[...document.querySelectorAll('input[data-slug]')], cnt=document.getElementById('cnt');
const upd=()=>{{cnt.textContent=`Снято: ${{boxes.filter(b=>b.checked).length}} из ${{boxes.length}}`;}};
boxes.forEach(b=>{{b.checked=done.has(b.dataset.slug);b.onchange=()=>{{b.checked?done.add(b.dataset.slug):done.delete(b.dataset.slug);
try{{localStorage.setItem(KEY,JSON.stringify([...done]))}}catch(e){{}};upd();}};}}); upd();
</script></body></html>"""
    (args.out / "checklist.html").write_text(page, encoding="utf-8")
    n_series = sum(1 for _, g, _ in rows if g == "серия")
    print(f"{len(rows)} wines from {args.wineries} wineries ({n_series} in label series) -> {args.out}/checklist.{{csv,html}}")


if __name__ == "__main__":
    main()

"""Review page for labeling real photos -> data/labeling/{index.html, data.js}.

For every photo the current pipeline (visual views + OCR re-ranking, same code
as the service and evaluate.py) proposes a Top-10; a person confirms the right
wine, searches the catalog, or marks "not in catalog". The page keeps answers
in the browser and exports eval/real/labels.tsv (image_path<TAB>slug, "-" = not
in catalog, rows with "?" are skipped by evaluate.py).

Open data/labeling/index.html directly from disk (no server needed).

Usage: python ml/scripts/label_helper.py [--photos eval/real/photos] [--k 10]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import combine_views  # noqa: E402  (same scoring as the service)

from wine_ml.config import DEVICE, MODEL_NAME, OCR_ALPHA, OCR_BETA, make_ocr_engine  # noqa: E402
from wine_ml.db import connect, fetch_embeddings  # noqa: E402
from wine_ml.embedder import Embedder  # noqa: E402
from wine_ml.preprocess import normalize_image  # noqa: E402
from wine_ml.text_match import rerank  # noqa: E402
from wine_ml.views import LABEL_WEIGHT, VIEWS  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", type=Path, default=Path("eval/real/photos"))
    ap.add_argument("--catalog", type=Path, default=Path("data/catalog"))
    ap.add_argument("--out", type=Path, default=Path("data/labeling"))
    ap.add_argument("--k", type=int, default=10)
    args = ap.parse_args()

    wines = {json.loads(l)["slug"]: json.loads(l) for l in (args.catalog / "wines.jsonl").open(encoding="utf-8")}
    with connect() as conn:
        per_view = {v: fetch_embeddings(conn, MODEL_NAME, [v]) for v in VIEWS}
    slugs = per_view["full"][0]

    photos = sorted(p for p in args.photos.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    emb, ocr_engine = Embedder(MODEL_NAME, DEVICE), make_ocr_engine(DEVICE)
    items = []
    for p in tqdm(photos, unit="photo"):
        with Image.open(p) as im:
            im.load()
            q = emb.embed([normalize_image(im)])[0]
            ocr = ocr_engine.read(im)
        scores = combine_views({v: x @ q[None].T for v, (_, x) in per_view.items()}, LABEL_WEIGHT)[:, 0]
        order = np.argsort(-scores)[: args.k]
        cands = [{"slug": slugs[j], "visual": float(scores[j]),
                  **{f: wines[slugs[j]].get(f) for f in ("name", "winery", "grapes", "category")}} for j in order]
        ranked = rerank(ocr, cands, OCR_ALPHA, OCR_BETA)
        items.append({
            "photo": p.name,
            "ocr": " · ".join(o["text"] for o in ocr if o["conf"] > 0.4)[:300],
            "best_visual": round(float(scores[order[0]]), 4),
            "cands": [{"slug": c["slug"], "score": round(c["final"], 4), "text": c["text"]} for c in ranked],
        })

    args.out.mkdir(parents=True, exist_ok=True)
    catalog = [{"slug": s, "name": w["name"], "winery": w.get("winery"), "category": w.get("category"),
                "img": w["image_file"]} for s, w in sorted(wines.items(), key=lambda kv: (kv[1].get("winery") or "", kv[1]["name"]))]
    (args.out / "data.js").write_text(
        "window.CATALOG=" + json.dumps(catalog, ensure_ascii=False) + ";\n"
        "window.ITEMS=" + json.dumps(items, ensure_ascii=False) + ";\n", encoding="utf-8")
    (args.out / "index.html").write_text(PAGE, encoding="utf-8")
    print(f"{len(items)} photos -> {args.out / 'index.html'}")


PAGE = r"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Разметка фото вин</title>
<style>
:root{--bg:#fdf9ed;--sand:#f8ecc9;--wine:#8f3d42;--text:#2c2a28;--muted:#857e79;--ok:#2e7d32}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--sand);padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header b{color:var(--wine)} button{font:inherit;cursor:pointer;border-radius:999px;border:1px solid var(--wine);background:#fff;color:var(--wine);padding:6px 14px}
button.primary{background:var(--wine);color:#fff} button:disabled{opacity:.4;cursor:default}
main{display:grid;grid-template-columns:minmax(280px,38%) 1fr;gap:16px;padding:16px;max-width:1500px;margin:auto}
@media(max-width:800px){main{grid-template-columns:1fr}}
.photo img{width:100%;max-height:78vh;object-fit:contain;border-radius:12px;background:#fff}
.meta{font-size:13px;color:var(--muted);margin:6px 0} .ocr{font-size:12px;color:var(--muted);word-break:break-word}
.state{padding:8px 12px;border-radius:10px;background:var(--sand);margin:8px 0;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px}
.c{background:#fff;border-radius:12px;padding:8px;border:2px solid transparent;cursor:pointer;position:relative;font-size:13px}
.c:hover{border-color:var(--sand)} .c.sel{border-color:var(--ok);box-shadow:0 0 0 2px var(--ok)}
.c img{width:100%;height:170px;object-fit:contain;mix-blend-mode:multiply}
.c .n{font-weight:600;line-height:1.2} .c .w{color:var(--muted)} .c .k{position:absolute;top:6px;left:8px;background:var(--wine);color:#fff;border-radius:99px;padding:0 7px;font-size:12px}
.c .s{font-size:11px;color:var(--muted)} input[type=search]{width:100%;padding:8px 12px;border-radius:999px;border:1px solid #c2bfbc;font:inherit;margin:10px 0}
.row{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0} h3{margin:14px 0 6px;font-size:15px}
.dots{display:flex;flex-wrap:wrap;gap:3px;max-width:520px} .dots span{width:9px;height:9px;border-radius:2px;background:#ddd;cursor:pointer}
.dots span.done{background:var(--ok)} .dots span.none{background:#999} .dots span.skip{background:#e0a800} .dots span.cur{outline:2px solid var(--wine)}
kbd{background:#fff;border:1px solid #ccc;border-radius:4px;padding:0 4px;font-size:12px}
</style></head><body>
<header>
  <b>Разметка</b><span id="pos"></span><span id="cnt"></span>
  <button id="prev">← Назад</button><button id="next">Вперёд →</button>
  <button id="nextTodo">К неразмеченному</button><button class="primary" id="export">Скачать labels.tsv</button>
  <div class="dots" id="dots"></div>
</header>
<main>
  <section class="photo"><img id="img" alt=""><div class="meta" id="name"></div><div class="ocr" id="ocr"></div></section>
  <section>
    <div class="state" id="state"></div>
    <div class="row"><button id="none">Нет в каталоге (<kbd>N</kbd>)</button><button id="skip">Не понятно, пропустить (<kbd>S</kbd>)</button><button id="clear">Сбросить</button></div>
    <div class="meta">Клавиши: <kbd>1</kbd>–<kbd>9</kbd>, <kbd>0</kbd> — выбрать кандидата; <kbd>←</kbd>/<kbd>→</kbd> — листать. Серии этикеток (брют/полусладкое, цвет, год, шахматная фигура) сверяйте внимательно.</div>
    <h3>Кандидаты сервиса</h3><div class="grid" id="cands"></div>
    <h3>Поиск по каталогу</h3><input type="search" id="q" placeholder="название или винодельня, например «табия победа»"><div class="grid" id="found"></div>
  </section>
</main>
<script src="data.js"></script>
<script>
const KEY='wine-labels-v1', PHOTO_DIR='../../eval/real/photos/', CAT_DIR='../catalog/images/';
const bySlug=Object.fromEntries(CATALOG.map(c=>[c.slug,c]));
let labels={}; try{labels=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
let i=0; const $=id=>document.getElementById(id);
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(labels))}catch(e){}};
const esc=s=>(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function card(slug,key,extra){const c=bySlug[slug]; if(!c) return '';
  const sel=labels[ITEMS[i].photo]===slug?' sel':'';
  return `<div class="c${sel}" data-slug="${esc(slug)}">${key!==undefined?`<span class="k">${key}</span>`:''}
  <img loading="lazy" src="${CAT_DIR}${encodeURIComponent(c.img)}" alt=""><div class="n">${esc(c.name)}</div>
  <div class="w">${esc(c.winery)} · ${esc(c.category)}</div>${extra?`<div class="s">${extra}</div>`:''}</div>`}
function render(){
  const it=ITEMS[i], lab=labels[it.photo];
  $('img').src=PHOTO_DIR+encodeURIComponent(it.photo); $('name').textContent=it.photo+` · лучший визуальный скор ${it.best_visual}`;
  $('ocr').textContent=it.ocr?('OCR: '+it.ocr):''; $('pos').textContent=`${i+1} / ${ITEMS.length}`;
  const n=Object.values(labels).filter(v=>v&&v!=='?').length; $('cnt').textContent=`размечено ${n}`;
  $('state').innerHTML= lab===undefined?'Не размечено': lab==='-'?'<b>Нет в каталоге</b>': lab==='?'?'Пропущено (не понятно)':
     `Выбрано: <b>${esc(bySlug[lab]?.name)}</b> — ${esc(bySlug[lab]?.winery)} <span class="meta">${esc(lab)}</span>`;
  $('cands').innerHTML=it.cands.map((c,k)=>card(c.slug,(k+1)%10,`скор ${c.score}${c.text?` · текст ${c.text}`:''}`)).join('');
  search(); dots();
}
function search(){const q=$('q').value.trim().toLowerCase(); if(q.length<2){$('found').innerHTML='';return}
  const words=q.split(/\s+/); const hits=CATALOG.filter(c=>{const t=((c.name||'')+' '+(c.winery||'')+' '+c.slug).toLowerCase(); return words.every(w=>t.includes(w))}).slice(0,40);
  $('found').innerHTML=hits.map(h=>card(h.slug)).join('')||'<div class="meta">Ничего не найдено</div>'}
function dots(){$('dots').innerHTML=ITEMS.map((it,k)=>{const l=labels[it.photo];
  const cls=l===undefined?'':l==='-'?'none':l==='?'?'skip':'done'; return `<span class="${cls}${k===i?' cur':''}" data-k="${k}" title="${esc(it.photo)}"></span>`}).join('')}
function setLabel(v){const p=ITEMS[i].photo; if(v===null) delete labels[p]; else labels[p]=v; save(); if(v!==null&&i<ITEMS.length-1){i++;} render(); window.scrollTo(0,0)}
document.addEventListener('click',e=>{const c=e.target.closest('.c'); if(c) return setLabel(c.dataset.slug);
  const d=e.target.closest('.dots span'); if(d){i=+d.dataset.k; render()}});
$('none').onclick=()=>setLabel('-'); $('skip').onclick=()=>setLabel('?'); $('clear').onclick=()=>setLabel(null);
$('prev').onclick=()=>{if(i>0){i--;render()}}; $('next').onclick=()=>{if(i<ITEMS.length-1){i++;render()}};
$('nextTodo').onclick=()=>{const k=ITEMS.findIndex(it=>labels[it.photo]===undefined); if(k>=0){i=k;render()}};
$('q').oninput=search;
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;
  if(/^[0-9]$/.test(e.key)){const k=(+e.key+9)%10; const c=ITEMS[i].cands[k]; if(c) setLabel(c.slug)}
  else if(e.key==='n'||e.key==='т') setLabel('-'); else if(e.key==='s'||e.key==='ы') setLabel('?');
  else if(e.key==='ArrowRight') $('next').click(); else if(e.key==='ArrowLeft') $('prev').click()});
$('export').onclick=()=>{const rows=['image_path\tslug',...ITEMS.filter(it=>labels[it.photo]!==undefined).map(it=>`${it.photo}\t${labels[it.photo]}`)];
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([rows.join('\n')+'\n'],{type:'text/tab-separated-values'}));
  a.download='labels.tsv'; a.click()};
render();
</script></body></html>
"""

if __name__ == "__main__":
    main()

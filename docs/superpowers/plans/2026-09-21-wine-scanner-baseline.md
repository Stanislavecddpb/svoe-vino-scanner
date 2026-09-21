# Wine Scanner: Backend Skeleton + CV Baseline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Photo → Nuxt API → Recognition Engine (stub | SigLIP 2 + pgvector) → `{"slug"}` / Top-5 with scores, runnable locally and via docker compose.

**Architecture:** Nuxt 3 (Nitro) owns the public API, catalog and pgvector search. A stateless Python FastAPI service (`ml/`) does image normalization + SigLIP 2 embedding. Offline Python scripts build the unambiguous catalog, load it into Postgres, embed reference images and evaluate.

**Tech Stack:** Nuxt 3 + Nitro + `pg` + vitest; Python 3.12, FastAPI, torch (CUDA), transformers (SigLIP 2), Pillow, psycopg 3, pgvector-python, pytest; Postgres 16 + pgvector (docker image `pgvector/pgvector:pg16`).

Spec: `docs/superpowers/specs/2026-09-21-wine-scanner-baseline-design.md`

## Global Constraints

- Eval contract: `POST /v1/eval/predict`, multipart field `image`, response `{"slug":"..."}`, HTTP 200; script timeout 10 s; target latency < 3 s.
- Web listens on port `8080` (script default endpoint `http://127.0.0.1:8080/v1/eval/predict`).
- ml service port `8001`; Postgres port `5432`, db/user/password `wine`/`wine`/`wine`.
- `ENGINE=stub|vector` (default `vector` in compose, `stub` in tests).
- Default model `google/siglip2-so400m-patch14-384`, env `MODEL_NAME`; fp16 on CUDA, fp32 on CPU; embeddings L2-normalized.
- Data under `data/` is gitignored; raw Strapi uploads dir: `data/raw/strapi/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads`.
- Only unambiguous catalog positions are indexed; exclusions go to `data/catalog/excluded.csv` with reason.

## File Structure

```
db/init.sql                         schema (extension vector, wines, wine_embeddings)
docker-compose.yml                  postgres + ml + web
.env.example                        all env vars
ml/pyproject.toml                   python package wine_ml + deps
ml/Dockerfile
ml/wine_ml/config.py                env settings
ml/wine_ml/preprocess.py            normalize_image(PIL) -> PIL
ml/wine_ml/embedder.py              Embedder(model_name, device).embed(list[PIL]) -> np.ndarray
ml/wine_ml/catalog.py               name_key(), build_catalog(csv, uploads) -> (wines, excluded)
ml/wine_ml/db.py                    connect(), upsert_wines(), upsert_embeddings(), fetch_embeddings()
ml/wine_ml/augment.py               field_like(PIL, rng) -> PIL  (synthetic "field photo")
ml/wine_ml/service.py               FastAPI app: GET /health, POST /embed
ml/scripts/build_catalog.py         CLI -> data/catalog/wines.jsonl, excluded.csv, images/
ml/scripts/load_catalog.py          CLI -> wines table
ml/scripts/build_index.py           CLI -> wine_embeddings
ml/scripts/evaluate.py              CLI -> reports/eval-<model>.md/.json
ml/scripts/contact_sheet.py         CLI: query dir -> top-5 contact sheet jpg via web API
ml/tests/test_preprocess.py, test_catalog.py, test_service.py, test_augment.py
web/package.json, nuxt.config.ts, Dockerfile, vitest.config.ts
web/server/utils/config.ts          runtime config accessors
web/server/utils/db.ts              pg Pool singleton
web/server/utils/image.ts           readImage(event) -> {buffer, filename, type} | throws 400
web/server/utils/engine/types.ts    Candidate, RecognitionEngine
web/server/utils/engine/stub.ts     StubEngine
web/server/utils/engine/vector.ts   VectorEngine (ml /embed + pgvector)
web/server/utils/engine/index.ts    getEngine()
web/server/utils/search.ts          toSearchResponse(candidates, ...)
web/server/routes/v1/eval/predict.post.ts
web/server/routes/v1/search.post.ts
web/server/routes/v1/wines/[slug].get.ts
web/server/routes/health.get.ts
web/app.vue                         minimal upload page for manual demo
web/tests/api.test.ts               contract tests on stub engine
eval/                               organizer kit (participant_test.sh, queries.tsv, queries/)
scripts/setup.ps1, scripts/dev.ps1  one-command local setup/run (Windows); Makefile-like README steps
README.md, ARCHITECTURE.md
```

---

### Task 1: Repo skeleton, DB schema, docker Postgres

**Files:** Create `db/init.sql`, `docker-compose.yml` (postgres only for now), `.env.example`, copy `data/raw/eval/*` → `eval/`.

**Interfaces — Produces:** tables

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS wines (
  slug text PRIMARY KEY, name text NOT NULL, category text, color text, region text,
  grapes text, description text, winery text, image_file text NOT NULL);
CREATE TABLE IF NOT EXISTS wine_embeddings (
  slug text REFERENCES wines(slug) ON DELETE CASCADE, model text NOT NULL,
  embedding vector NOT NULL, PRIMARY KEY (slug, model));
```

- [ ] Write `db/init.sql` (above), compose service `db` from `pgvector/pgvector:pg16` mounting `./db/init.sql:/docker-entrypoint-initdb.d/init.sql`, healthcheck `pg_isready -U wine`.
- [ ] Run `docker compose up -d db` then `docker compose exec db psql -U wine -c "\dt"` → expect `wines`, `wine_embeddings`.
- [ ] Commit `chore: repo skeleton, pgvector schema, organizer eval kit`.

### Task 2: Catalog builder (unambiguous positions)

**Files:** `ml/pyproject.toml`, `ml/wine_ml/catalog.py`, `ml/scripts/build_catalog.py`, `ml/tests/test_catalog.py`.

**Interfaces — Produces:**
- `name_key(stem: str) -> str` — lowercase, Cyrillic→Latin translit, keep only `[a-z0-9]`.
- `strip_hash(stem: str) -> str` — removes repeated `_[0-9a-f]{10}` suffixes.
- `build_catalog(rows: list[dict], upload_files: list[Path]) -> tuple[list[dict], list[dict]]` — wines: `{slug,name,category,color,region,grapes,description,winery,src_file}`; excluded: `{slug, photo, reason}` with reason ∈ `shared_photo|file_not_found|ambiguous_file`.

- [ ] Tests (fail first):

```python
from pathlib import Path
from wine_ml.catalog import name_key, strip_hash, build_catalog

def test_name_key_translit_and_punct():
    assert name_key("Цимлянское Рислинг") == "tsimlyanskoerisling"
    assert name_key("4300_tlKHpEg") == name_key("4300_tl_K_Hp_Eg")

def test_strip_hash_repeated():
    assert strip_hash("Aristov_Roze_cc598880d5_2335683dfd") == "Aristov_Roze"

def row(slug, photo): return {"Slug": slug, "Название фото": photo, "Название вина": slug,
    "Категория": "", "Цвет": "", "Регион": "", "Сорт винограда": "", "Описание": "", "Винодельня": ""}

def test_build_catalog_rules(tmp_path):
    (tmp_path / "a_0123456789.webp").write_bytes(b"A")
    (tmp_path / "b_0123456789.webp").write_bytes(b"B1")
    (tmp_path / "b_abcdefabcd.webp").write_bytes(b"B2")          # ambiguous, different bytes
    (tmp_path / "c_0123456789.webp").write_bytes(b"C")
    (tmp_path / "c_abcdefabcd.webp").write_bytes(b"C")           # identical bytes -> ok
    rows = [row("a", "a.webp"), row("a", "a.webp"), row("b", "b.webp"), row("c", "c.webp"),
            row("d1", "d.webp"), row("d2", "d.webp"), row("e", "missing.webp")]
    wines, excl = build_catalog(rows, sorted(tmp_path.iterdir()))
    assert sorted(w["slug"] for w in wines) == ["a", "c"]
    reasons = {e["slug"]: e["reason"] for e in excl}
    assert reasons == {"b": "ambiguous_file", "d1": "shared_photo", "d2": "shared_photo", "e": "file_not_found"}
```

- [ ] Implement `catalog.py`; CLI `build_catalog.py --csv data/raw/strapi_output0709.csv --uploads <dir> --out data/catalog` writes `wines.jsonl`, `excluded.csv`, copies images to `data/catalog/images/<slug><ext>` (skips `thumbnail_|small_|medium_|large_`), verifies each opens with Pillow (else reason `unreadable_image`), prints counts.
- [ ] `pytest ml/tests/test_catalog.py -v` → PASS; run CLI on real data → expect ~1990 wines.
- [ ] Commit `feat(ml): build unambiguous catalog from CSV + Strapi uploads`.

### Task 3: Preprocess + Embedder + ml service `/embed`

**Files:** `ml/wine_ml/config.py`, `preprocess.py`, `embedder.py`, `service.py`, tests `test_preprocess.py`, `test_service.py`.

**Interfaces — Produces:**
- `normalize_image(img: PIL.Image) -> PIL.Image` — `ImageOps.exif_transpose`, alpha composited onto white, RGB, trim uniform border (white/transparent background of catalog shots), pad to square with white, never upscales beyond original.
- `load_image(data: bytes) -> PIL.Image` — raises `ValueError("invalid image")`.
- `Embedder(model_name: str, device: str).embed(images: list[PIL.Image], batch_size=16) -> np.ndarray[float32] (n, dim)`, rows L2-normalized; `.dim`, `.model_name`.
- `create_app(embedder_factory) -> FastAPI`; `POST /embed` multipart `image` → `{"model", "dim", "embedding": list[float]}`; 400 `{"detail": "invalid image"}`; `GET /health` → `{"status":"ok","model","device"}`.

- [ ] Tests:

```python
# test_preprocess.py
from PIL import Image
from wine_ml.preprocess import normalize_image

def test_rgba_to_square_rgb_white_bg():
    im = Image.new("RGBA", (100, 300), (0, 0, 0, 0)); im.paste((200, 0, 0, 255), (30, 50, 70, 250))
    out = normalize_image(im)
    assert out.mode == "RGB" and out.size[0] == out.size[1]
    assert out.getpixel((0, 0)) == (255, 255, 255)

def test_exif_rotation_applied():
    im = Image.new("RGB", (200, 100), (10, 20, 30)); exif = im.getexif(); exif[0x0112] = 6
    import io; b = io.BytesIO(); im.save(b, "JPEG", exif=exif); b.seek(0)
    out = normalize_image(Image.open(b))
    assert out.size[0] == out.size[1] >= 200
```

```python
# test_service.py — fake embedder, no model download
import io, numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from wine_ml.service import create_app

class Fake:
    model_name, dim, device = "fake", 4, "cpu"
    def embed(self, images, batch_size=16):
        v = np.ones((len(images), 4), np.float32); return v / np.linalg.norm(v, axis=1, keepdims=True)

def png():
    b = io.BytesIO(); Image.new("RGB", (32, 32), "red").save(b, "PNG"); return b.getvalue()

def test_embed_ok():
    c = TestClient(create_app(lambda: Fake()))
    r = c.post("/embed", files={"image": ("x.png", png(), "image/png")})
    assert r.status_code == 200 and r.json()["dim"] == 4 and len(r.json()["embedding"]) == 4

def test_embed_bad_image():
    c = TestClient(create_app(lambda: Fake()))
    assert c.post("/embed", files={"image": ("x.png", b"nope", "image/png")}).status_code == 400
```

- [ ] Implement; `Embedder` uses `AutoModel.from_pretrained(name, torch_dtype=fp16 if cuda)` + `AutoProcessor`, `model.get_image_features(**inputs)`.
- [ ] `pytest ml/tests -v` → PASS. Manual: `uvicorn wine_ml.service:app --port 8001`, `curl -F image=@eval/queries/019c68d0.jpg localhost:8001/embed` → 1152-dim vector.
- [ ] Commit `feat(ml): image normalization + SigLIP 2 embed service`.

### Task 4: Load catalog + build index into pgvector

**Files:** `ml/wine_ml/db.py`, `ml/scripts/load_catalog.py`, `ml/scripts/build_index.py`.

**Interfaces — Produces:** `connect() -> psycopg.Connection` (env `DATABASE_URL`, default `postgresql://wine:wine@localhost:5432/wine`), `upsert_wines(conn, wines)`, `upsert_embeddings(conn, model, slugs, vectors)`, `fetch_embeddings(conn, model) -> (slugs, np.ndarray)`.

- [ ] Implement; `build_index.py --model <name> --batch 16` embeds `data/catalog/images/*` via `Embedder` + `normalize_image`, skips slugs already indexed for the model unless `--force`, shows progress.
- [ ] Run both; verify `SELECT count(*) FROM wine_embeddings` ≈ wines count.
- [ ] Commit `feat(ml): load catalog and index embeddings into pgvector`.

### Task 5: Nuxt API with stub engine

**Files:** all `web/` files listed above except `vector.ts`.

**Interfaces — Produces:**

```ts
export interface Candidate { slug: string; name: string; winery: string | null; score: number }
export interface RecognitionEngine { name: string; model: string | null; recognize(image: Buffer): Promise<Candidate[]> }  // sorted desc, length ≤ 5
```

`toSearchResponse(cands, engine, latencyMs, marginThreshold)` →
`{ top1: Candidate|null, top5: Candidate[], margin: number|null, confident: boolean, engine, model, latency_ms }`.

- [ ] Tests `web/tests/api.test.ts` using `@nuxt/test-utils/e2e` `setup({ env: { ENGINE: 'stub' } })`:
  - predict with PNG → 200 and body `{slug: string}` with only key `slug`;
  - predict without `image` → 400 JSON `{error}`;
  - predict with non-image bytes → 400;
  - search → `top5.length === 5`, scores sorted desc, `margin === top5[0].score - top5[1].score`;
  - `GET /health` → `{status:'ok', engine:'stub'}`.
- [ ] StubEngine: deterministic (sha256 of image bytes → pick 5 slugs from a fixed list, or from DB if reachable); no ml/DB required.
- [ ] Image validation by magic bytes (JPEG/PNG/WEBP/GIF/BMP/HEIC), max 15 MB.
- [ ] `npx vitest run` → PASS. Commit `feat(web): Nuxt API skeleton with stub recognition engine`.

### Task 6: VectorEngine + wine card + health

- [ ] `vector.ts`: POST image to `${ML_URL}/embed` (FormData, 5 s timeout) → `SELECT w.slug, w.name, w.winery, 1 - (e.embedding <=> $1::vector) AS score FROM wine_embeddings e JOIN wines w USING (slug) WHERE e.model = $2 ORDER BY e.embedding <=> $1::vector LIMIT 5`. ml failure → 503.
- [ ] `/v1/wines/[slug]` → row from `wines` or 404; `/health` reports db, ml, indexed count.
- [ ] Manual: `ENGINE=vector`, curl predict on `eval/queries/*` → slug present.
- [ ] Commit `feat(web): vector engine over pgvector, wine card endpoint`.

### Task 7: Evaluation

**Files:** `ml/wine_ml/augment.py`, `ml/tests/test_augment.py`, `ml/scripts/evaluate.py`, `ml/scripts/contact_sheet.py`.

- [ ] `field_like(img, rng)`: random perspective (±12%), rotation ±12°, crop 70–100%, place on random textured/colored background, brightness/contrast ±30%, glare ellipse (p=0.5), gaussian blur (p=0.5), JPEG q 40–85. Test: output RGB, deterministic for same seed, differs from input.
- [ ] `evaluate.py --model <name> --n-aug 2 [--limit N] [--labels tsv]`: loads index from DB, embeds augmented queries in-process, cosine top-5; metrics: top1, top5, mean margin (correct top1), hard subset (nearest other reference cos ≥ 0.9), latency of embed per image; writes `reports/eval-<model>.json/.md`. With `--labels` evaluates real labeled photos instead.
- [ ] `contact_sheet.py --dir eval/queries --url http://127.0.0.1:8080` → `reports/contact_<name>.jpg` query + top-5 reference thumbnails with scores.
- [ ] Run organizer script: `bash eval/participant_test.sh --images-dir eval/queries --manifest eval/queries.tsv --output reports/predictions.jsonl` → 3 rows, non-null slugs, latency < 3000.
- [ ] Commit `feat(ml): synthetic evaluation, contact sheets, organizer script run`.

### Task 8: Docker compose full stack + setup scripts + docs

- [ ] `ml/Dockerfile` (python:3.12-slim, CPU torch by default, build arg for CUDA), `web/Dockerfile` (node:22 build → `.output/server/index.mjs`, PORT 8080), compose services `db`, `ml` (HF cache volume, optional `deploy.resources.reservations.devices` GPU in `docker-compose.gpu.yml`), `web` (`ENGINE=vector`, `ML_URL=http://ml:8001`).
- [ ] `scripts/setup.ps1`: venv, pip install (CUDA torch), npm ci, compose up db, build_catalog, load, index. `scripts/dev.ps1`: start ml + web.
- [ ] README.md (setup, run, env table, eval, limitations), ARCHITECTURE.md (layers: normalization → features → search → card → extras; engine swap; where OCR plugs in).
- [ ] Verify `docker compose up --build` → `/health` ok; commit `chore: compose stack, setup scripts, README, ARCHITECTURE`.

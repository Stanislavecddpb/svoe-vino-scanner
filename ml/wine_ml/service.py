"""ml service: image -> SigLIP 2 embedding (+ label text), and text re-ranking of candidates.

Run: uvicorn wine_ml.service:app --host 0.0.0.0 --port 8001

POST /embed    multipart image -> {model, dim, embedding, embed_ms}
POST /analyze  multipart image -> /embed fields + {ocr: [{text, conf, cx, cy, h}], ocr_ms}
POST /rerank   JSON {ocr, candidates: [{slug, name, winery, category, visual, ...}]} -> {candidates}
"""
from __future__ import annotations

import asyncio
import time
from functools import lru_cache
from typing import Callable

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from wine_ml.config import MAX_UPLOAD_BYTES, OCR_ALPHA, OCR_BETA
from wine_ml.preprocess import load_image, normalize_image
from wine_ml.text_match import rerank


class RerankRequest(BaseModel):
    ocr: list[dict]
    candidates: list[dict]
    alpha: float = OCR_ALPHA
    beta: float = OCR_BETA


def create_app(embedder_factory: Callable, ocr_factory: Callable | None = None) -> FastAPI:
    app = FastAPI(title="wine-ml", version="0.2.0")
    get_embedder = lru_cache(maxsize=1)(embedder_factory)
    get_ocr = lru_cache(maxsize=1)(ocr_factory) if ocr_factory else None

    @app.on_event("startup")
    def _warmup() -> None:
        get_embedder()
        if get_ocr:
            get_ocr()

    async def read_upload(image: UploadFile):
        data = await image.read()
        if not data:
            raise HTTPException(400, "empty file")
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file too large")
        try:
            return load_image(data)
        except ValueError:
            raise HTTPException(400, "invalid image")

    def embed_image(raw) -> dict:
        t0 = time.perf_counter()
        e = get_embedder()
        vec = e.embed([normalize_image(raw)])[0]
        return {"model": e.model_name, "dim": int(vec.shape[0]), "embedding": vec.tolist(),
                "embed_ms": round((time.perf_counter() - t0) * 1000, 1)}

    def ocr_image(raw) -> dict:
        t0 = time.perf_counter()
        items = get_ocr().read(raw) if get_ocr else []
        return {"ocr": items, "ocr_ms": round((time.perf_counter() - t0) * 1000, 1)}

    @app.get("/health")
    def health() -> dict:
        e = get_embedder()
        return {"status": "ok", "model": e.model_name, "device": e.device, "dim": e.dim,
                "ocr": get_ocr is not None}

    @app.post("/embed")
    async def embed(image: UploadFile = File(...)) -> dict:
        return embed_image(await read_upload(image))

    @app.post("/analyze")
    async def analyze(image: UploadFile = File(...)) -> dict:
        raw = await read_upload(image)
        # embedding and OCR run concurrently (both release the GIL on GPU work)
        emb, ocr = await asyncio.gather(asyncio.to_thread(embed_image, raw), asyncio.to_thread(ocr_image, raw))
        return {**emb, **ocr}

    @app.post("/rerank")
    def rerank_candidates(req: RerankRequest) -> dict:
        for c in req.candidates:
            if not isinstance(c.get("visual"), (int, float)):
                raise HTTPException(422, "every candidate needs a numeric 'visual' score")
        return {"candidates": rerank(req.ocr, req.candidates, req.alpha, req.beta)}

    return app


def _default_embedder():
    from wine_ml.config import DEVICE, MODEL_NAME
    from wine_ml.embedder import Embedder

    return Embedder(MODEL_NAME, DEVICE)


def _default_ocr():
    from wine_ml.config import resolve_device
    from wine_ml.ocr import OcrEngine

    return OcrEngine(resolve_device())


def _build_app() -> FastAPI:
    from wine_ml.config import OCR_ENABLED

    return create_app(_default_embedder, _default_ocr if OCR_ENABLED else None)


app = _build_app()

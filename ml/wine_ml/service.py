"""ml service: image -> normalized SigLIP 2 embedding.

Run: uvicorn wine_ml.service:app --host 0.0.0.0 --port 8001
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Callable

from fastapi import FastAPI, File, HTTPException, UploadFile

from wine_ml.config import MAX_UPLOAD_BYTES
from wine_ml.preprocess import load_image, normalize_image


def create_app(embedder_factory: Callable) -> FastAPI:
    app = FastAPI(title="wine-ml", version="0.1.0")
    get_embedder = lru_cache(maxsize=1)(embedder_factory)

    @app.on_event("startup")
    def _warmup() -> None:
        get_embedder()

    @app.get("/health")
    def health() -> dict:
        e = get_embedder()
        return {"status": "ok", "model": e.model_name, "device": e.device, "dim": e.dim}

    @app.post("/embed")
    async def embed(image: UploadFile = File(...)) -> dict:
        data = await image.read()
        if not data:
            raise HTTPException(400, "empty file")
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file too large")
        try:
            im = normalize_image(load_image(data))
        except ValueError:
            raise HTTPException(400, "invalid image")
        t0 = time.perf_counter()
        e = get_embedder()
        vec = e.embed([im])[0]
        return {"model": e.model_name, "dim": int(vec.shape[0]), "embedding": vec.tolist(),
                "embed_ms": round((time.perf_counter() - t0) * 1000, 1)}

    return app


def _default_embedder():
    from wine_ml.config import DEVICE, MODEL_NAME
    from wine_ml.embedder import Embedder

    return Embedder(MODEL_NAME, DEVICE)


app = create_app(_default_embedder)

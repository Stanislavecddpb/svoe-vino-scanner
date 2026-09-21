from __future__ import annotations

import os

MODEL_NAME = os.getenv("MODEL_NAME", "google/siglip2-so400m-patch14-384")
DEVICE = os.getenv("DEVICE", "auto")  # auto | cuda | cpu
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://wine:wine@localhost:5432/wine")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))


def resolve_device(device: str = DEVICE) -> str:
    if device != "auto":
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"

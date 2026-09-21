"""SigLIP 2 image embeddings (L2-normalized, float32)."""
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

from wine_ml.config import MODEL_NAME, resolve_device


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME, device: str = "auto"):
        self.model_name = model_name
        self.device = resolve_device(device)
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.processor = AutoProcessor.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name, dtype=dtype).eval()
        # Only image features are used: drop the text tower before moving to the GPU
        # (~half of the weights; frees VRAM for OCR). Image embeddings are unchanged.
        if hasattr(model, "text_model"):
            model.text_model = None
        self.model = model.to(self.device)
        self.dtype = dtype
        self.dim = int(self.model.config.vision_config.hidden_size)

    @torch.inference_mode()
    def embed(self, images: list[Image.Image], batch_size: int = 16) -> np.ndarray:
        out = []
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            inputs = self.processor(images=batch, return_tensors="pt").to(self.device)
            inputs["pixel_values"] = inputs["pixel_values"].to(self.dtype)
            feats = self.model.get_image_features(**inputs)
            if not isinstance(feats, torch.Tensor):  # newer transformers return a model output
                feats = feats.pooler_output
            feats = torch.nn.functional.normalize(feats.float(), dim=-1)
            out.append(feats.cpu().numpy())
        return np.concatenate(out).astype(np.float32)

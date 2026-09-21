"""Label text reading (EasyOCR, Russian + English).

Returns text fragments with confidence and normalized box geometry
(cx, cy, h in 0..1 of the image), which text_match uses to down-weight
neighbour bottles at the frame edges.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageOps

OCR_MAX_SIDE = 1280  # larger photos are downscaled: faster, and label text stays readable


class OcrEngine:
    def __init__(self, device: str = "cuda", languages: tuple[str, ...] = ("ru", "en")):
        import easyocr

        self.device = device
        self.reader = easyocr.Reader(list(languages), gpu=device == "cuda", verbose=False)

    def read(self, im: Image.Image, min_conf: float = 0.2) -> list[dict]:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((OCR_MAX_SIDE, OCR_MAX_SIDE))
        w, h = im.size
        out = []
        for box, text, conf in self.reader.readtext(np.asarray(im)):
            if conf < min_conf:
                continue
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            out.append({
                "text": text, "conf": round(float(conf), 3),
                "cx": round((min(xs) + max(xs)) / 2 / w, 3),
                "cy": round((min(ys) + max(ys)) / 2 / h, 3),
                "h": round((max(ys) - min(ys)) / h, 3),
            })
        return out

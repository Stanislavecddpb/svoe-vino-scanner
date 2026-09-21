"""Yandex Vision OCR (cloud) behind the same interface as OcrEngine.read().

POST https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText
headers: Authorization: Api-Key <key>, x-folder-id: <folder>
body:    {"content": base64, "mimeType": "JPEG", "languageCodes": ["ru", "en"], "model": "page"}
reply:   textAnnotation{width, height, blocks[{lines[{text, boundingBox{vertices[{x, y}]}}]}]}

The API accepts JPEG/PNG/PDF only, so every photo is re-encoded to JPEG
(after EXIF rotation and downscaling). Lines carry no confidence -> conf = 1.0.
"""
from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.request

from PIL import Image, ImageOps

from wine_ml.ocr import OCR_MAX_SIDE

YANDEX_OCR_URL = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"


class YandexOcrEngine:
    device = "cloud"

    def __init__(self, api_key: str, folder_id: str, timeout: float = 5.0,
                 languages: tuple[str, ...] = ("ru", "en"), url: str = YANDEX_OCR_URL):
        if not api_key or not folder_id:
            raise ValueError("Yandex OCR needs YC_OCR_API_KEY and YC_FOLDER_ID")
        self.api_key, self.folder_id, self.timeout = api_key, folder_id, timeout
        self.languages, self.url = list(languages), url

    def _request(self, jpeg: bytes) -> dict:
        body = json.dumps({"content": base64.b64encode(jpeg).decode(), "mimeType": "JPEG",
                           "languageCodes": self.languages, "model": "page"}).encode()
        req = urllib.request.Request(self.url, data=body, method="POST", headers={
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
        })
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def read(self, im: Image.Image, min_conf: float = 0.0) -> list[dict]:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((OCR_MAX_SIDE, OCR_MAX_SIDE))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        try:
            reply = self._request(buf.getvalue())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            # OCR only re-ranks; without it the service still answers by the image
            print(f"[yandex-ocr] request failed, continuing without text: {e}")
            return []
        return parse_reply(reply, im.size)


def parse_reply(reply: dict, size: tuple[int, int]) -> list[dict]:
    """textAnnotation -> [{text, conf, cx, cy, h}] with coordinates normalized to 0..1."""
    ann = reply.get("result", reply).get("textAnnotation") or {}
    w = float(ann.get("width") or size[0]) or 1.0
    h = float(ann.get("height") or size[1]) or 1.0
    out = []
    for block in ann.get("blocks", []):
        for line in block.get("lines", []):
            text = (line.get("text") or "").strip()
            vs = (line.get("boundingBox") or {}).get("vertices") or []
            if not text or not vs:
                continue
            xs = [float(v.get("x", 0)) for v in vs]  # int64 comes as strings in JSON
            ys = [float(v.get("y", 0)) for v in vs]
            out.append({"text": text, "conf": 1.0,
                        "cx": round((min(xs) + max(xs)) / 2 / w, 3),
                        "cy": round((min(ys) + max(ys)) / 2 / h, 3),
                        "h": round((max(ys) - min(ys)) / h, 3)})
    return out

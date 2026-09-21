import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from wine_ml.service import create_app


class Fake:
    model_name, dim, device = "fake", 4, "cpu"

    def embed(self, images, batch_size=16):
        v = np.ones((len(images), 4), np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)


def png() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(b, "PNG")
    return b.getvalue()


def client():
    return TestClient(create_app(lambda: Fake()))


def test_embed_ok():
    with client() as c:
        r = c.post("/embed", files={"image": ("x.png", png(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["dim"] == 4 and len(body["embedding"]) == 4 and body["model"] == "fake"


def test_embed_bad_image():
    with client() as c:
        r = c.post("/embed", files={"image": ("x.png", b"nope", "image/png")})
    assert r.status_code == 400


def test_embed_missing_field():
    with client() as c:
        assert c.post("/embed").status_code == 422


def test_health():
    with client() as c:
        assert c.get("/health").json()["model"] == "fake"


class FakeOcr:
    def read(self, im):
        return [{"text": "МУСКАТЕЛЬ БЕЛЫЙ", "conf": 0.9, "cx": 0.5, "cy": 0.5, "h": 0.05}]


def test_analyze_returns_embedding_and_ocr():
    with TestClient(create_app(lambda: Fake(), lambda: FakeOcr())) as c:
        r = c.post("/analyze", files={"image": ("x.png", png(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert len(body["embedding"]) == 4 and body["ocr"][0]["text"] == "МУСКАТЕЛЬ БЕЛЫЙ"


def test_analyze_without_ocr_engine():
    with client() as c:
        body = c.post("/analyze", files={"image": ("x.png", png(), "image/png")}).json()
    assert body["ocr"] == [] and len(body["embedding"]) == 4


def test_rerank_endpoint():
    cands = [
        {"slug": "a", "name": "Мускат белый", "winery": "М", "category": "Белое", "visual": 0.86},
        {"slug": "b", "name": "Мускатель белый", "winery": "М", "category": "Белое", "visual": 0.85},
    ]
    ocr = [{"text": "МУСКАТЕЛЬ", "conf": 0.99, "cx": 0.5, "cy": 0.5}]
    with client() as c:
        r = c.post("/rerank", json={"ocr": ocr, "candidates": cands, "alpha": 0.1, "beta": 0.02})
    assert r.status_code == 200
    assert [x["slug"] for x in r.json()["candidates"]] == ["b", "a"]


def test_rerank_requires_visual_score():
    with client() as c:
        r = c.post("/rerank", json={"ocr": [], "candidates": [{"slug": "a"}]})
    assert r.status_code == 422


class SlowOcr:
    def read(self, im):
        import time
        time.sleep(0.5)
        return [{"text": "late", "conf": 1.0}]


def test_analyze_answers_without_ocr_when_ocr_is_slow(monkeypatch):
    monkeypatch.setattr("wine_ml.service.OCR_TIMEOUT_S", 0.1)
    with TestClient(create_app(lambda: Fake(), lambda: SlowOcr())) as c:
        body = c.post("/analyze", files={"image": ("x.png", png(), "image/png")}).json()
    assert body["ocr"] == [] and body["ocr_timeout"] is True and len(body["embedding"]) == 4

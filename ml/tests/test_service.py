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

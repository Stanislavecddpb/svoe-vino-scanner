import json
import urllib.error

import pytest
from PIL import Image

from wine_ml.ocr_yandex import YandexOcrEngine, parse_reply

REPLY = {"result": {"textAnnotation": {
    "width": "1000", "height": "800",
    "blocks": [{"lines": [
        {"text": "МУСКАТЕЛЬ", "boundingBox": {"vertices": [
            {"x": "400", "y": "300"}, {"x": "400", "y": "340"}, {"x": "600", "y": "340"}, {"x": "600", "y": "300"}]}},
        {"text": "  ", "boundingBox": {"vertices": [{"x": "0", "y": "0"}]}},
    ]}],
}}}


def test_parse_reply_normalizes_boxes():
    items = parse_reply(REPLY, (1000, 800))
    assert items == [{"text": "МУСКАТЕЛЬ", "conf": 1.0, "cx": 0.5, "cy": 0.4, "h": 0.05}]


def test_read_sends_jpeg_with_auth_and_parses(monkeypatch):
    sent = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(REPLY).encode()

    def fake_urlopen(req, timeout):
        sent["headers"] = dict(req.header_items())
        sent["body"] = json.loads(req.data)
        return Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    items = YandexOcrEngine("KEY", "FOLDER").read(Image.new("RGBA", (50, 40), "red"))
    assert items[0]["text"] == "МУСКАТЕЛЬ"
    assert sent["headers"]["Authorization"] == "Api-Key KEY"
    assert sent["headers"]["X-folder-id"] == "FOLDER"
    assert sent["body"]["mimeType"] == "JPEG" and sent["body"]["languageCodes"] == ["ru", "en"]


def test_read_degrades_to_no_text_on_network_error(monkeypatch):
    def boom(req, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert YandexOcrEngine("KEY", "FOLDER").read(Image.new("RGB", (10, 10))) == []


def test_requires_credentials():
    with pytest.raises(ValueError):
        YandexOcrEngine("", "folder")

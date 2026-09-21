import io

import pytest
from PIL import Image

from wine_ml.preprocess import load_image, normalize_image


def test_rgba_to_square_rgb_white_bg():
    im = Image.new("RGBA", (100, 300), (0, 0, 0, 0))
    im.paste((200, 0, 0, 255), (30, 50, 70, 250))
    out = normalize_image(im)
    assert out.mode == "RGB" and out.size[0] == out.size[1]
    assert out.getpixel((0, 0)) == (255, 255, 255)
    # transparent margin trimmed: the bottle fills the full height
    assert out.size[1] <= 210


def test_exif_rotation_applied():
    im = Image.new("RGB", (200, 100), (10, 20, 30))
    exif = im.getexif()
    exif[0x0112] = 6  # rotate 90
    b = io.BytesIO()
    im.save(b, "JPEG", exif=exif)
    out = normalize_image(Image.open(io.BytesIO(b.getvalue())))
    assert out.size == (200, 200)
    assert out.getpixel((100, 100))[0] < 40  # content kept


def test_large_image_downscaled():
    out = normalize_image(Image.new("RGB", (4000, 3000), "blue"))
    assert max(out.size) <= 1024


def test_load_image_rejects_garbage():
    with pytest.raises(ValueError):
        load_image(b"not an image")

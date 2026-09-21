"""Photo normalization shared by indexing, the embed service and evaluation.

Catalog references are studio shots (often transparent/white background, tall
bottle), field photos are phone shots (EXIF rotation, arbitrary aspect). We
bring both to the same shape before the model's own resize: upright RGB,
transparent -> white, near-white margins trimmed, padded to a white square.
Padding (not center-crop) keeps the whole label in frame.
"""
from __future__ import annotations

import io

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

MAX_SIDE = 1024
WHITE = (255, 255, 255)
TRIM_THRESHOLD = 16  # max channel difference from white still treated as background

try:  # optional HEIC support (iPhone photos)
    from pillow_heif import register_heif_opener  # type: ignore

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass


def load_image(data: bytes) -> Image.Image:
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ValueError("invalid image") from e
    return im


def _to_rgb_on_white(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, WHITE)
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB")


def _trim_white(im: Image.Image) -> Image.Image:
    diff = ImageChops.difference(im, Image.new("RGB", im.size, WHITE)).convert("L")
    mask = diff.point(lambda v: 255 if v > TRIM_THRESHOLD else 0)
    box = mask.getbbox()
    if not box:
        return im
    w, h = box[2] - box[0], box[3] - box[1]
    if w < 0.05 * im.width or h < 0.05 * im.height:  # almost empty: keep as is
        return im
    return im.crop(box)


def _pad_square(im: Image.Image) -> Image.Image:
    side = max(im.size)
    out = Image.new("RGB", (side, side), WHITE)
    out.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return out


def normalize_image(im: Image.Image) -> Image.Image:
    im = ImageOps.exif_transpose(im)
    im = _to_rgb_on_white(im)
    im = _trim_white(im)
    if max(im.size) > MAX_SIDE:
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return _pad_square(im)

"""Turn a clean catalog reference into a synthetic "field photo".

Used only for evaluation while no labeled field photos exist. Simulates what a
phone shot at the shelf does: perspective/tilt, partial framing, background,
lighting shift, glare, defocus and JPEG compression.
"""
from __future__ import annotations

import io
import random

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


def _perspective_coeffs(src: list[tuple[float, float]], dst: list[tuple[float, float]]) -> list[float]:
    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.array(rows, dtype=np.float64)
    b = np.array([c for p in src for c in p], dtype=np.float64)
    return np.linalg.solve(a, b).tolist()


def _random_perspective(im: Image.Image, rng: random.Random, strength: float = 0.12) -> Image.Image:
    w, h = im.size
    d = lambda s: rng.uniform(0, strength) * s  # noqa: E731
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = [(d(w), d(h)), (w - d(w), d(h)), (w - d(w), h - d(h)), (d(w), h - d(h))]
    return im.transform((w, h), Image.Transform.PERSPECTIVE, _perspective_coeffs(src, dst),
                        Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))


def _background(size: tuple[int, int], rng: random.Random) -> Image.Image:
    base = tuple(rng.randint(30, 230) for _ in range(3))
    arr = np.full((size[1], size[0], 3), base, dtype=np.int16)
    arr += np.random.default_rng(rng.randint(0, 2**31)).integers(-25, 25, arr.shape, dtype=np.int16)
    bg = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    return bg.filter(ImageFilter.GaussianBlur(rng.uniform(1, 6)))


def _glare(im: Image.Image, rng: random.Random) -> Image.Image:
    w, h = im.size
    layer = Image.new("L", im.size, 0)
    cx, cy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.2, 0.8) * h
    rx, ry = rng.uniform(0.05, 0.2) * w, rng.uniform(0.1, 0.35) * h
    ImageDraw.Draw(layer).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=rng.randint(120, 230))
    layer = layer.filter(ImageFilter.GaussianBlur(max(rx, ry) / 3))
    return Image.composite(Image.new("RGB", im.size, (255, 255, 255)), im, layer)


def _label_closeup(im: Image.Image, rng: random.Random) -> Image.Image:
    """Crop the label band of a bottle shot: a shelf photo is usually a label close-up."""
    box = im.getchannel("A").getbbox() or (0, 0, im.width, im.height)
    im = im.crop(box)
    w, h = im.size
    top = rng.uniform(0.35, 0.55) * h
    band = rng.uniform(0.3, 0.45) * h
    return im.crop((0, int(top), w, int(min(h, top + band))))


def field_like(ref: Image.Image, rng: random.Random, closeup_p: float = 0.5,
               max_side: int = 768) -> Image.Image:
    """Synthetic field photo from a reference image (deterministic for a given rng state).

    With probability ``closeup_p`` it is a label close-up (label fills the frame,
    like the public field photos), otherwise a whole-bottle shot.
    """
    im = ImageOps.exif_transpose(ref).convert("RGBA")
    im.thumbnail((max_side, max_side))  # 768: fast CV eval; ~2048: label text stays readable (OCR eval)
    closeup = rng.random() < closeup_p

    if closeup:
        im = _label_closeup(im, rng)
        im = im.resize((im.width * 2, im.height * 2), Image.Resampling.BICUBIC)
    else:  # partial framing: keep 70-100% of each side
        w, h = im.size
        cw, ch = int(w * rng.uniform(0.7, 1.0)), int(h * rng.uniform(0.7, 1.0))
        x0, y0 = rng.randint(0, w - cw), rng.randint(0, h - ch)
        im = im.crop((x0, y0, x0 + cw, y0 + ch))

    im = _random_perspective(im, rng)
    im = im.rotate(rng.uniform(-12, 12), Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))

    # place on a background with phone aspect 3:4
    if closeup:  # label spans 70-100% of the frame width
        canvas_w = int(im.width / rng.uniform(0.7, 1.0))
        canvas_h = max(int(canvas_w * 4 / 3), im.height + 4)
    else:  # bottle fills 55-95% of the frame height
        canvas_h = int(im.height / rng.uniform(0.55, 0.95))
        canvas_w = max(int(canvas_h * 0.75), im.width + 4)
    canvas = _background((canvas_w, canvas_h), rng)
    ox = rng.randint(0, canvas_w - im.width)
    oy = rng.randint(0, canvas_h - im.height)
    canvas.paste(im, (ox, oy), im.getchannel("A"))
    out = canvas

    out = ImageEnhance.Brightness(out).enhance(rng.uniform(0.7, 1.3))
    out = ImageEnhance.Contrast(out).enhance(rng.uniform(0.7, 1.3))
    out = ImageEnhance.Color(out).enhance(rng.uniform(0.7, 1.2))
    if rng.random() < 0.5:
        out = _glare(out, rng)
    if rng.random() < 0.5:
        out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.5, 2.0)))

    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=rng.randint(40, 85))
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")

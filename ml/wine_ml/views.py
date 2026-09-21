"""Several views of a catalog reference: the whole bottle plus label-band crops.

Field photos are usually label close-ups while references show the whole
bottle; indexing label crops as extra vectors narrows that scale gap. A wine's
score at search time is the max over its views.

Bands are fractions of the bottle's bounding box height (full width is kept).
They are deliberately wider than / offset from the synthetic close-up crop in
augment.py (35-55% start, 30-45% tall) so the index is not tuned to the test.
"""
from __future__ import annotations

from PIL import Image, ImageOps

from wine_ml.preprocess import MAX_SIDE, _pad_square, _to_rgb_on_white, _trim_white, normalize_image

LABEL_BANDS: dict[str, tuple[float, float]] = {
    "label_mid": (0.30, 0.70),
    "label_low": (0.45, 0.95),
}
VIEWS: tuple[str, ...] = ("full", *LABEL_BANDS)

# search score = (1 - w) * full + w * best label view (web: env LABEL_WEIGHT)
LABEL_WEIGHT = 0.5


def reference_views(ref: Image.Image, views: list[str] | tuple[str, ...] = VIEWS) -> dict[str, Image.Image]:
    """Normalized (square RGB) images for the requested views, in the requested order."""
    unknown = set(views) - set(VIEWS)
    if unknown:
        raise ValueError(f"unknown views: {sorted(unknown)}")
    out: dict[str, Image.Image] = {}
    bottle = None
    for name in views:
        if name == "full":
            out[name] = normalize_image(ref)
            continue
        if bottle is None:
            bottle = _trim_white(_to_rgb_on_white(ImageOps.exif_transpose(ref)))
        top, bottom = LABEL_BANDS[name]
        h = bottle.height
        band = bottle.crop((0, int(top * h), bottle.width, max(int(bottom * h), int(top * h) + 1)))
        band.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        out[name] = _pad_square(band)
    return out

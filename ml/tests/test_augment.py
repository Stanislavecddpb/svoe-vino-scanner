import random

import numpy as np
from PIL import Image

from wine_ml.augment import field_like


def ref() -> Image.Image:
    im = Image.new("RGBA", (200, 500), (0, 0, 0, 0))
    im.paste((120, 20, 40, 255), (50, 20, 150, 480))
    im.paste((240, 230, 200, 255), (60, 250, 140, 400))  # label
    return im


def test_output_is_rgb_and_deterministic():
    a = field_like(ref(), random.Random(7))
    b = field_like(ref(), random.Random(7))
    assert a.mode == "RGB"
    assert np.array_equal(np.asarray(a), np.asarray(b))


def test_differs_from_reference_and_between_seeds():
    a = np.asarray(field_like(ref(), random.Random(1)).resize((64, 64)), dtype=np.float32)
    b = np.asarray(field_like(ref(), random.Random(2)).resize((64, 64)), dtype=np.float32)
    r = np.asarray(ref().convert("RGB").resize((64, 64)), dtype=np.float32)
    assert np.abs(a - b).mean() > 5
    assert np.abs(a - r).mean() > 5

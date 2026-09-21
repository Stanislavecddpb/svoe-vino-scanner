from PIL import Image

from wine_ml.views import VIEWS, reference_views


def bottle() -> Image.Image:
    """Transparent canvas, bottle 100x400 at (50, 50); red label at 60-80% of bottle height."""
    im = Image.new("RGBA", (200, 500), (0, 0, 0, 0))
    im.paste((20, 60, 20, 255), (50, 50, 150, 450))
    im.paste((220, 0, 0, 255), (50, 290, 150, 370))
    return im


def test_all_views_square_rgb():
    views = reference_views(bottle())
    assert list(views) == list(VIEWS)
    for v in views.values():
        assert v.mode == "RGB" and v.size[0] == v.size[1]


def test_views_subset():
    assert list(reference_views(bottle(), ["full"])) == ["full"]


def red_share(im: Image.Image) -> float:
    px = list(im.convert("RGB").getdata())
    return sum(1 for r, g, b in px if r > 180 and g < 60) / len(px)


def test_label_views_zoom_into_label_band():
    views = reference_views(bottle())
    # the label occupies a larger part of the label crops than of the whole bottle
    assert red_share(views["label_low"]) > 2 * red_share(views["full"])
    assert red_share(views["label_mid"]) > red_share(views["full"])

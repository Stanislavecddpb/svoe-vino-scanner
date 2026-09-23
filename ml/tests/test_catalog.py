import os

from PIL import Image

from wine_ml.catalog import build_catalog, is_product_shot, name_key, strip_hash


def test_name_key_translit_and_punct():
    assert name_key("Цимлянское Рислинг") == name_key("Tsimlyanskoe_Risling")
    assert name_key("4300_tlKHpEg") == name_key("4300_tl_K_Hp_Eg")


def test_name_key_tolerates_strapi_transliteration_variants():
    # CSV keeps the Cyrillic original, Strapi stores transliterated names with other rules
    assert name_key("Черная Львица") == name_key("Chernaya_Lvicza")      # ц -> cz
    assert name_key("Агора_Мускат Черный") == name_key("Agora_Muskat_Chernyj")  # ый -> yj
    assert name_key("Овощи") == name_key("ovoshhi")                        # щ -> shh
    assert name_key("Сухое") == name_key("sukhoe")                         # х -> kh
    assert name_key("Мускат") != name_key("Мускатель")


def test_strip_hash_repeated():
    assert strip_hash("Aristov_Roze_cc598880d5_2335683dfd") == "Aristov_Roze"


def bottle_png(path, color=(90, 20, 30)):
    im = Image.new("RGBA", (120, 360), (0, 0, 0, 0))
    im.paste((*color, 255), (40, 20, 80, 340))
    im.save(path)


def banner_png(path, color=(30, 120, 200)):
    im = Image.new("RGB", (400, 200), color)
    im.paste((220, 180, 40), (50, 40, 350, 160))
    im.save(path)


def test_is_product_shot(tmp_path):
    bottle_png(tmp_path / "b.png")
    banner_png(tmp_path / "x.png")
    assert is_product_shot(tmp_path / "b.png")
    assert not is_product_shot(tmp_path / "x.png")


def row(slug, photo):
    return {"Slug": slug, "Название фото": photo, "Название вина": f" {slug} ",
            "Категория": "", "Цвет": "", "Регион": "", "Сорт винограда": "",
            "Описание": "", "Винодельня": ""}


def test_build_catalog_rules(tmp_path):
    bottle_png(tmp_path / "a_0123456789.png")
    bottle_png(tmp_path / "thumbnail_a_0123456789.png")                    # derivative, ignored
    # generic name reused by unrelated uploads: the single product shot wins
    banner_png(tmp_path / "Screenshot_7_0123456789.png")
    bottle_png(tmp_path / "Screenshot_7_abcdefabcd.png", color=(200, 30, 30))
    banner_png(tmp_path / "Screenshot_7_1111111111.png")
    # re-uploads of the same bottle: the newest file wins
    bottle_png(tmp_path / "c_0123456789.png", color=(10, 10, 10))
    bottle_png(tmp_path / "c_abcdefabcd.png", color=(20, 20, 20))
    os.utime(tmp_path / "c_0123456789.png", (1_000_000, 1_000_000))
    os.utime(tmp_path / "c_abcdefabcd.png", (2_000_000, 2_000_000))
    # only banners behind a name: still ambiguous
    banner_png(tmp_path / "e_0123456789.png")
    banner_png(tmp_path / "e_abcdefabcd.png", color=(200, 60, 60))
    # Strapi transliteration differs from ours
    bottle_png(tmp_path / "Chernaya_Lvicza_0123456789.png")
    rows = [row("a", "a.webp"), row("a", "a.webp"), row("b", "Screenshot_7.webp"), row("c", "c.webp"),
            row("d1", "a2.webp"), row("d2", "a2.webp"), row("e", "e.webp"),
            row("f", "missing.webp"), row("g", "Черная Львица.webp")]
    bottle_png(tmp_path / "a2_0123456789.png")
    wines, excl = build_catalog(rows, sorted(tmp_path.iterdir()))
    by = {w["slug"]: w for w in wines}
    assert sorted(by) == ["a", "b", "c", "d1", "d2", "g"]
    assert by["a"]["src_file"].name == "a_0123456789.png" and by["a"]["mapping"] == "exact"
    assert by["b"]["src_file"].name == "Screenshot_7_abcdefabcd.png" and by["b"]["mapping"] == "product_shot"
    assert by["c"]["src_file"].name == "c_abcdefabcd.png" and by["c"]["mapping"] == "newest_reupload"
    assert by["d1"]["mapping"] == by["d2"]["mapping"] == "shared_photo"
    assert by["g"]["src_file"].name == "Chernaya_Lvicza_0123456789.png"
    assert {e["slug"]: e["reason"] for e in excl} == {"e": "ambiguous_file", "f": "file_not_found"}

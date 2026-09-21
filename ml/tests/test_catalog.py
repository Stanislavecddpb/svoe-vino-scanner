from wine_ml.catalog import build_catalog, name_key, strip_hash


def test_name_key_translit_and_punct():
    assert name_key("Цимлянское Рислинг") == "tsimlyanskoerisling"
    assert name_key("4300_tlKHpEg") == name_key("4300_tl_K_Hp_Eg")


def test_strip_hash_repeated():
    assert strip_hash("Aristov_Roze_cc598880d5_2335683dfd") == "Aristov_Roze"


def row(slug, photo):
    return {"Slug": slug, "Название фото": photo, "Название вина": f" {slug} ",
            "Категория": "", "Цвет": "", "Регион": "", "Сорт винограда": "",
            "Описание": "", "Винодельня": ""}


def test_build_catalog_rules(tmp_path):
    (tmp_path / "a_0123456789.webp").write_bytes(b"A")
    (tmp_path / "thumbnail_a_0123456789.webp").write_bytes(b"a")  # derivative, ignored
    (tmp_path / "b_0123456789.webp").write_bytes(b"B1")
    (tmp_path / "b_abcdefabcd.webp").write_bytes(b"B2")  # ambiguous, different bytes
    (tmp_path / "c_0123456789.webp").write_bytes(b"C")
    (tmp_path / "c_abcdefabcd.webp").write_bytes(b"C")  # identical bytes -> ok
    rows = [row("a", "a.webp"), row("a", "a.webp"), row("b", "b.webp"), row("c", "c.webp"),
            row("d1", "d.webp"), row("d2", "d.webp"), row("e", "missing.webp")]
    wines, excl = build_catalog(rows, sorted(tmp_path.iterdir()))
    assert sorted(w["slug"] for w in wines) == ["a", "c"]
    a = next(w for w in wines if w["slug"] == "a")
    assert a["name"] == "a" and a["src_file"].name == "a_0123456789.webp"
    reasons = {e["slug"]: e["reason"] for e in excl}
    assert reasons == {"b": "ambiguous_file", "d1": "shared_photo",
                       "d2": "shared_photo", "e": "file_not_found"}

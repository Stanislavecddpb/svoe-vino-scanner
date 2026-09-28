from wine_ml.analogs import AnalogFinder, compatible, is_sparkling, sugar_of


def wine(slug, winery, category="Белое", grapes="Совиньон Блан", region="Крым", name=None, desc=""):
    return {"slug": slug, "name": name or slug, "winery": winery, "category": category,
            "grapes": grapes, "region": region, "description": desc}


def test_sugar_and_sparkling_from_slug_and_name():
    assert sugar_of(wine("x-beloe-polusladkoe-12", "A")) == "полусладкое"
    assert sugar_of(wine("y", "A", name="Кюве экстра брют")) == "экстра брют"
    assert sugar_of(wine("pobeda", "A")) is None
    assert is_sparkling(wine("abrau-bryut", "A")) and not is_sparkling(wine("x-suhoe", "A"))


def test_compatible_rules():
    a = wine("a-suhoe", "A")
    assert not compatible(a, wine("b-suhoe", "A"))                       # same winery
    assert not compatible(a, wine("c-suhoe", "C", category="Красное"))    # other colour
    assert not compatible(a, wine("d-bryut", "D"))                        # sparkling vs still
    assert not compatible(a, wine("e-polusladkoe", "E"))                  # other sweetness
    assert compatible(a, wine("f", "F"))                                  # unknown sweetness = dry still wine
    assert not compatible(wine("g-polusladkoe", "G"), wine("h", "H"))     # ... so it is not a semi-sweet analog


def test_analogs_rank_same_grape_and_notes_one_per_winery():
    wines = [
        wine("src-suhoe", "Src", desc="Аромат крыжовника, цитруса и свежескошенной травы"),
        wine("b1-suhoe", "B", desc="Ноты крыжовника и цитруса, травянистые оттенки"),
        wine("b2-suhoe", "B", desc="Ноты крыжовника, цитруса и травы"),                 # same winery as b1
        wine("c-suhoe", "C", grapes="Шардоне", desc="Сливочные тона, ваниль, дуб"),
        wine("d-suhoe", "D", region="Кубань", desc="Ноты цитруса и крыжовника"),
        wine("e-krasnoe", "E", category="Красное", desc="Ноты крыжовника и цитруса"),
        *[wine(f"red{i}", f"R{i}", category="Красное", grapes="Мерло", desc="Вишня, слива, табак") for i in range(6)],
    ]
    out = AnalogFinder(wines).analogs("src-suhoe", k=5)
    slugs = [o["slug"] for o in out]
    assert slugs[0] in ("b1-suhoe", "b2-suhoe") and "e-krasnoe" not in slugs
    assert len({s[:2] for s in slugs}) == len(slugs)                        # one per winery
    assert slugs.index("c-suhoe") > slugs.index("d-suhoe")                  # other grape ranks lower
    assert "Тот же сорт — Совиньон Блан" in out[0]["reason"] and "крыжовн" in out[0]["reason"]

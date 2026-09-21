import json
from pathlib import Path

from wine_ml.text_match import (
    conflicts,
    fuzzy_sim,
    rerank,
    tokens,
    translit,
)


def test_translit_and_tokens():
    assert translit("Мускатель белый") == "muskatel belyy"
    assert tokens("МУСКАТЕЛЬ, Массандра 2023 0,75л") == ["muskatel", "massandra", "2023", "075l"]
    assert tokens("a на 15") == []  # too short, noise


def test_fuzzy_sim_tolerates_ocr_errors_but_not_other_words():
    assert fuzzy_sim("muskatea", "muskatel") >= 0.8   # "МУСКАТЕАЬ" as read by OCR
    assert fuzzy_sim("beayy", "belyy") >= 0.8         # "БЕАЫЙ"
    assert fuzzy_sim("muskat", "muskatel") < 0.8      # a different word


# Real EasyOCR output (text, confidence, normalized box centre/height) for the public query photos.
# 02eef911.webp: Massandra "Мускатель белый" in the centre, the neighbour on the right is
# "Мускат белый Красного камня" and its "МУСКАТ КРАСНОГО" is read too (larger font than the target!).
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "ocr_public_queries.json").read_text(encoding="utf-8"))
MASSANDRA_OCR = FIXTURE["02eef911.webp"]


def cand(slug, name, visual, category="Белое"):
    return {"slug": slug, "name": name, "winery": "Массандра", "grapes": None,
            "category": category, "visual": visual}


MASSANDRA_TOP = [
    cand("massandra-muskat-belyy-yuzhnoberezhnyy-beloe-sladkoe-16", "Мускат белый Южнобережный", 0.855),
    cand("massandra-muskatel-rozovyy-belye-sorta-vinograda-rozovoe-sladkoe-16", "Мускатель розовый", 0.8463, "Розовое"),
    cand("massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16", "Мускатель белый", 0.8304),
    cand("massandra-muskat", "Мускат", 0.829),
    cand("massandra-muskat-belyy-krasnogo-kamnya-beloe-sladkoe-13", "Мускат белый красного камня", 0.8044),
]


def test_rerank_puts_the_wine_named_on_the_label_first():
    out = rerank(MASSANDRA_OCR, MASSANDRA_TOP, alpha=0.1, beta=0.02)
    assert out[0]["slug"] == "massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16"
    assert [c["final"] for c in out] == sorted((c["final"] for c in out), reverse=True)
    assert out[0]["text"] > out[1]["text"]


def test_rerank_without_ocr_keeps_visual_order():
    out = rerank([], MASSANDRA_TOP, alpha=0.1, beta=0.02)
    assert [c["slug"] for c in out] == [c["slug"] for c in MASSANDRA_TOP]
    assert all(c["final"] == c["visual"] for c in out)


def test_conflicts_color_and_sugar():
    ocr = tokens("БРЮТ белое")
    assert conflicts(ocr, tokens("Игристое розовое брют")) == 1      # colour differs
    assert conflicts(ocr, tokens("Игристое белое полусладкое")) == 1  # sugar differs
    assert conflicts(ocr, tokens("Игристое белое брют")) == 0
    assert conflicts(ocr, tokens("Игристое")) == 0                    # nothing to contradict

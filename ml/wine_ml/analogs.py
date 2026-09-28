"""Analogs from other wineries: wines of the same style that could replace the found one.

A candidate must come from another winery, have the same colour category
(белое / красное / розовое / оранжевое), the same type (sparkling / still) and a
compatible sweetness. Candidates are ranked by grape overlap, similarity of the
tasting description and region; at most one wine per winery. Each analog gets a
short human-readable reason ("Тот же сорт — Совиньон Блан · сухое белое · Крым ·
общие ноты: крыжовник, цитрус").
"""
from __future__ import annotations

import math
import re
from collections import Counter

W_GRAPES, W_TEXT, W_REGION = 0.5, 0.35, 0.15
NOTE_MAX_SHARE = 0.5  # a word shown as a shared note must occur in at most this share of descriptions

SUGAR_PATTERNS = [  # order matters: the first match wins
    ("экстра брют", r"ekstra.?bryut|экстра.?брют|extra.?brut|zero.?dosage|зеро.?дозаж|brut.?nature"),
    ("брют", r"bryut|брют|brut"),
    ("полусладкое", r"polusladk|полуслад"),
    ("полусухое", r"polusuh|полусух"),
    ("сладкое", r"sladk|сладк|desert|десерт|dessert"),
    ("сухое", r"suhoe|suhoy|сухое|сухой"),
]
SPARKLING = r"bryut|брют|brut|igrist|игрист|petnat|pet.?nat|пет.?нат|shampansk|шампанск|frizzante|prosecco|spumante|crémant|cremant"
STOP = set("вино вина вкус вкусе аромат аромате ароматы букет цвет цвета цвете оттенки оттенками тона тонами ноты нотки нотами "
           "послевкусие послевкусии очень легкие легкий легкое хорошо хорошей хороший также которые который этого этот "
           "имеет вином винограда винограде характере структура структуры сорта".split())


def sugar_of(w: dict) -> str | None:
    s = f"{w.get('slug', '')} {w.get('name', '')}".lower()
    for label, pat in SUGAR_PATTERNS:
        if re.search(pat, s):
            return label
    return None


def is_sparkling(w: dict) -> bool:
    return bool(re.search(SPARKLING, f"{w.get('slug', '')} {w.get('name', '')}".lower()))


def grapes_of(w: dict) -> set[str]:
    return {g.strip().lower().replace("ё", "е") for g in re.split(r"[,;/]", w.get("grapes") or "") if g.strip()}


def _words(text: str) -> list[str]:
    return [t for t in re.findall(r"[а-яёa-z]{4,}", (text or "").lower().replace("ё", "е")) if t not in STOP]


def _stem(word: str) -> str:
    return word[:5]  # crude Russian stemming: "вишня/вишни/вишневый" -> "вишн"


def style_sugar(w: dict) -> str:
    """Sweetness for matching; unknown means the usual style: dry still wine, brut sparkling."""
    return sugar_of(w) or ("брют" if is_sparkling(w) else "сухое")


# a shared "note" must read as an aroma in the genitive ("ноты крыжовника, лайма, фруктов"),
# not an adjective or a generic word ("ароматом", "хрустящей", "насыщенный")
_NOTE_OK = re.compile(r"(а|я|и|ы|ов)$")
_NOTE_BAD = re.compile(r"(ми|ие|ые|ого|его|ей|ой)$")


def _is_note(word: str) -> bool:
    return bool(_NOTE_OK.search(word)) and not _NOTE_BAD.search(word) and not word.startswith(("арома", "нот", "тон"))


def compatible(a: dict, b: dict) -> bool:
    if a["slug"] == b["slug"] or (a.get("winery") or "") == (b.get("winery") or ""):
        return False
    if (a.get("category") or "") != (b.get("category") or ""):
        return False
    if is_sparkling(a) != is_sparkling(b):
        return False
    return style_sugar(a) == style_sugar(b)


class AnalogFinder:
    def __init__(self, wines: list[dict]):
        self.wines = wines
        self.by_slug = {w["slug"]: w for w in wines}
        docs = {w["slug"]: [_stem(t) for t in _words(w.get("description"))] for w in wines}
        df = Counter(s for toks in docs.values() for s in set(toks))
        n = len(wines)
        self.idf = {s: math.log((n + 1) / (d + 1)) + 1 for s, d in df.items()}
        self.df_share = {s: d / n for s, d in df.items()}
        self.vec = {}
        for slug, toks in docs.items():
            tf = Counter(toks)
            v = {s: c * self.idf[s] for s, c in tf.items()}
            norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
            self.vec[slug] = {s: x / norm for s, x in v.items()}
        # a readable word for every stem (most frequent surface form)
        forms: dict[str, Counter] = {}
        for w in wines:
            for t in _words(w.get("description")):
                forms.setdefault(_stem(t), Counter())[t] += 1
        self.word = {s: c.most_common(1)[0][0] for s, c in forms.items()}

    def _text_sim(self, a: str, b: str) -> tuple[float, list[str]]:
        va, vb = self.vec[a], self.vec[b]
        common = [(va[s] * vb[s], s) for s in va.keys() & vb.keys()]
        common.sort(reverse=True)
        # readable shared notes: skip words that occur in most descriptions ("фрукты", "ягоды")
        notes = [self.word[s] for _, s in common if self.df_share[s] <= NOTE_MAX_SHARE and _is_note(self.word[s])][:3]
        return sum(x for x, _ in common), notes

    def score(self, a: dict, b: dict) -> tuple[float, str]:
        ga, gb = grapes_of(a), grapes_of(b)
        grape = len(ga & gb) / len(ga | gb) if ga | gb else 0.0
        text, notes = self._text_sim(a["slug"], b["slug"])
        region = 1.0 if a.get("region") and a.get("region") == b.get("region") else 0.0
        total = W_GRAPES * grape + W_TEXT * text + W_REGION * region
        parts = []
        shared = [g for g in (b.get("grapes") or "").split(",") if g.strip().lower().replace("ё", "е") in ga]
        if shared:
            parts.append(("Тот же сорт — " if len(shared) == 1 else "Те же сорта — ") + ", ".join(s.strip() for s in shared[:3]))
        style = " ".join(x for x in (sugar_of(b), (b.get("category") or "").lower()) if x)
        if style:
            parts.append(style)
        if region:
            parts.append(b["region"])
        if notes:
            parts.append("ноты " + ", ".join(notes))
        return total, " · ".join(parts)

    def analogs(self, slug: str, k: int = 6) -> list[dict]:
        a = self.by_slug[slug]
        scored = []
        for b in self.wines:
            if compatible(a, b):
                s, reason = self.score(a, b)
                scored.append((s, b, reason))
        scored.sort(key=lambda x: -x[0])
        out, seen = [], set()
        for s, b, reason in scored:
            if b.get("winery") in seen:
                continue
            seen.add(b.get("winery"))
            out.append({"slug": b["slug"], "score": round(s, 4), "reason": reason})
            if len(out) == k:
                break
        return out

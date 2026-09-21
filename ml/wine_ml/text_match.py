"""Re-rank visual candidates by the text read on the label (OCR).

CV finds the right label series; within a series wines differ by words
(sugar, colour, grape, year) that CV barely sees. For each candidate we check
how much of its name/winery is confirmed by OCR (recall) and how much of the
informative OCR text it explains (precision), then add the F1 to the visual
score and subtract a penalty for contradictions (e.g. label says "брют",
candidate is "полусладкое").

Details that matter on real shelf photos:
- OCR misreads letters ("МУСКАТЕАЬ", "БЕАЫЙ") -> fuzzy token match;
- labels are in Cyrillic or Latin, slugs are transliterated -> everything is
  compared in Latin transliteration;
- neighbour bottles are read too -> OCR tokens are weighted by distance from
  the frame centre (the scanned label is usually centred);
- words shared by all candidates ("Массандра") do not discriminate -> IDF
  weights computed within the candidate list.
"""
from __future__ import annotations

import math
import re

_TRANSLIT = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p",
     "r", "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"],
))

FUZZY_MIN = 0.8        # normalized Levenshtein similarity for a token match
CENTER_SIGMA_X = 0.2   # OCR token weight falls off with horizontal distance from the centre
CENTER_SIGMA_Y = 0.35

# Values that contradict each other within a group (colour, sugar).
GROUPS: dict[str, dict[str, set[str]]] = {
    "color": {
        "white": {"belyy", "beloe", "belaya", "belogo", "white", "blanc", "bianco"},
        "red": {"krasnoe", "krasnyy", "krasnaya", "red", "rosso", "rouge"},
        "rose": {"rozovoe", "rozovyy", "rozovaya", "rose", "roze", "rosato"},
        "orange": {"oranzhevoe", "oranzhevyy", "orange"},
    },
    "sugar": {
        "brut": {"bryut", "brut"},
        "dry": {"suhoe", "suhoy", "sukhoe", "dry", "secco"},
        "semi_dry": {"polusuhoe", "polusuhoy", "demisec"},
        "semi_sweet": {"polusladkoe", "polusladkiy", "semisweet"},
        "sweet": {"sladkoe", "sladkiy", "sweet", "dolce"},
    },
}
YEAR_RE = re.compile(r"^20[0-3]\d$")


def translit(text: str) -> str:
    return "".join(_TRANSLIT.get(c, c) for c in text.lower())


def tokens(text: str | None) -> list[str]:
    """Latin tokens of length >= 3 (plus 4-digit years); '0,75' -> '075'."""
    if not text:
        return []
    s = re.sub(r"(?<=\d)[.,](?=\d)", "", translit(text))
    return [t for t in re.findall(r"[a-z0-9]+", s) if len(t) >= 3]


def _lev(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def fuzzy_sim(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b or abs(len(a) - len(b)) > max(len(a), len(b)) * (1 - FUZZY_MIN):
        return 0.0
    return 1 - _lev(a, b) / max(len(a), len(b))


def _group_values(toks: list[str]) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for group, values in GROUPS.items():
        for value, words in values.items():
            if any(fuzzy_sim(t, w) >= FUZZY_MIN for t in toks for w in words):
                found.setdefault(group, set()).add(value)
    years = {t for t in toks if YEAR_RE.match(t)}
    if years:
        found["year"] = years
    return found


def conflicts(ocr_tokens: list[str], candidate_tokens: list[str]) -> int:
    """Number of groups (colour, sugar, year) where the label and the candidate disagree."""
    seen, cand = _group_values(ocr_tokens), _group_values(candidate_tokens)
    return sum(1 for g, v in seen.items() if g in cand and not (v & cand[g]))


def _ocr_weighted_tokens(ocr: list[dict]) -> list[tuple[str, float]]:
    out = []
    for item in ocr:
        w = float(item.get("conf", 1.0))
        if "cx" in item:
            dx, dy = item["cx"] - 0.5, item.get("cy", 0.5) - 0.5
            w *= math.exp(-dx * dx / (2 * CENTER_SIGMA_X ** 2) - dy * dy / (2 * CENTER_SIGMA_Y ** 2))
        out += [(t, w) for t in tokens(item["text"])]
    return out


def candidate_name_tokens(c: dict) -> list[str]:
    """What is printed on a label: wine name and winery."""
    return list(dict.fromkeys(tokens(c.get("name")) + tokens(c.get("winery"))))


def candidate_attr_tokens(c: dict) -> list[str]:
    """Attributes used for contradictions: name, category and slug (slug carries colour/sugar)."""
    return tokens(c.get("name")) + tokens(c.get("category")) + tokens((c.get("slug") or "").replace("-", " "))


def rerank(ocr: list[dict], candidates: list[dict], alpha: float, beta: float) -> list[dict]:
    """Candidates (dicts with 'visual' score) -> copies with 'text', 'conflicts', 'final', sorted by final."""
    ocr_toks = _ocr_weighted_tokens(ocr)
    names = [candidate_name_tokens(c) for c in candidates]
    k = len(candidates)
    df: dict[str, int] = {}
    for toks in names:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log((k + 1) / (d + 0.5)) for t, d in df.items()}

    # best OCR evidence for every candidate token: (similarity * OCR weight, index of OCR token)
    def evidence(t: str) -> tuple[float, int]:
        best, idx = 0.0, -1
        for i, (o, w) in enumerate(ocr_toks):
            s = fuzzy_sim(t, o)
            if s >= FUZZY_MIN and s * w > best:
                best, idx = s * w, i
        return best, idx

    ev = {t: evidence(t) for t in idf}
    # informative OCR tokens = those that confirm some candidate token; their weight = max idf they confirm
    informative: dict[int, float] = {}
    for t, (s, i) in ev.items():
        if i >= 0:
            informative[i] = max(informative.get(i, 0.0), idf[t] * ocr_toks[i][1])
    info_total = sum(informative.values())

    ocr_plain = [t for t, _ in ocr_toks]
    out = []
    for c, toks in zip(candidates, names):
        total = sum(idf[t] for t in toks)
        matched = sum(idf[t] * ev[t][0] for t in toks)
        recall = matched / total if total else 0.0
        explained = sum(informative[ev[t][1]] for t in toks if ev[t][1] in informative)
        precision = min(1.0, explained / info_total) if info_total else 0.0
        text = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
        n_conf = conflicts(ocr_plain, candidate_attr_tokens(c)) if ocr_plain else 0
        out.append({**c, "text": round(text, 4), "conflicts": n_conf,
                    "final": round(c["visual"] + alpha * text - beta * n_conf, 4)})
    return sorted(out, key=lambda c: c["final"], reverse=True)

"""Ranking of candidate lines by more than metre: sense, novelty, endings, clichés.

The review batch of 2026-10-09 (docs/research/research_notes/calaveritas_quality_audit_2026-10-09.md)
showed what a metre-only ranking produces: 96% of rhyme-closing Spanish lines ended on one of the six
most frequent words of their family, 37% of stanzas opened on a Death epithet, 7.7% of lines ended on
a word tacked on after a comma, and trait labels were pasted in verbatim. The checks here follow
PoesIA's line scorer (``evaluation/metrics.py``: novelty, end-word, cliché, theme) without its
embedding model, so they run inside the small container: theme is word overlap with the stanza's
scene, novelty is character-trigram overlap with earlier lines.
"""

from __future__ import annotations

import re
from collections import Counter

from poesia.quality import gates
from poesia.quality.diversity import RecentEndings as _SharedRecent

CLICHES = {
    "es": (
        "llega la flaca",
        "llegó la flaca",
        "llega la catrina",
        "llegó la catrina",
        "la muerte llega",
        "llegó la muerte",
        "llega la muerte",
        "con su guadaña",
        "sin prisa",
        "en vano",
        "a su puerta",
        "a tu puerta",
        "toca la puerta",
        "tocó la puerta",
        "tocó a la puerta",
        "le llegó la hora",
        "su hora llegó",
        "llegó su hora",
        "no hay escape",
        "no hay escapatoria",
        "se lo llevó",
        "se la llevó",
    ),
    "en": (
        "death came knocking",
        "came knocking",
        "at the door",
        "at your door",
        "with her scythe",
        "your time has come",
        "time to go",
        "no escape",
        "came for",
    ),
}

_EPITHETS = r"(?:catrina|calaca|flaca|muerte|huesuda|huesudita|parca|pelona|calavera|dientona)"
DEATH_OPENING = {
    "es": re.compile(rf"^[¡¿\"«]*\s*(?:y |pero |mas |ya )?(?:la |el )?{_EPITHETS}\b", re.I),
    "en": re.compile(
        r"^[\"“]*\s*(?:and |but |now )?(?:la catrina|catrina|lady death|death|the reaper)\b", re.I
    ),
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zà-ÿ'’]+", text.lower())


def tacked_on(line: str) -> bool:
    """True for a line whose last word stands alone after a comma (shared gate)."""
    return gates.tacked_on(line) is not None


def death_opening(line: str, language: str) -> bool:
    return bool(DEATH_OPENING[language].search(line.strip()))


def cliches(line: str, language: str) -> int:
    low = " ".join(_words(line))
    return sum(1 for c in CLICHES[language] if c in low)


def _trigrams(text: str) -> set[str]:
    s = " ".join(_words(text))
    return {s[i : i + 3] for i in range(max(0, len(s) - 2))}


def similarity(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def _stems(text: str) -> set[str]:
    return {w[:5] for w in _words(text) if len(w) >= 4}


def copied(line: str, material: str) -> bool:
    """True if the line pastes three or more consecutive words of a trait or detail."""
    m = _words(material)
    low = " ".join(_words(line))
    return any(" ".join(m[i : i + 3]) in low for i in range(len(m) - 2))


class RecentEndings(_SharedRecent):
    """End words of recent lines across poems (shared ``poesia.quality.diversity``)."""

    def add(self, words: list[str]) -> None:  # type: ignore[override] - takes end words
        super().add(words)


RECENT = RecentEndings()


def score_line(
    line: str,
    language: str,
    *,
    syllables: int,
    target: int,
    end_word: str,
    common_ends: set[str],
    scene: str,
    material: str,
    prior: list[str],
    opening: bool,
    recent: Counter[str] | None = None,
) -> float:
    """Higher is better. ``opening``: the line opens a stanza after the first one."""
    score = -1.0 * abs(syllables - target)
    overlap = len(_stems(line) & _stems(scene + " " + material))
    score += min(overlap, 3) * 0.4
    score -= 1.0 * cliches(line, language)
    if end_word in common_ends:
        score -= 0.6
    if recent:
        score -= min(recent.get(end_word, 0), 6) * 0.25
    if prior:
        sim = max(similarity(line, p) for p in prior)
        if sim > 0.4:
            score -= 2.0 * (sim - 0.4) / 0.6 + 0.5
    if material and copied(line, material):
        score -= 0.8
    if opening and death_opening(line, language):
        score -= 1.5
    return score

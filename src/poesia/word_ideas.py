"""Small suggestions first: words that rhyme with a line's partner (packaging/UX plan U6).

From the co-writing research behind docs/HACK_APERTUS_PLAN.md §2a: suggestions keep the poem
the author's own when they are small and requested. So "Ideas" first offers rhyme words, each
with why it fits; whole lines come from the model only on a second request.

Offline and deterministic. Candidates come from frequency-ranked word lists
(``poesia/wordlists/<lang>.txt``, the 40,000 most frequent words from wordfreq 3.1.1, data
CC BY-SA 4.0; see that folder's README), and every word offered is checked with the same
``rhyme_key`` the page uses to mark a rhyme, so a suggested word always passes the page's
check. English candidates come from CMUdict rhymes, ranked by the same list (scanning 40,000
English words takes minutes; CMUdict's rhyme lookup is instant).
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from typing import Any

_PUNCT = ".,;:!?¡¿«»\"'()[]—–-…“”‘’"

_WHY = {
    "es": "rima con «{partner}»",
    "en": "rhymes with “{partner}”",
    "it": "rima con «{partner}»",
}
_SYLL = {"es": ("sílaba", "sílabas"), "en": ("syllable", "syllables"), "it": ("sillaba", "sillabe")}


@cache
def _ranked(language: str) -> list[str]:
    text = resources.files("poesia.wordlists").joinpath(f"{language}.txt").read_text("utf-8")
    return [w for w in text.split("\n") if w]


@cache
def _rank(language: str) -> dict[str, int]:
    return {w: i for i, w in enumerate(_ranked(language))}


@cache
def _phonology(language: str) -> Any:
    from poesia.webapp import _phonology as phon

    return phon(language)


@cache
def _by_key(language: str) -> dict[str, list[str]]:
    """Rhyme key -> words in frequency order (es, it: a few hundred ms, once)."""
    phon = _phonology(language)
    index: dict[str, list[str]] = {}
    for word in _ranked(language):
        if len(word) < 2:
            continue
        key = phon.rhyme_key(word).consonant
        if key:
            index.setdefault(key, []).append(word)
    return index


def last_word(line: str) -> str:
    words = [w.strip(_PUNCT) for w in line.split()]
    words = [w for w in words if w]
    return words[-1].lower() if words else ""


def _candidates(language: str, partner_line: str, key: str) -> list[str]:
    if language != "en":
        return _by_key(language).get(key, [])
    import pronouncing  # type: ignore[import-untyped]

    rank = _rank("en")
    rhymes = {w for w in pronouncing.rhymes(last_word(partner_line)) if w in rank}
    return sorted(rhymes, key=rank.__getitem__)


def _syllables(word: str, language: str) -> int:
    from poesia.scansion_view import syllable_view

    try:
        view = syllable_view(word, language)
        return sum(len(w["syl"]) for w in view) or 1
    except Exception:
        return 1


_IT_VOWELS = set("aeiouàèéìíòóùú")


def _italian_stress_is_certain(word: str, syllables: int) -> bool:
    """True when the Italian rhyme key's stress is not a guess (see phonology.italian limits).

    Unmarked words stressed on the third-to-last syllable (*crescita*, *opera*) look like
    ordinary ones (*partita*, *maniera*) without a dictionary, and would be offered as false
    rhymes. Safe: up to two syllables, a written accent, or a closed second-to-last syllable
    (two consonants before the last vowel, not stop + l/r: *bellezza*, *profondo*).
    """
    if syllables <= 2 or any(c in "àèéìíòóùú" for c in word):
        return True
    core = word.rstrip("aeiou")  # drop the final vowel(s)
    cluster = ""
    for c in reversed(core):
        if c in _IT_VOWELS:
            break
        cluster = c + cluster
    return len(cluster) >= 2 and not (cluster[-1] in "lr" and cluster[-2] in "bcdfgptv")


def rhyme_words(
    language: str, partner_line: str, avoid: set[str] | None = None, k: int = 8
) -> list[dict[str, Any]]:
    """Up to ``k`` common words that rhyme with ``partner_line``, most frequent first.

    ``avoid`` holds words not to offer (the poem's other line endings). Each item is
    ``{"word", "syllables", "why"}``; ``why`` is in the poem's language.
    """
    phon = _phonology(language)
    key = phon.rhyme_key(partner_line).consonant if partner_line.strip() else ""
    if not key:
        return []
    partner = last_word(partner_line)
    skip = {partner, *(w.lower() for w in (avoid or set()))}
    out: list[dict[str, Any]] = []
    ranked = _candidates(language, partner_line, key)
    # Content words first: the most frequent ~150 are mostly function words ("con", "son").
    rank = _rank(language)
    ranked = sorted(ranked, key=lambda w: rank.get(w, 10**6) < 150)
    for word in ranked:
        # Not the same word, nor the partner with a prefix ("venir"/"prevenir" is weak rhyme).
        if word in skip or (partner and (word.endswith(partner) or partner.endswith(word))):
            continue
        if phon.rhyme_key(word).consonant != key:  # the page's own test, so it always passes
            continue
        n = _syllables(word, language)
        if language == "it" and not _italian_stress_is_certain(word, n):
            continue
        one, many = _SYLL[language]
        why = f"{_WHY[language].format(partner=partner)} · {n} {one if n == 1 else many}"
        out.append({"word": word, "syllables": n, "why": why})
        if len(out) >= k:
            break
    return out

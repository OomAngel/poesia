"""Spanish metrical syllable count, with the licences poets use.

Measured 2026-10-10 on ADSO (100 hand-scanned Golden-Age sonnets, 1,404 lines; rules tuned
on sonnets 1-50): held-out sonnets 51-100 93.8% of lines exact, the expert's count in the
licensed set for 99.7%; all 100: 93.5% exact, signed bias -0.01. The earlier counter was 59.3%
exact with a bias of -0.34. On 194 octosyllables of the Vanegas Arroyo broadsides: 92.3%
exact (was 69.1%), 100% in the set. Published scanners reach 95-97% on ADSO.

How a line is counted:
- Syllables and lexical stress per word come from ``fonemas`` (phonetic, so "y" in "ya" and
  "yo" is a consonant and "hie-", "hue-" start with a glide, not a vowel).
- Synalepha joins a word ending in a vowel sound to a word starting with one ("la aurora").
  A word ending in a consonant never joins ("los ojos" stays apart), and a lone vowel word
  ("y", "o") between two vowels joins once, not on both sides.
- The line ending follows the last stressed syllable of the last word: oxytone +1,
  proparoxytone -1, any final monosyllable +1. Adverbs in -mente end on their "men" stress.
- Licences give the *set* of counts a poet may claim: dialefa (keeping vowels apart where
  the second carries stress), syneresis (joining a hiatus inside a word: "po-e-ta") and
  dieresis (splitting a diphthong: "su-a-ve"). A form gate passes a line whose target is in
  the set; ``best`` is the usual reading, for metrics and repair messages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_VOWEL = set("aeiouáéíóú")  # in fonemas' phonetic output the glides are j and w, not vowels
_GLIDE_NUCLEUS = re.compile(r"[jw][aeiouáéíóú]|[aeiouáéíóú][jw]")

# Unstressed (atonic) monosyllables and function words: articles, prepositions, unstressed
# pronouns and possessives, conjunctions, relatives (RAE, Ortografía 2010, §1.4).
ATONIC = frozenset(
    """a al ante bajo con contra de del desde en entre hacia hasta para por según sin so sobre
    tras el la lo los las un una unos unas mi mis tu tus su sus nuestro nuestra vuestro vuestra
    me te se nos os le les y e ni o u que si pues mas aunque cuando como donde porque quien
    cual cuyo cuya""".split()
)
# Old spellings that put an accent on monosyllables (fué, dió); fonemas would split them.
_OLD_SPELLING = {
    "fué": "fue",
    "fuí": "fui",
    "dió": "dio",
    "vió": "vio",
    "pié": "pie",
    "piés": "pies",
    "á": "a",
    "é": "e",
    "ó": "o",
    "ú": "u",
}


@dataclass(frozen=True)
class _Word:
    text: str
    syllables: tuple[str, ...]
    stress: int | None  # index of the stressed syllable; None for atonic words
    last_stress: int  # last primary or secondary stress (for -mente adverbs)
    starts_vowel: bool
    ends_vowel: bool
    glides: int  # diphthongs a dieresis could split


@lru_cache(maxsize=200_000)
def _fonemas_syllables(word: str) -> tuple[str, ...]:
    from fonemas.fonemas import Transcription  # type: ignore[import-untyped]

    try:
        return tuple(Transcription(word).phonology.syllables)
    except Exception:  # noqa: BLE001 - unknown words fall back to a vowel-group estimate
        return ()


def _clean(token: str) -> str:
    word = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", "", token).lower()
    return _OLD_SPELLING.get(word, word)


def _plain(syllable: str) -> str:
    return syllable.replace("ˈ", "").replace("ˌ", "")


def _word(text: str) -> _Word:
    syls = _fonemas_syllables(text)
    if not syls:
        groups = re.findall(r"[aeiouáéíóúü]+", text) or ["x"]
        syls = tuple(groups)
    stress = next((i for i, s in enumerate(syls) if "ˈ" in s), len(syls) - 1)
    last_stress = max((i for i, s in enumerate(syls) if "ˈ" in s or "ˌ" in s), default=stress)
    first, last = _plain(syls[0]), _plain(syls[-1])
    return _Word(
        text=text,
        syllables=syls,
        stress=None if text in ATONIC else stress,
        last_stress=last_stress,
        starts_vowel=bool(first) and first[0] in _VOWEL,
        ends_vowel=bool(last) and last[-1] in _VOWEL,
        glides=sum(1 for s in syls if _GLIDE_NUCLEUS.search(_plain(s))),
    )


def words(line: str) -> list[_Word]:
    return [_word(w) for w in (_clean(t) for t in line.split()) if w]


def _joins(ws: list[_Word]) -> tuple[int, int, int]:
    """Synalephas between words: (certain, optional, chained)."""
    certain = optional = chained = 0
    merged_prev = False
    for a, b in zip(ws, ws[1:], strict=False):
        if not (a.ends_vowel and b.starts_vowel):
            merged_prev = False
        elif merged_prev and len(a.syllables) == 1 and len(a.text) == 1:
            chained += 1  # "raudo y espumoso": the lone vowel joins one side only
            merged_prev = False
        else:
            merged_prev = True
            if b.stress == 0:
                optional += 1  # dialefa is licensed before a stressed vowel; usually still joined
            else:
                certain += 1
    return certain, optional, chained


def _ending(last: _Word) -> int:
    """Oxytone +1, paroxytone 0, proparoxytone -1; a final monosyllable counts as oxytone."""
    if len(last.syllables) == 1:
        return 1
    return {0: 1, 1: 0}.get(len(last.syllables) - 1 - last.last_stress, -1)


def _hiatus(ws: list[_Word]) -> int:
    return sum(
        1
        for w in ws
        for x, y in zip(w.syllables, w.syllables[1:], strict=False)
        if _plain(x)[-1:] in _VOWEL and _plain(y)[:1] in _VOWEL
    )


def metrical_counts(line: str) -> tuple[int, frozenset[int]]:
    """``(best, licensed)``: the usual count and every count the licences allow."""
    ws = words(line)
    if not ws:
        return 0, frozenset({0})
    base = sum(len(w.syllables) for w in ws)
    certain, optional, chained = _joins(ws)
    ending = _ending(ws[-1])
    best = base - certain - optional + ending
    licensed = {base - certain - k + ending for k in range(optional + chained + 1)}
    for _ in range(_hiatus(ws)):  # syneresis: join a hiatus inside a word
        licensed |= {c - 1 for c in licensed}
    for _ in range(sum(w.glides for w in ws)):  # dieresis: split a diphthong
        licensed |= {c + 1 for c in licensed}
    return best, frozenset(licensed)

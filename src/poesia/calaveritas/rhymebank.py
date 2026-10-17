"""Rhyme families from the frequency word lists, for writing a calaverita line by line.

Apertus does not keep rhyme or metre when asked for a whole Spanish quatrain (live test 2026-10-09:
0 of 12 Spanish requests passed, 8B and 70B alike). So when a line must be repaired to rhyme, the
engine offers a few words of its partner's rhyme family; the model may also use its own word. Families come from ``poesia/wordlists`` (the
40,000 most frequent words, CC BY-SA 4.0, wordfreq), keyed by the Mexican-Spanish rhyme of
``rhyme.spanish_rhyme`` or the CMU rhyme in English. Words that the content floor or the Escolar
list would reject are never offered.
"""

from __future__ import annotations

import random
import threading
from functools import lru_cache
from pathlib import Path

from .guard import ESCOLAR_EXTRA, HATE, PRIVATE_SENSITIVE, SELF_HARM, SEXUAL, _hits
from .rhyme import english_rhyme, spanish_rhyme

WORDLISTS = Path(__file__).resolve().parent.parent / "wordlists"
TOP = 15000
SKIP_MOST_FREQUENT = 60  # the very top is function words; length >= 4 removes the rest
MIN_FAMILY = 6

# Function or vague words that make poor line endings even when they rhyme.
WEAK = {
    "cuyo",
    "cuya",
    "cuyos",
    "cuyas",
    "cual",
    "cuales",
    "aquel",
    "aquella",
    "esto",
    "esta",
    "este",
    "aquí",
    "allí",
    "sabe",
    "malo",
    "tanto",
    "cuanto",
    "mismo",
    "misma",
    "cada",
    "which",
    "that",
    "this",
    "those",
    "these",
    "there",
    "where",
    "would",
    "could",
    "should",
}

_LOCK = threading.Lock()


def _words(language: str) -> list[str]:
    path = WORDLISTS / f"{language}.txt"
    words = path.read_text(encoding="utf-8").split()[:TOP]
    return [w for w in words[SKIP_MOST_FREQUENT:] if len(w) >= 4 and w.isalpha()]


def _key(word: str, language: str, phonology: object | None) -> str:
    return (spanish_rhyme(word) if language == "es" else english_rhyme(word, phonology)).consonant


@lru_cache(maxsize=4)
def families(language: str, phonology: object | None = None) -> dict[str, tuple[str, ...]]:
    """Rhyme key -> words in frequency order, floor-filtered; only families of MIN_FAMILY or more."""
    with _LOCK:
        out: dict[str, list[str]] = {}
        unsafe = HATE + SEXUAL + SELF_HARM + PRIVATE_SENSITIVE
        for w in _words(language):
            if _hits(w, unsafe):
                continue
            k = _key(w, language, phonology)
            if k:  # one-letter keys are stressed final vowels: café, fue, sé
                out.setdefault(k, []).append(w)
        return {k: tuple(v) for k, v in out.items() if len(v) >= MIN_FAMILY}


def _clean(words: list[str], escolar: bool) -> list[str]:
    return [
        w
        for w in words
        if w not in WEAK and 4 <= len(w) <= 10 and not (escolar and _hits(w, ESCOLAR_EXTRA))
    ]


COMMON = (
    6  # the most frequent words of a family, ranked down when they end a line (audit 2026-10-09)
)
DEPTH = 40  # how deep into a family the offered words are sampled


def partners(
    word: str,
    language: str,
    escolar: bool,
    avoid: set[str],
    k: int = 6,
    phonology: object | None = None,
    rng: random.Random | None = None,
) -> list[str]:
    """Words that rhyme with ``word`` (same family), excluding ``avoid``. Without ``rng``: the most
    frequent first; with it, a sample from the first DEPTH words, so repairs do not all end on the
    same six words ("prisa", "mano", "frente"...)."""
    key = _key(word, language, phonology)
    fam = families(language, phonology).get(key, ())
    bare = word.lower().strip(".,;:!?¡¿«»\"'")
    pool = [w for w in _clean(list(fam), escolar) if w != bare and w not in avoid]
    if rng is None:
        return pool[:k]
    return rng.sample(pool[:DEPTH], min(k, len(pool[:DEPTH])))


def common(word: str, language: str, phonology: object | None = None) -> set[str]:
    """The COMMON most frequent words of ``word``'s rhyme family."""
    return set(families(language, phonology).get(_key(word, language, phonology), ())[:COMMON])


GENRE_WORDS = {
    "es": {
        "catrina",
        "calaca",
        "huesuda",
        "huesudita",
        "flaca",
        "parca",
        "pelona",
        "calavera",
        "calaverita",
        "guadaña",
        "cempasúchil",
        "ofrenda",
        "panteón",
        "posada",
        "calaveras",
    },
    "en": {"catrina", "calaca", "calavera", "calaverita", "calaveritas", "scythe", "ofrenda"},
}


@lru_cache(maxsize=2)
def vocabulary(language: str) -> frozenset[str]:
    """Every word of the 40,000-word list plus the genre's own words, lower-cased."""
    words = (WORDLISTS / f"{language}.txt").read_text(encoding="utf-8").split()
    return frozenset(w.lower() for w in words) | GENRE_WORDS[language]


def unknown_words(line: str, language: str, allowed: set[str]) -> list[str]:
    """Words of ``line`` that are neither in the vocabulary nor in ``allowed`` (name, traits, detail)."""
    import re

    vocab = vocabulary(language)
    words = re.findall(r"[A-Za-zÀ-ÿ’']+", line)
    out = []
    for w in words:
        lw = w.lower().strip("'’")
        if lw.endswith(("'s", "’s")):
            lw = lw[:-2]
        if (
            lw
            and lw not in allowed
            and (
                lw not in vocab
                or (
                    len(lw) >= 3
                    and re.fullmatch(r"m*(c[md]|d?c{0,3})(x[cl]|l?x{0,3})(i[xv]|v?i{0,3})", lw)
                )
            )
        ):
            out.append(
                w
            )  # unknown word, or a Roman numeral such as "viii" (the word list has them)
    return out

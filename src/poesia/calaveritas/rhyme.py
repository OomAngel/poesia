"""Rhyme keys for calaveritas: Mexican Spanish pronunciation, and English through the CMU dictionary.

A calaverita rhymes by ear, so the key is phonetic, not orthographic. In Mexican Spanish (seseo,
yeísmo, b/v merger, silent h) "casa" rhymes with "caza", "nueva" with "prueba" and "halla" with
"vaya". Since 2026-10-10 the Spanish key lives in ``poesia.phonology.spanish_rhyme`` (shared by
every deployment; this module keeps its interface); before, the engine's key compared spelling and took the
wrong vowel as stressed in words such as "agua". Both are fixed here, in this package only.

The consonant key runs from the stressed vowel of the last word to its end; the assonant key keeps
only the vowels of that tail, without the weak vowel of a diphthong ("historia" -> "oa").
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Rhyme:
    consonant: str
    assonant: str


def _last_word(line: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿ'’]+", line)
    return words[-1].lower() if words else ""


def spanish_rhyme(line: str) -> Rhyme:
    """Mexican-Spanish rhyme key (seseo): the shared ``phonology.spanish_rhyme`` key."""
    from poesia.phonology.spanish_rhyme import spanish_rhyme_key

    key = spanish_rhyme_key(line, "seseo")
    return Rhyme(key.consonant, key.assonant)


def english_rhyme(line: str, phonology: object | None = None) -> Rhyme:
    """English rhyme through the engine's CMU-based key; falls back to spelling when unavailable."""
    if phonology is not None:
        try:
            key = phonology.rhyme_key(line)  # type: ignore[attr-defined]
            if key and key.consonant:
                return Rhyme(key.consonant, key.assonant)
        except Exception:  # noqa: S110 - the spelling fallback below is the defined behaviour
            pass
    word = _last_word(line)
    m = re.search(r"[aeiouy][^aeiouy]*e?$", word)
    tail = word[m.start() :] if m else word
    return Rhyme(tail, "".join(c for c in tail if c in "aeiouy"))


def rhyme_of(line: str, language: str, phonology: object | None = None) -> Rhyme:
    return spanish_rhyme(line) if language == "es" else english_rhyme(line, phonology)


def scheme_of(lines: list[str], language: str, phonology: object | None = None) -> str:
    """Letters for a quatrain by consonant rhyme, e.g. "ABAB"; unmatched lines get their own letter."""
    keys = [rhyme_of(line, language, phonology).consonant for line in lines]
    letters: list[str] = []
    seen: dict[str, str] = {}
    for k in keys:
        if k and k in seen:
            letters.append(seen[k])
        else:
            letter = chr(ord("A") + len(seen))
            if k:
                seen[k] = letter
            else:
                seen[f"__{len(seen)}"] = letter
            letters.append(letter)
    return "".join(letters)


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text)

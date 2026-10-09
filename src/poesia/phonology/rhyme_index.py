"""Words grouped by rhyme key, from the frequency word lists (``poesia/wordlists``).

Shared by the page's rhyme-word ideas (``poesia.word_ideas``) and the generation prompt's
word bank (``poesia.generation.rhyme_fetcher``), so both offer words of the poem's language
checked with the same ``rhyme_key`` the page uses to mark a rhyme. Offline; each language's
index is built once (a few hundred ms to about a second).
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from typing import Any


@cache
def ranked(language: str) -> list[str]:
    """The language's word list, most frequent first (German nouns capitalised)."""
    text = resources.files("poesia.wordlists").joinpath(f"{language}.txt").read_text("utf-8")
    return [w for w in text.split("\n") if w]


@cache
def rank(language: str) -> dict[str, int]:
    return {w: i for i, w in enumerate(ranked(language))}


@cache
def phonology(language: str) -> Any:
    """The scanner for ``language`` (es, en, it, de, fr)."""
    if language == "es":
        from poesia.phonology.spanish import SpanishPhonology

        return SpanishPhonology()
    if language == "en":
        from poesia.phonology.english import EnglishPhonology

        return EnglishPhonology()
    if language == "it":
        from poesia.phonology.italian import ItalianPhonology

        return ItalianPhonology()
    if language == "de":
        from poesia.phonology.german import GermanPhonology

        return GermanPhonology()
    if language == "fr":
        from poesia.phonology.french import FrenchPhonology

        return FrenchPhonology()
    raise ValueError(f"no phonology for language '{language}'")


@cache
def by_key(language: str) -> dict[str, list[str]]:
    """Rhyme key -> words in frequency order."""
    phon = phonology(language)
    index: dict[str, list[str]] = {}
    for word in ranked(language):
        if len(word) < 2:
            continue
        key = phon.rhyme_key(word).consonant
        if key:
            index.setdefault(key, []).append(word)
    return index


def rhyming_words(language: str, word: str) -> list[str]:
    """Words that share ``word``'s rhyme key, most frequent first (``word`` itself excluded)."""
    key = phonology(language).rhyme_key(word).consonant
    if not key:
        return []
    low = word.lower()
    return [w for w in by_key(language).get(key, []) if w.lower() != low]

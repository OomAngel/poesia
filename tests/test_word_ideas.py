"""Rhyme words first (poesia.word_ideas): small, offline suggestions (plan U6)."""

from __future__ import annotations

from poesia.word_ideas import _italian_stress_is_certain, rhyme_words


def test_words_already_ending_a_line_are_not_offered():
    first = "La luna vierte su silencio en el mar"
    offered = [w["word"] for w in rhyme_words("es", first)]
    again = [w["word"] for w in rhyme_words("es", first, avoid={offered[0]})]
    assert offered[0] not in again and "mar" not in offered


def test_italian_never_offers_an_unmarked_third_to_last_stress():
    # crèscita, pèrdita, òpera look like partìta, manièra without a dictionary.
    words = {w["word"] for w in rhyme_words("it", "Nel mezzo del cammin di nostra vita", k=40)}
    words |= {w["word"] for w in rhyme_words("it", "il mare che respira nella sera", k=40)}
    assert not words & {"crescita", "perdita", "vendita", "nascita", "opera", "camera", "lettera"}
    assert _italian_stress_is_certain("bellezza", 3)  # closed second-to-last syllable
    assert _italian_stress_is_certain("città", 2)  # written accent
    # Known from Wiktionary's table since 2026-10-08 (they used to be guesses).
    assert _italian_stress_is_certain("crescita", 3) and _italian_stress_is_certain("tenebre", 3)
    # A word the table does not know, with an open second-to-last syllable, stays a guess.
    assert not _italian_stress_is_certain("zorbita", 3)


def test_each_word_says_why_in_the_poems_language():
    (es,) = rhyme_words("es", "La luna vierte su silencio en el mar", k=1)
    assert es["why"].startswith("rima con «mar»") and "sílaba" in es["why"]
    (en,) = rhyme_words("en", "I wandered lonely as a cloud", k=1)
    assert en["why"].startswith("rhymes with “cloud”")

"""Italian scansion: sinalefe, line endings, diphthongs, rhyme."""

from __future__ import annotations

import pytest

from poesia.phonology.base import Stress
from poesia.phonology.italian import ItalianPhonology

P = ItalianPhonology()


@pytest.mark.parametrize(
    "line",
    [
        "Nel mezzo del cammin di nostra vita",  # Dante, Inf. I 1
        "mi ritrovai per una selva oscura,",  # sinalefe: una_selva? no; selva_oscura
        "Voi ch'ascoltate in rime sparse il suono",  # Petrarca, RVF 1
        "in consolar i casi e i dolor mei;",  # chain of three vowels, tronco ending
        "e veggio ad un lacciuol Giunone e Dido,",
    ],
)
def test_endecasillabi_count_eleven(line: str) -> None:
    assert P.scan_line(line).metrical_syllable_count == 11


def test_endings_piano_tronco_sdrucciolo() -> None:
    assert P.scan_line("la città").metrical_syllable_count == 4  # la cit-tà + 1
    assert P.scan_line("il mare").metrical_syllable_count == 3  # piano
    assert P.scan_line("la lùcida").metrical_syllable_count == 3  # sdrucciolo, accent written


def test_diphthongs_and_silent_h() -> None:
    assert P.scan_line("cuore").metrical_syllable_count == 2  # cuo-re
    assert P.scan_line("Ahi").metrical_syllable_count == 2  # one syllable, tronco + 1


def test_stress_on_the_tenth_position() -> None:
    pattern = P.scan_line("Nel mezzo del cammin di nostra vita").stress_pattern
    assert pattern[9] is Stress.PRIMARY


def test_rhyme_from_the_stressed_vowel() -> None:
    assert P.rhyme_key("il mio cuore").consonant == P.rhyme_key("l'amore").consonant == "ore"
    assert P.rhyme_key("la città").consonant == "a"
    assert P.rhyme_key("cuore").consonant != P.rhyme_key("mare").consonant


def test_unmarked_third_to_last_stress_from_wiktionary():
    # crescita, tavola, perdita: stressed on the third-to-last syllable with no written
    # accent; the rule alone stressed the second-to-last (data/it_stress.tsv).
    from poesia.phonology.italian import ItalianPhonology

    p = ItalianPhonology()
    assert p.rhyme_key("sopra la tavola").consonant == "avola"
    assert p.rhyme_key("la crescita del mondo").consonant == "ondo"
    assert p.rhyme_key("una perdita").consonant == "erdita"
    # Words the rule gets right, and ambiguous ones (ancora / ancóra), are not listed.
    assert p.rhyme_key("nella sera").consonant == "era"
    assert p.rhyme_key("e poi ancora").consonant == "ora"

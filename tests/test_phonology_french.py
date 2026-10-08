"""French scansion and rhyme: classical counting rules and sound-based rhyme."""

import pytest

from poesia.phonology.french import FrenchPhonology

F = FrenchPhonology()


@pytest.mark.parametrize(
    ("line", "count"),
    [
        ("Mes pleurs sont à moi, nul au monde", 8),  # final mute e not counted
        ("L'être qui souffre est un mystère", 8),  # souffre est: elision
        ("Comme un enfant en pleurs, j'osai crier : « Prends-moi !", 12),  # cri-er (liquid)
        ("Le spectre disparaît en criant : Souviens-toi !", 12),  # aî one vowel
        ("Mais à nos yeux bientôt la vision décroît ;", 12),  # vi-si-on (diérèse)
        ("Battirent leurs habits puis les lui essayèrent", 12),  # -ent silent at the end
        ("Laissa crouler ainsi le toit de ses aïeux ?", 12),  # aï-eux
        ("Nous guides à travers les écueils d'ici-bas,", 12),  # é-cueils
    ],
)
def test_counts_classical_lines(line, count):
    assert F.scan_line(line).metrical_syllable_count == count


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("mystère", "solitaire"),
        ("temps", "sang"),
        ("rose", "chose"),
        ("soleil", "pareil"),
        ("fille", "famille"),
        ("bien", "rien"),
        ("commence", "France"),
    ],
)
def test_rhyming_words_share_a_key(a, b):
    assert F.rhyme_key(f"x {a}").consonant == F.rhyme_key(f"x {b}").consonant


@pytest.mark.parametrize(("a", "b"), [("mer", "mère"), ("rose", "rosse"), ("bien", "science")])
def test_non_rhymes_differ(a, b):
    assert F.rhyme_key(f"x {a}").consonant != F.rhyme_key(f"x {b}").consonant

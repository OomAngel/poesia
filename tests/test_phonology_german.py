"""German scansion and rhyme."""

import pytest

from poesia.phonology.base import Stress
from poesia.phonology.german import GermanPhonology

G = GermanPhonology()
U, S = Stress.UNSTRESSED, Stress.PRIMARY


def test_iambic_tetrameter():
    r = G.scan_line("Ich muß hinaus, ich muß zu dir,")
    assert r.metrical_syllable_count == 8
    assert r.stress_pattern[2:4] == (U, S)  # hi-NAUS


@pytest.mark.parametrize(
    ("line", "count"),
    [
        ("Mit den Quellen geht mein Grüßen,", 8),
        ("Die hohen Bastionen schauten mich an,", 10),
        ("Du hast ja Schiller und Goethe:", 8),
    ],
)
def test_counts(line, count):
    assert G.scan_line(line).metrical_syllable_count == count


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Hand", "Wolkenwand"),
        ("Tag", "lag"),
        ("Herz", "Schmerz"),
        ("werden", "Behörden"),
        ("Kleid", "verstreut"),
    ],
)
def test_rhymes(a, b):
    assert G.rhyme_key(f"x {a}").consonant == G.rhyme_key(f"x {b}").consonant


@pytest.mark.parametrize(("a", "b"), [("Hand", "Hund"), ("Liebe", "Leben")])
def test_non_rhymes(a, b):
    assert G.rhyme_key(f"x {a}").consonant != G.rhyme_key(f"x {b}").consonant

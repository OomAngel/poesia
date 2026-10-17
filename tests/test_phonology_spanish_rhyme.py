"""Spanish rhyme keys by sound (poesia.phonology.spanish_rhyme)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from poesia.phonology.spanish import SpanishPhonology
from poesia.phonology.spanish_rhyme import spanish_rhyme_key

GOLD = Path("seeds/poetry_corpus/eval_gold/adso_gold_100.jsonl")


def rhymes(a: str, b: str, variety: str = "seseo") -> bool:
    return spanish_rhyme_key(a, variety).consonant == spanish_rhyme_key(b, variety).consonant


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("corazón", "canción"),
        ("nueva", "prueba"),  # b/v
        ("halla", "vaya"),  # ll/y, silent h
        ("pingüino", "camino"),
        ("rey", "ley"),
        ("tierra", "guerra"),  # rhyme starts at the strong vowel of the diphthong
    ],
)
def test_rhymes(a: str, b: str) -> None:
    assert rhymes(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("historia", "alegría"),  # falling diphthong: "oria" vs "ia" (the old key rhymed them)
        ("agua", "tregua"),  # á-gua vs tré-gua
        ("Calavera", "Catrina"),
    ],
)
def test_not_rhymes(a: str, b: str) -> None:
    assert not rhymes(a, b)


def test_variety_switch() -> None:
    assert rhymes("casa", "caza", "seseo")
    assert not rhymes("casa", "caza", "distincion")
    assert SpanishPhonology(variety="distincion").rhyme_key("caza").consonant == "aza"
    with pytest.raises(ValueError):
        spanish_rhyme_key("casa", "andaluz")


def test_assonance_and_mexican_x() -> None:
    assert spanish_rhyme_key("historia").assonant == "oa"
    assert spanish_rhyme_key("México").consonant.startswith("eji")


@pytest.mark.skipif(not GOLD.exists(), reason="ADSO gold set is DVC/local data")
def test_adso_quatrain_groups() -> None:
    """Lines 1-4-5-8 and 2-3-6-7 of each sonnet: 98.5% of groups match, A/B never (2026-10-10)."""
    full = cross = n = 0
    for row in GOLD.open(encoding="utf-8"):
        verses = [v for v in json.loads(row)["completion"].split("\n") if v.strip()]
        if len(verses) != 14:
            continue
        keys = [spanish_rhyme_key(v).consonant for v in verses[:8]]
        a, b = [keys[i] for i in (0, 3, 4, 7)], [keys[i] for i in (1, 2, 5, 6)]
        n += 1
        full += (len(set(a)) == 1) + (len(set(b)) == 1)
        cross += a[0] == b[0]
    assert full / (2 * n) >= 0.97 and cross == 0

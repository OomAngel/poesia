"""Tests for the shared phonology dataclasses (poesia.phonology.base).

These types have no external dependencies, so these tests never need the
optional phonology extras (rantanplan/pronouncing/phonemizer) installed.
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult, Stress, Syllable


def test_stress_enum_values() -> None:
    assert Stress.UNSTRESSED.value == 0
    assert Stress.PRIMARY.value == 1
    assert Stress.SECONDARY.value == 2


def test_syllable_defaults() -> None:
    syl = Syllable(text="po")
    assert syl.text == "po"
    assert syl.stress == Stress.UNSTRESSED
    assert syl.phonemes == ()


def test_syllable_is_frozen() -> None:
    syl = Syllable(text="po")
    try:
        syl.text = "esía"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("Syllable should be frozen (immutable)")


def test_rhyme_key_holds_consonant_and_assonant() -> None:
    key = RhymeKey(consonant="ado", assonant="a-o")
    assert key.consonant == "ado"
    assert key.assonant == "a-o"


def test_scan_result_defaults() -> None:
    result = ScanResult(line="En un lugar de la Mancha")
    assert result.line == "En un lugar de la Mancha"
    assert result.syllables == []
    assert result.metrical_syllable_count == 0
    assert result.stress_pattern == ()
    assert result.rhyme_key is None
    assert result.is_valid is False
    assert result.violations == []


def test_scan_result_can_hold_syllables_and_stress_pattern() -> None:
    syllables = [Syllable(text="po", stress=Stress.PRIMARY), Syllable(text="ma")]
    result = ScanResult(
        line="poma",
        syllables=syllables,
        metrical_syllable_count=2,
        stress_pattern=(Stress.PRIMARY, Stress.UNSTRESSED),
        is_valid=True,
    )
    assert len(result.syllables) == 2
    assert result.stress_pattern == (Stress.PRIMARY, Stress.UNSTRESSED)
    assert result.is_valid is True

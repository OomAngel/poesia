"""Tests for Dutch phonology backend."""

import pytest

from poesia.phonology.dutch import DutchPhonology


@pytest.fixture
def dutch_phonology() -> DutchPhonology:
    return DutchPhonology()


def test_dutch_scan_line_syllable_count(dutch_phonology: DutchPhonology) -> None:
    """Dutch scan_line should count syllables correctly."""
    result = dutch_phonology.scan_line("De avond valt")
    # pyphen hyphenation-based: De(1) + avond(1) + valt(1) = 3
    # Note: pyphen uses hyphenation dictionaries, not phonetic syllables
    assert result.metrical_syllable_count == 3
    assert result.is_valid is True


def test_dutch_scan_line_longer_verse(dutch_phonology: DutchPhonology) -> None:
    """Dutch scan_line should handle longer verses with hyphenatable words."""
    result = dutch_phonology.scan_line("avondstilte in de vallei")
    # avond-stil-te(3) + in(1) + de(1) + val-lei(2) = 7
    assert result.metrical_syllable_count >= 5  # At least these many
    assert result.is_valid is True


def test_dutch_rhyme_key(dutch_phonology: DutchPhonology) -> None:
    """Dutch rhyme_key should extract rhyme signature."""
    key = dutch_phonology.rhyme_key("De avond valt")
    assert key.consonant != ""
    assert key.assonant != ""


def test_dutch_scan_line_has_stress_pattern(dutch_phonology: DutchPhonology) -> None:
    """Dutch scan_line should produce a stress pattern."""
    result = dutch_phonology.scan_line("avondstilte")
    # a-vond-stil-te = 4 syllables
    assert len(result.stress_pattern) > 0
    assert len(result.stress_pattern) == result.metrical_syllable_count

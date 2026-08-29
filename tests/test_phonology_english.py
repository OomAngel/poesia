"""Tests for English phonology backend, including the g2p_en OOV fallback.

`beholdings` and `flibbertigibbet` are confirmed absent from CMUdict (see
`pronouncing.phones_for_word` returning an empty list for both) — they exist
here specifically to exercise the fallback path, not the CMUdict-hit path.
"""

import pytest

from poesia.phonology.english import EnglishPhonology


@pytest.fixture
def english_phonology() -> EnglishPhonology:
    return EnglishPhonology()


def test_cmudict_word_stresses(english_phonology: EnglishPhonology) -> None:
    """A word CMUdict knows should resolve without touching the fallback.

    "holdings" -> HH OW1 L D IH0 NG Z: two vowel phones (OW1, IH0), so two
    stress digits, not one per letter-syllable.
    """
    assert english_phonology.stresses_for_word("holdings") == "10"


def test_oov_word_no_longer_raises(english_phonology: EnglishPhonology) -> None:
    """The bug this test guards: an OOV last word used to raise ValueError
    and crash the whole generation loop instead of degrading gracefully."""
    key = english_phonology.rhyme_key("what a strange word: beholdings")
    assert key.consonant != ""
    assert key.assonant != ""


def test_oov_word_stresses_via_fallback(english_phonology: EnglishPhonology) -> None:
    """g2p_en fallback should still produce a real stress digit string."""
    digits = english_phonology.stresses_for_word("flibbertigibbet")
    assert digits is not None
    assert set(digits) <= {"0", "1", "2"}
    assert len(digits) > 1  # multi-syllable


def test_cmudict_and_fallback_rhyme_keys_share_arpabet_format(
    english_phonology: EnglishPhonology,
) -> None:
    """CMUdict hits and g2p_en fallbacks must share one phoneme alphabet
    (ARPAbet), so a rhyme key from either path is directly comparable —
    not two incompatible representations that can never match each other.

    This checks representation compatibility, not that these two specific
    (unrelated) words rhyme — g2p_en's stress prediction for an invented
    word like "beholdings" is not something to assert as fact.
    """
    cmudict_key = english_phonology.rhyme_key("stacks of old holdings")
    fallback_key = english_phonology.rhyme_key("a strange word: beholdings")
    for key in (cmudict_key, fallback_key):
        assert key.consonant
        tokens = key.consonant.split()
        assert all(tok.isalnum() and tok.isupper() for tok in tokens)


def test_scan_line_counts_syllables_through_fallback(
    english_phonology: EnglishPhonology,
) -> None:
    """scan_line should not drop OOV words silently; it should still count
    their syllables via the fallback."""
    result = english_phonology.scan_line("flibbertigibbet")
    assert result.is_valid is True
    assert result.metrical_syllable_count > 1

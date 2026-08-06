"""Tests for Spanish sinalefa (vowel elision) and metrical counting.

Sinalefa is THE critical feature for correct Spanish verse scansion.
Without it, hendecasyllables (11-syllable lines) are miscounted.
"""

import pytest

from poesia.phonology.spanish import (
    SpanishPhonology,
    _count_sinalefas,
    _final_stress_adjustment,
)


class TestSinalefaDetection:
    """Tests for _count_sinalefas helper function."""

    def test_basic_sinalefa(self) -> None:
        """Vowel-to-vowel across words creates sinalefa."""
        # "la aurora" → la-au-ro-ra → lau-ro-ra (1 sinalefa)
        assert _count_sinalefas(["la", "aurora"]) == 1

    def test_h_sinalefa(self) -> None:
        """H+vowel at word start still creates sinalefa."""
        # "de humilde" → de-hu-mil-de → deu-mil-de (1 sinalefa)
        assert _count_sinalefas(["de", "humilde"]) == 1

    def test_y_sinalefa(self) -> None:
        """Y at word start creates sinalefa (y sounds like vowel)."""
        # "como y cuando" (but y is a word itself, so edge case)
        assert _count_sinalefas(["como", "y"]) == 1

    def test_multiple_sinalefas(self) -> None:
        """Multiple sinalefas in one line."""
        # "la aurora empieza" → 2 sinalefas (la-a, a-e)
        assert _count_sinalefas(["la", "aurora", "empieza"]) == 2

    def test_no_sinalefa_consonant_start(self) -> None:
        """No sinalefa when second word starts with consonant."""
        assert _count_sinalefas(["la", "luna"]) == 0

    def test_no_sinalefa_consonant_end(self) -> None:
        """No sinalefa when first word ends in consonant (not n/s)."""
        assert _count_sinalefas(["sol", "alto"]) == 0

    def test_sinalefa_with_n_ending(self) -> None:
        """Words ending in -n can have sinalefa."""
        # "hablan alto" → ha-blan-al-to → ha-blal-to (sinalefa on an+a)
        # Actually -an ends in n preceded by vowel, so yes
        assert _count_sinalefas(["están", "aquí"]) == 1

    def test_empty_words(self) -> None:
        """Empty word list should return 0."""
        assert _count_sinalefas([]) == 0
        assert _count_sinalefas([""]) == 0


class TestFinalStressAdjustment:
    """Tests for final word stress adjustment (aguda/llana/esdrújula)."""

    def test_aguda_adds_one(self) -> None:
        """Oxytone (aguda) final word adds 1 to syllable count."""
        # "corazón" ends in -ón (stressed last syllable)
        assert _final_stress_adjustment(["corazón"], 3) == 4

    def test_llana_no_change(self) -> None:
        """Paroxytone (llana) final word doesn't change count."""
        # "casa" is llana (stress on penult)
        assert _final_stress_adjustment(["casa"], 2) == 2

    def test_esdrujula_subtracts_one(self) -> None:
        """Proparoxytone (esdrújula) final word subtracts 1."""
        # "lámpara" is esdrújula
        assert _final_stress_adjustment(["lámpara"], 3) == 2

    def test_aguda_by_consonant_ending(self) -> None:
        """Word ending in consonant (not n/s) without accent is aguda."""
        # "amor" ends in -r, no accent → aguda → +1
        assert _final_stress_adjustment(["amor"], 2) == 3


class TestSpanishPhonologyMetrics:
    """Integration tests for full metrical scansion with sinalefa."""

    @pytest.fixture
    def phonology(self) -> SpanishPhonology:
        return SpanishPhonology()

    def test_simple_sinalefa_line(self, phonology: SpanishPhonology) -> None:
        """Simple line with clear sinalefa."""
        # "la aurora" = la(1) + au-ro-ra(3) = 4 ortho, 1 sinalefa = 3 metrical
        line = "la aurora"
        result = phonology.scan_line(line)
        assert result.metrical_syllable_count == 3

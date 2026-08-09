"""Haiku metre scoring with real Spanish phonology (5-7-5 pattern).

These tests exercise metre_score against real scansion (sinalefa-aware),
complementing the pure-function tests in test_evaluation_metrics.py.
"""

from __future__ import annotations

from poesia.evaluation.metrics import metre_score
from poesia.forms.definitions import get_form
from poesia.phonology.spanish import SpanishPhonology


def test_haiku_has_syllable_pattern() -> None:
    """Haiku FormSpec should define 5-7-5 syllable pattern (cycling beyond)."""
    haiku = get_form("haiku")
    assert haiku.syllable_pattern == [5, 7, 5]
    for idx, expected in [(0, 5), (1, 7), (2, 5), (3, 5), (4, 7), (5, 5)]:
        assert haiku.syllables_for_line(idx) == expected


def test_haiku_metre_scoring_ranks_by_deviation() -> None:
    """Scores decrease as deviation from the target syllable count grows."""
    phonology = SpanishPhonology()
    scan_5 = phonology.scan_line("luna brillante")  # ~5 syllables
    scan_7 = phonology.scan_line("la luna brilla en silencio")  # ~8 w/ sinalefa
    scan_11 = phonology.scan_line("en el jardín florece la luna de primavera")  # ~14

    score_5 = metre_score(scan_5, target_syllable_count=5)
    score_7 = metre_score(scan_7, target_syllable_count=5)
    score_11 = metre_score(scan_11, target_syllable_count=5)
    assert score_5 >= 0.8
    assert score_7 < score_5
    assert score_11 < score_7


def test_metre_score_nonzero_for_valid_targets() -> None:
    """Regression: metre_score must never return 0.0 for positive targets."""
    scan = SpanishPhonology().scan_line("luna")
    for target in [5, 7, 11]:
        assert metre_score(scan, target_syllable_count=target) >= 0.0

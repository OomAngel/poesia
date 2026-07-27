"""Unit tests for evaluation metrics (metre, rhyme, theme, novelty, cliche)."""

from __future__ import annotations

from poesia.evaluation.metrics import (
    cliche_penalty,
    composite_score,
    metre_score,
    novelty_score,
    rhyme_score,
    theme_score,
)
from poesia.phonology.base import ScanResult


def test_metre_score() -> None:
    scan = ScanResult(line="test", metrical_syllable_count=11)
    assert metre_score(scan, target_syllable_count=11) == 1.0
    assert metre_score(scan, target_syllable_count=0) == 0.0
    assert metre_score(scan, target_syllable_count=10) == 0.9


def test_rhyme_score() -> None:
    assert rhyme_score("at", "at") == 1.0
    assert rhyme_score("at", "og") == 0.0


def test_theme_score() -> None:
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert theme_score(v1, v2) == 1.0
    assert theme_score(v1, v3) == 0.0
    assert theme_score([], v1) == 0.0


def test_novelty_score() -> None:
    c = [1.0, 0.0, 0.0]
    p1 = [1.0, 0.0, 0.0]  # Identical
    p2 = [0.0, 1.0, 0.0]  # Orthogonal

    assert novelty_score(c, []) == 1.0
    assert novelty_score(c, [p2]) == 1.0
    assert novelty_score(c, [p1, p2]) == 0.0


def test_cliche_penalty() -> None:
    cliches = frozenset(["lluvia sobre piedra", "sangre y fuego"])
    assert cliche_penalty("El cielo azul", cliches) == 0.0
    assert cliche_penalty("La lluvia sobre piedra cae", cliches) == 0.25


def test_composite_score() -> None:
    """Test composite scoring with normalization (default behavior)."""
    # With all signals active and normalize_weights=True (default)
    score = composite_score(metre=1.0, rhyme=1.0, theme=1.0, novelty=1.0, cliche=0.0)
    # All weights sum to 0.9 (excluding cliche), normalized to 1.0
    # All scores are 1.0, so result is 1.0
    assert score == 1.0
    
    # Test without normalization (old behavior)
    score_abs = composite_score(
        metre=1.0, rhyme=1.0, theme=1.0, novelty=1.0, cliche=0.0,
        normalize_weights=False
    )
    assert score_abs == 0.9  # 0.3 + 0.2 + 0.25 + 0.15 = 0.9

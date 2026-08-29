"""Unit tests for evaluation metrics (metre, rhyme, theme, novelty, cliche)."""

from __future__ import annotations

from poesia.evaluation.metrics import (
    cliche_penalty,
    composite_score,
    foot_score,
    metre_score,
    novelty_score,
    rhyme_score,
    theme_score,
)
from poesia.phonology.base import ScanResult, Stress


def test_metre_score() -> None:
    scan = ScanResult(line="test", metrical_syllable_count=11)
    assert metre_score(scan, target_syllable_count=11) == 1.0
    assert metre_score(scan, target_syllable_count=0) == 0.0
    assert metre_score(scan, target_syllable_count=10) == 0.9


def test_foot_score_no_claim_is_neutral() -> None:
    # Forms with no foot claim (haiku, Spanish syllable-count forms) should
    # never be penalized for a check that doesn't apply to them.
    assert foot_score((Stress.PRIMARY, Stress.PRIMARY, Stress.PRIMARY), foot=None) == 1.0
    assert foot_score((), foot=None) == 1.0


def test_foot_score_perfect_iamb() -> None:
    # weak, STRONG, weak, STRONG — a textbook two-foot iambic run.
    pattern = (Stress.UNSTRESSED, Stress.PRIMARY, Stress.UNSTRESSED, Stress.PRIMARY)
    assert foot_score(pattern, foot="iambic") == 1.0


def test_foot_score_inverted_is_trochaic_not_iambic() -> None:
    # STRONG, weak, STRONG, weak — every position disagrees with iambic.
    pattern = (Stress.PRIMARY, Stress.UNSTRESSED, Stress.PRIMARY, Stress.UNSTRESSED)
    assert foot_score(pattern, foot="iambic") == 0.0


def test_foot_score_partial_match() -> None:
    # Positions 0,1 match iambic (weak, STRONG); positions 2,3 don't (STRONG, weak).
    pattern = (Stress.UNSTRESSED, Stress.PRIMARY, Stress.PRIMARY, Stress.UNSTRESSED)
    assert foot_score(pattern, foot="iambic") == 0.5


def test_foot_score_secondary_stress_counts_as_stressed() -> None:
    pattern = (Stress.UNSTRESSED, Stress.SECONDARY)
    assert foot_score(pattern, foot="iambic") == 1.0


def test_foot_score_empty_pattern_with_foot_claim() -> None:
    # A foot claim is made but there's no data to check it against — can't
    # confirm compliance, so this is scored as non-compliant, not neutral.
    assert foot_score((), foot="iambic") == 0.0


def test_foot_score_unknown_foot_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown foot pattern"):
        foot_score((Stress.PRIMARY,), foot="trochaic")


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
    # All weights are normalized to sum to 1.0; all scores are 1.0 (foot and
    # end_word default to 1.0 too), so the result is 1.0 — up to float error
    # from summing several non-power-of-two weight fractions.
    assert abs(score - 1.0) < 1e-9

    # Test without normalization (old behavior)
    score_abs = composite_score(
        metre=1.0, rhyme=1.0, theme=1.0, novelty=1.0, cliche=0.0, normalize_weights=False
    )
    # 0.22 + 0.15 + 0.20 + 0.10 + 0.07 + 0.05*1.0(foot) + 0.13*0.0(fragment) - 0.08*0.0 = 0.79
    assert abs(score_abs - 0.79) < 0.01

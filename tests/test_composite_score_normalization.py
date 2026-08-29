"""Tests for composite score weight normalization (Issue #4)."""

from __future__ import annotations

from poesia.evaluation.metrics import composite_score


def test_composite_score_without_normalization():
    """Original behavior: absolute weights, scores in narrow range."""
    # Degraded mode: only metre, novelty, end_word active
    score = composite_score(
        metre=0.5,
        rhyme=0.0,
        theme=0.0,
        novelty=1.0,
        cliche=0.0,
        normalize_weights=False,
    )
    # end_word and foot also default to 1.0 (no repetition, no foot claim):
    # 0.22*0.5 + 0.10*1.0 + 0.07*1.0 + 0.05*1.0 = 0.11 + 0.10 + 0.07 + 0.05 = 0.33
    assert abs(score - 0.33) < 0.01


def test_composite_score_with_normalization():
    """With normalization: weights redistributed, better score spread."""
    # Same inputs, but normalize_weights=True (default)
    score = composite_score(
        metre=0.5,
        rhyme=0.0,
        theme=0.0,
        novelty=1.0,
        cliche=0.0,
        normalize_weights=True,
    )
    # Active weights: metre (0.22) + novelty (0.10) + end_word (0.07) + foot (0.05,
    # defaults to 1.0 — no foot claim passed) = 0.44
    # Normalization factor: 1.0 / 0.44 = 2.273...
    # Normalized: metre=0.5, novelty=0.227, end_word=0.159, foot=0.114
    # Score: 0.5*0.5 + 0.227*1.0 + 0.159*1.0 + 0.114*1.0 = 0.25 + 0.227 + 0.159 + 0.114 = 0.75
    assert abs(score - 0.75) < 0.01


def test_normalization_with_all_signals_active():
    """When all signals active, normalization should preserve relative weights."""
    score_normalized = composite_score(
        metre=0.8,
        rhyme=0.6,
        theme=0.7,
        novelty=0.5,
        cliche=0.1,
        normalize_weights=True,
    )

    score_absolute = composite_score(
        metre=0.8,
        rhyme=0.6,
        theme=0.7,
        novelty=0.5,
        cliche=0.1,
        normalize_weights=False,
    )

    # With all signals active except fragment_fidelity (defaults to 0, excluded),
    # foot still defaults to 1.0 (no foot claim passed) and stays active:
    # Absolute: 0.22*0.8 + 0.15*0.6 + 0.20*0.7 + 0.10*0.5 - 0.08*0.1 + 0.07*1.0 + 0.05*1.0
    #         = 0.176 + 0.09 + 0.14 + 0.05 - 0.008 + 0.07 + 0.05 = 0.568
    assert abs(score_absolute - 0.568) < 0.01
    # Normalized should give same ranking order even if absolute values differ slightly
    assert score_normalized > 0.5  # Reasonable score with all positive signals


def test_normalization_improves_score_spread():
    """Normalization should create better differentiation between candidates."""
    # Two candidates with different metre in degraded mode

    candidate_a_norm = composite_score(
        metre=0.9, rhyme=0.0, theme=0.0, novelty=1.0, cliche=0.0, normalize_weights=True
    )

    candidate_b_norm = composite_score(
        metre=0.3, rhyme=0.0, theme=0.0, novelty=1.0, cliche=0.0, normalize_weights=True
    )

    candidate_a_abs = composite_score(
        metre=0.9, rhyme=0.0, theme=0.0, novelty=1.0, cliche=0.0, normalize_weights=False
    )

    candidate_b_abs = composite_score(
        metre=0.3, rhyme=0.0, theme=0.0, novelty=1.0, cliche=0.0, normalize_weights=False
    )

    # Spread with normalization
    spread_norm = candidate_a_norm - candidate_b_norm
    # Spread without normalization
    spread_abs = candidate_a_abs - candidate_b_abs

    # Normalized spread should be larger (better differentiation)
    assert spread_norm > spread_abs
    assert spread_norm > 0.3  # Significant difference


def test_metre_always_considered_active():
    """Metre should always be considered active even if 0.0."""
    # Edge case: metre=0.0 but novelty=1.0
    score = composite_score(
        metre=0.0,
        rhyme=0.0,
        theme=0.0,
        novelty=1.0,
        cliche=0.0,
        normalize_weights=True,
    )

    # Should still normalize based on metre + novelty + end_word + foot
    # Active: metre (0.22) + novelty (0.10) + end_word (0.07) + foot (0.05) = 0.44
    # Normalized novelty: 0.10 / 0.44 = 0.227
    # Normalized end_word: 0.07 / 0.44 = 0.159
    # Normalized foot: 0.05 / 0.44 = 0.114
    # Score (metre input is 0.0, contributes nothing): 0.227 + 0.159 + 0.114 = 0.5
    assert abs(score - 0.5) < 0.01


def test_cliche_penalty_not_affected_by_normalization():
    """Cliché penalty should subtract normally, not get normalized."""
    score_no_cliche = composite_score(
        metre=0.5, rhyme=0.0, theme=0.0, novelty=1.0, cliche=0.0, normalize_weights=True
    )

    score_with_cliche = composite_score(
        metre=0.5, rhyme=0.0, theme=0.0, novelty=1.0, cliche=0.5, normalize_weights=True
    )

    # Cliché should reduce score
    assert score_with_cliche < score_no_cliche
    # The reduction should be proportional to original cliche weight
    # But in normalized version, this gets scaled too

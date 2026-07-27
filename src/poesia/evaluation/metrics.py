"""Individual scoring functions for candidate poem lines.

Each function returns a float in [0, 1] (higher is better), except
`cliche_penalty`, which returns a float in [0, 1] representing penalty
magnitude (higher is worse, gets subtracted in the composite score).

Phase 0 status: interfaces + naive placeholder implementations. Real
implementations depend on `sentence-transformers` (theme/novelty) and a
curated cliché phrase list or n-gram model (KenLM, Phase 2).
"""

from __future__ import annotations

from poesia.phonology.base import ScanResult


def metre_score(scan: ScanResult, target_syllable_count: int) -> float:
    """Score how closely a scanned line matches a target metrical syllable count.

    Returns 1.0 for an exact match, decaying linearly with absolute deviation.
    """
    if target_syllable_count <= 0:
        return 0.0
    deviation = abs(scan.metrical_syllable_count - target_syllable_count)
    return max(0.0, 1.0 - deviation / target_syllable_count)


def rhyme_score(candidate_key: str, target_key: str) -> float:
    """Score rhyme match between a candidate line's rhyme key and a target key.

    Phase 0: exact string match only (1.0 or 0.0). Later: graded similarity
    using phoneme edit distance for near-rhyme / slant-rhyme scoring.
    """
    return 1.0 if candidate_key == target_key else 0.0


def _cosine_similarity(vec1: list[float] | tuple[float, ...], vec2: list[float] | tuple[float, ...]) -> float:
    """Compute cosine similarity between two numeric vectors in pure Python."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (norm1 * norm2)))


def theme_score(candidate_embedding: list[float] | tuple[float, ...], theme_embedding: list[float] | tuple[float, ...]) -> float:
    """Cosine similarity between candidate vector and poem's theme anchor.

    Acts as baseline semantic alignment scoring. Pluggable for higher-order
    cross-encoders or Graph RAG contextual embeddings in Phase 3.
    """
    return _cosine_similarity(candidate_embedding, theme_embedding)


def novelty_score(
    candidate_embedding: list[float] | tuple[float, ...],
    prior_line_embeddings: list[list[float] | tuple[float, ...]],
) -> float:
    """Score how semantically distinct a candidate is from prior poem lines.

    Returns 1.0 - max_similarity(candidate, prior_lines). If no prior lines exist,
    returns 1.0 (maximum novelty).
    """
    if not prior_line_embeddings:
        return 1.0

    max_sim = max(_cosine_similarity(candidate_embedding, prior) for prior in prior_line_embeddings)
    return round(max(0.0, 1.0 - max_sim), 4)



def cliche_penalty(line: str, cliche_phrases: frozenset[str]) -> float:
    """Penalty in [0, 1] for containing known clichéd phrases.

    Phase 0: naive substring matching against a curated phrase set. Phase 2
    upgrade path: KenLM perplexity against a period/poet-specific corpus —
    suspiciously low perplexity indicates formulaic, overused phrasing.
    """
    lowered = line.lower()
    hits = sum(1 for phrase in cliche_phrases if phrase in lowered)
    if hits == 0:
        return 0.0
    return min(1.0, hits * 0.25)


def composite_score(
    metre: float,
    rhyme: float,
    theme: float,
    novelty: float,
    cliche: float,
    weights: dict[str, float] | None = None,
    normalize_weights: bool = True,
) -> float:
    """Combine individual scores into a single ranking value.

    S = w_m*metre + w_r*rhyme + w_t*theme + w_n*novelty - w_c*cliche

    Args:
        metre: Syllable count accuracy score [0, 1]
        rhyme: Rhyme match score [0, 1]
        theme: Semantic theme alignment [0, 1]
        novelty: Distinctness from prior lines [0, 1]
        cliche: Cliché penalty [0, 1] (subtracted)
        weights: Optional custom weights dict
        normalize_weights: If True, redistribute weights of unused signals to
            active ones. This improves score differentiation in degraded mode
            (e.g., when theme=0 because embeddings unavailable). Default True.

    Returns:
        Composite score, typically in [0, 1] when weights normalized.

    Note:
        Scores are intended for ranking candidates within a single generation
        session, not for cross-session comparison.
    """
    w = weights or {
        "metre": 0.3,
        "rhyme": 0.2,
        "theme": 0.25,
        "novelty": 0.15,
        "cliche": 0.1,
    }

    # Identify which signals are active (non-zero)
    # We consider a signal "active" if it's non-zero or if it could vary
    # (theme/rhyme are inactive only when they're exactly 0.0 AND would be 0 for all candidates)
    signals_used = {
        "metre": metre,
        "rhyme": rhyme,
        "theme": theme,
        "novelty": novelty,
    }

    if normalize_weights:
        # Find signals that are actually contributing (non-zero scores exist)
        # Simple heuristic: if ALL signals of a type would be 0, exclude its weight
        # For now, we check if the score is exactly 0.0
        # A better approach would track which signals are "available" but for v1 this works
        
        # Calculate weight sum for active signals (exclude those at 0)
        active_weight_sum = sum(
            w[signal] for signal, score in signals_used.items() 
            if score > 0.0 or signal == "metre"  # metre always active
        )
        
        # If no active signals, fall back to original weights
        if active_weight_sum > 0.0:
            # Normalize weights so active ones sum to 1.0 (ignoring cliche penalty)
            normalization_factor = 1.0 / active_weight_sum
            w = {k: v * normalization_factor for k, v in w.items()}

    return (
        w["metre"] * metre
        + w["rhyme"] * rhyme
        + w["theme"] * theme
        + w["novelty"] * novelty
        - w["cliche"] * cliche
    )

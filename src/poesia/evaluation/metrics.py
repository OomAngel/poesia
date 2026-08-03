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


def _cosine_similarity(
    vec1: list[float] | tuple[float, ...], vec2: list[float] | tuple[float, ...]
) -> float:
    """Compute cosine similarity between two numeric vectors in pure Python."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (norm1 * norm2)))


def theme_score(
    candidate_embedding: list[float] | tuple[float, ...],
    theme_embedding: list[float] | tuple[float, ...],
) -> float:
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


def end_word_penalty(line: str, prior_end_words: set[str]) -> float:
    """Return 0 if the line ends with a word already used as a prior line-end, else 1.

    The penalty is 0 (no penalty) if the word is new, meaning that prior use of the
    exact same word as a line ending incurs a score penalty of 1.0. Punctuation is
    stripped before comparison.

    Args:
        line: Candidate line text.
        prior_end_words: Set of ``str.lower()`` words that have already been used
            as line-ending words in previously committed lines.

    Returns:
        1.0 if the end word is novel, 0.0 (full penalty) if repeated.
    """
    if not prior_end_words:
        return 1.0
    words = line.strip().split()
    if not words:
        return 1.0
    last = words[-1].rstrip(".,;:!?¿¡\"'—").lower()
    return 0.0 if last in prior_end_words else 1.0


def composite_score(
    metre: float,
    rhyme: float,
    theme: float,
    novelty: float,
    cliche: float,
    end_word: float = 1.0,
    fragment_fidelity: float = 0.0,
    weights: dict[str, float] | None = None,
    normalize_weights: bool = True,
) -> float:
    """Combine individual scores into a single ranking value.

    S = w_m*metre + w_r*rhyme + w_t*theme + w_f*fragment_fidelity + w_n*novelty
        - w_c*cliche - w_e*(1 - end_word)

    Args:
        metre: Syllable count accuracy score [0, 1]
        rhyme: Rhyme match score [0, 1]
        theme: Semantic theme alignment [0, 1]
        novelty: Distinctness from prior lines [0, 1]
        cliche: Cliché penalty [0, 1] (subtracted)
        end_word: End-word repetition penalty — 1.0 if novel, 0.0 if repeated.
        fragment_fidelity: Cosine similarity to the source fragment embedding [0, 1].
        weights: Optional custom weights dict
        normalize_weights: If True, redistribute weights of unused signals to
            active ones. Improves score differentiation in degraded mode.

    Returns:
        Composite score, typically in [0, 1] when weights normalized.
    """
    w = weights or {
        "metre": 0.25,
        "rhyme": 0.15,
        "theme": 0.20,
        "novelty": 0.10,
        "cliche": 0.08,
        "end_word": 0.07,
        "fragment_fidelity": 0.15,
    }

    signals_used = {
        "metre": metre,
        "rhyme": rhyme,
        "theme": theme,
        "novelty": novelty,
        "end_word": end_word,
        "fragment_fidelity": fragment_fidelity,
    }

    if normalize_weights:
        active_weight_sum = sum(
            w[signal] for signal, score in signals_used.items() if score > 0.0 or signal == "metre"
        )
        if active_weight_sum > 0.0:
            normalization_factor = 1.0 / active_weight_sum
            w = {k: v * normalization_factor for k, v in w.items()}

    return (
        w["metre"] * metre
        + w["rhyme"] * rhyme
        + w["theme"] * theme
        + w["novelty"] * novelty
        - w["cliche"] * cliche
        + w["end_word"] * end_word
        + w["fragment_fidelity"] * fragment_fidelity
    )

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


def theme_score(candidate_embedding, theme_embedding) -> float:
    """Cosine similarity between a candidate line and the poem's theme anchor.

    Requires sentence-transformers embeddings computed upstream. Phase 0:
    placeholder signature only, not yet wired to sentence-transformers.
    """
    raise NotImplementedError(
        "theme_score requires sentence-transformers integration (Phase 1)."
    )


def novelty_score(candidate_embedding, prior_line_embeddings: list) -> float:
    """Score how semantically distinct a candidate is from prior poem lines.

    Prevents near-redundant lines. Higher = more novel relative to what has
    already been written in this poem.
    """
    raise NotImplementedError(
        "novelty_score requires sentence-transformers integration (Phase 1)."
    )


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
) -> float:
    """Combine individual scores into a single ranking value.

    S = w_m*metre + w_r*rhyme + w_t*theme + w_n*novelty - w_c*cliche
    """
    w = weights or {
        "metre": 0.3,
        "rhyme": 0.2,
        "theme": 0.25,
        "novelty": 0.15,
        "cliche": 0.1,
    }
    return (
        w["metre"] * metre
        + w["rhyme"] * rhyme
        + w["theme"] * theme
        + w["novelty"] * novelty
        - w["cliche"] * cliche
    )

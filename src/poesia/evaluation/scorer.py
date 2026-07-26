"""Composite line/poem scorer tying phonology + metrics together.

This is the single entry point the generation loop calls to rank candidate
lines. It owns no state beyond configuration — the actual embedding /
phonology backends are injected so this class stays testable without heavy
model loading.
"""

from __future__ import annotations

from dataclasses import dataclass

from poesia.evaluation.metrics import composite_score
from poesia.phonology.base import ScanResult


@dataclass
class ScoredCandidate:
    """A candidate line paired with its scan result and composite score."""

    line: str
    scan: ScanResult
    score: float
    breakdown: dict[str, float]


class LineScorer:
    """Ranks candidate lines against form constraints and a theme anchor.

    Phase 0: metre scoring only is functional (via injected phonology
    backend). Theme/novelty scoring is stubbed pending sentence-transformers
    integration (Phase 1).
    """

    def __init__(self, phonology_backend, target_syllable_count: int) -> None:
        self._phonology = phonology_backend
        self._target_syllable_count = target_syllable_count

    def score_candidates(self, candidates: list[str]) -> list[ScoredCandidate]:
        """Scan and score a batch of candidate lines, ranked best-first."""
        scored: list[ScoredCandidate] = []
        for line in candidates:
            scan = self._phonology.scan_line(line)
            from poesia.evaluation.metrics import metre_score

            m_score = metre_score(scan, self._target_syllable_count)
            breakdown = {
                "metre": m_score,
                "rhyme": 0.0,
                "theme": 0.0,
                "novelty": 0.0,
                "cliche": 0.0,
            }
            total = composite_score(**breakdown)
            scored.append(ScoredCandidate(line=line, scan=scan, score=total, breakdown=breakdown))
        return sorted(scored, key=lambda c: c.score, reverse=True)

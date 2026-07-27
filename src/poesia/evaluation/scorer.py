"""Composite line/poem scorer tying phonology + metrics together.

This is the single entry point the generation loop calls to rank candidate
lines. It owns no state beyond configuration — the actual embedding /
phonology backends are injected so this class stays testable without heavy
model loading.

Phase 1 update: Now uses real theme_score/novelty_score when an embedding
client is provided. Falls back to metre-only scoring if no embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from poesia.evaluation.metrics import (
    cliche_penalty,
    composite_score,
    metre_score,
    novelty_score,
    rhyme_score,
    theme_score,
)
from poesia.phonology.base import ScanResult

if TYPE_CHECKING:
    from poesia.memoria.embeddings import EmbeddingClient


@dataclass
class ScoredCandidate:
    """A candidate line paired with its scan result and composite score."""

    line: str
    scan: ScanResult
    score: float
    breakdown: dict[str, float]


# Common Spanish clichés to penalize
SPANISH_CLICHES: frozenset[str] = frozenset([
    "corazón herido", "lágrimas de amor", "eterno amor",
    "dulce mirada", "triste soledad", "amarga pena",
    "luz de mis ojos", "alma mía", "fuego ardiente",
])

ENGLISH_CLICHES: frozenset[str] = frozenset([
    "heart of gold", "break my heart", "eternal love",
    "tears of joy", "light of my life", "soul mate",
])


class LineScorer:
    """Ranks candidate lines against form constraints and a theme anchor.

    When an embedding_client is provided, uses real semantic scoring:
    - theme_score: cosine similarity to theme embedding
    - novelty_score: 1 - max similarity to prior lines
    - cliche_penalty: substring match against known clichés

    Without embedding_client, falls back to metre-only scoring.
    """

    def __init__(
        self,
        phonology_backend,
        target_syllable_count: int,
        embedding_client: EmbeddingClient | None = None,
        theme_text: str | None = None,
        target_rhyme_key: str | None = None,
        language: str = "es",
    ) -> None:
        self._phonology = phonology_backend
        self._target_syllable_count = target_syllable_count
        self._embedding_client = embedding_client
        self._target_rhyme_key = target_rhyme_key
        self._language = language

        # Pre-compute theme embedding if we have both client and theme
        self._theme_embedding: list[float] | None = None
        if embedding_client and theme_text:
            try:
                self._theme_embedding = embedding_client.embed(theme_text)
            except Exception:
                pass  # Fall back to no theme scoring

        # Track prior line embeddings for novelty scoring
        self._prior_embeddings: list[list[float]] = []

        # Select cliché set by language
        self._cliches = SPANISH_CLICHES if language == "es" else ENGLISH_CLICHES

    def score_candidates(
        self,
        candidates: list[str],
        prior_lines: list[str] | None = None,
    ) -> list[ScoredCandidate]:
        """Scan and score a batch of candidate lines, ranked best-first.

        Args:
            candidates: Lines to score
            prior_lines: Previously selected lines (for novelty scoring)

        Returns:
            List of ScoredCandidate sorted by descending score
        """
        # Embed prior lines for novelty scoring
        if prior_lines and self._embedding_client:
            self._prior_embeddings = []
            for line in prior_lines:
                try:
                    self._prior_embeddings.append(self._embedding_client.embed(line))
                except Exception:
                    pass

        scored: list[ScoredCandidate] = []
        for line in candidates:
            scan = self._phonology.scan_line(line)

            # Metre score (always computed)
            m_score = metre_score(scan, self._target_syllable_count)

            # Rhyme score (if target rhyme key provided)
            r_score = 0.0
            if self._target_rhyme_key:
                candidate_rhyme = self._phonology.rhyme_key(line)
                r_score = rhyme_score(candidate_rhyme.consonant, self._target_rhyme_key)

            # Theme score (if embedding client + theme available)
            t_score = 0.0
            candidate_embedding: list[float] | None = None
            if self._embedding_client and self._theme_embedding:
                try:
                    candidate_embedding = self._embedding_client.embed(line)
                    t_score = theme_score(candidate_embedding, self._theme_embedding)
                except Exception:
                    pass

            # Novelty score (if we have prior embeddings)
            n_score = 1.0  # Maximum novelty if no priors
            if candidate_embedding and self._prior_embeddings:
                n_score = novelty_score(candidate_embedding, self._prior_embeddings)

            # Cliché penalty
            c_penalty = cliche_penalty(line, self._cliches)

            breakdown = {
                "metre": m_score,
                "rhyme": r_score,
                "theme": t_score,
                "novelty": n_score,
                "cliche": c_penalty,
            }
            total = composite_score(**breakdown)
            scored.append(ScoredCandidate(line=line, scan=scan, score=total, breakdown=breakdown))

        return sorted(scored, key=lambda c: c.score, reverse=True)

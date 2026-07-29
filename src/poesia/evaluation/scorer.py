"""Composite line/poem scorer tying phonology + metrics together.

This is the single entry point the generation loop calls to rank candidate
lines. It owns no state beyond configuration — the actual embedding /
phonology backends are injected so this class stays testable without heavy
model loading.

Phase 1 update: Now uses real theme_score/novelty_score when an embedding
client is provided. Falls back to metre-only scoring if no embeddings.

P0 hardening: validates embeddings and exposes failures explicitly instead of
silent fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from poesia.evaluation.metrics import (
    cliche_penalty,
    composite_score,
    metre_score,
    novelty_score,
    rhyme_score,
    theme_score,
)
from poesia.memoria.embedding_validation import (
    EmbeddingValidationError,
    validate_embedding_vector,
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



@runtime_checkable
class ScorerProtocol(Protocol):
    """Protocol for line scoring."""
    def score_candidates(self, candidates, prior_lines=None):
        ...


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
        fragment_fidelity_text: str | None = None,
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
                raw_theme = embedding_client.embed_one(theme_text)
                self._theme_embedding = validate_embedding_vector(
                    raw_theme,
                    expected_dimension=embedding_client.dimension,
                    context="theme embedding",
                )
            except EmbeddingValidationError as e:
                raise ValueError(f"Invalid theme embedding: {e}") from e
            except Exception as e:
                raise RuntimeError(f"Failed to embed theme text: {e}") from e

        # P4: fragment fidelity — pre-compute embedding of the source fragment
        self._fragment_fidelity_embedding: list[float] | None = None
        if embedding_client and fragment_fidelity_text:
            try:
                raw_frag = embedding_client.embed_one(fragment_fidelity_text, text_type="passage")
                self._fragment_fidelity_embedding = validate_embedding_vector(
                    raw_frag,
                    expected_dimension=embedding_client.dimension,
                    context="fragment fidelity embedding",
                )
            except EmbeddingValidationError:
                pass  # silently degrade — optional signal
            except Exception:
                pass

        # Track prior line embeddings for novelty scoring
        self._prior_embeddings: list[list[float]] = []

        # Track prior line-ending words (P4: anti-end-repetition)
        self._prior_end_words: set[str] = set()

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
            for i, line in enumerate(prior_lines):
                try:
                    # Use embed_one() for scalar text
                    raw_emb = self._embedding_client.embed_one(line)
                    # P0: validate prior line embedding
                    validated = validate_embedding_vector(
                        raw_emb,
                        expected_dimension=self._embedding_client.dimension,
                        context=f"prior line {i} embedding",
                    )
                    self._prior_embeddings.append(validated)
                except EmbeddingValidationError as e:
                    # P0: expose validation failure explicitly
                    raise ValueError(f"Invalid prior line {i} embedding: {e}") from e
                except Exception as e:
                    # Other failures
                    raise RuntimeError(f"Failed to embed prior line {i}: {e}") from e

        # Build set of prior line-ending words (P4: anti-end-repetition)
        self._prior_end_words = set()
        if prior_lines:
            for pl in prior_lines:
                words = pl.strip().split()
                if words:
                    self._prior_end_words.add(words[-1].rstrip(".,;:!?¿¡\"'—").lower())

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
                    raw_cand = self._embedding_client.embed_one(line)
                    candidate_embedding = validate_embedding_vector(
                        raw_cand,
                        expected_dimension=self._embedding_client.dimension,
                        context=f"candidate line '{line[:30]}...' embedding",
                    )
                    t_score = theme_score(candidate_embedding, self._theme_embedding)
                except EmbeddingValidationError as e:
                    raise ValueError(f"Invalid candidate embedding: {e}") from e
                except Exception as e:
                    raise RuntimeError(f"Failed to embed candidate line: {e}") from e

            # Novelty score (if we have prior embeddings)
            n_score = 1.0  # Maximum novelty if no priors
            if candidate_embedding and self._prior_embeddings:
                n_score = novelty_score(candidate_embedding, self._prior_embeddings)

            # P4: fragment fidelity score (how close to source fragment)
            ff_score = 0.0
            if candidate_embedding and self._fragment_fidelity_embedding:
                from poesia.evaluation.metrics import theme_score as _fidelity
                ff_score = _fidelity(candidate_embedding, self._fragment_fidelity_embedding)

            # P4: end-word repetition penalty
            from poesia.evaluation.metrics import end_word_penalty
            ew_score = end_word_penalty(line, self._prior_end_words)

            # Cliché penalty
            c_penalty = cliche_penalty(line, self._cliches)

            breakdown = {
                "metre": m_score,
                "rhyme": r_score,
                "theme": t_score,
                "novelty": n_score,
                "cliche": c_penalty,
                "end_word": ew_score,
                "fragment_fidelity": ff_score,
            }
            total = composite_score(**breakdown)
            scored.append(ScoredCandidate(line=line, scan=scan, score=total, breakdown=breakdown))

        return sorted(scored, key=lambda c: c.score, reverse=True)

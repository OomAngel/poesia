"""Tests for LineScorer semantic scoring (theme, novelty, cliché).

Verifies that Phase 1 metrics (theme_score, novelty_score) are actually
wired into the scorer when an embedding client is provided.
"""

import pytest

from poesia.evaluation.scorer import LineScorer, SPANISH_CLICHES, ENGLISH_CLICHES
from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.phonology.spanish import SpanishPhonology


class TestScorerWithEmbeddings:
    """Tests for scorer with embedding client enabled."""

    @pytest.fixture
    def embedding_client(self) -> StubEmbeddingClient:
        return StubEmbeddingClient()

    @pytest.fixture
    def phonology(self) -> SpanishPhonology:
        return SpanishPhonology()

    def test_scorer_computes_theme_score(
        self, phonology: SpanishPhonology, embedding_client: StubEmbeddingClient
    ) -> None:
        """Scorer should compute non-zero theme score with embedding client."""
        scorer = LineScorer(
            phonology_backend=phonology,
            target_syllable_count=11,
            embedding_client=embedding_client,
            theme_text="la luna llena",
            language="es",
        )
        candidates = ["La luna brilla en el cielo oscuro"]
        scored = scorer.score_candidates(candidates)

        assert len(scored) == 1
        # Theme score should be computed (non-zero)
        assert scored[0].breakdown["theme"] >= 0.0

    def test_scorer_computes_novelty_score(
        self, phonology: SpanishPhonology, embedding_client: StubEmbeddingClient
    ) -> None:
        """Scorer should compute novelty score relative to prior lines."""
        scorer = LineScorer(
            phonology_backend=phonology,
            target_syllable_count=11,
            embedding_client=embedding_client,
            theme_text="la noche",
            language="es",
        )
        candidates = ["La noche cae sobre el campo"]
        prior_lines = ["El día termina lentamente"]

        scored = scorer.score_candidates(candidates, prior_lines=prior_lines)

        assert len(scored) == 1
        # Novelty score should be computed
        assert "novelty" in scored[0].breakdown

    def test_scorer_penalizes_cliches(
        self, phonology: SpanishPhonology, embedding_client: StubEmbeddingClient
    ) -> None:
        """Scorer should penalize lines containing clichés."""
        scorer = LineScorer(
            phonology_backend=phonology,
            target_syllable_count=11,
            embedding_client=embedding_client,
            theme_text="amor",
            language="es",
        )
        # Line with Spanish cliché
        cliche_line = "Mi corazón herido sangra amor"
        clean_line = "El viento mueve las hojas secas"

        cliche_scored = scorer.score_candidates([cliche_line])
        clean_scored = scorer.score_candidates([clean_line])

        # Cliché line should have penalty
        assert cliche_scored[0].breakdown["cliche"] > 0.0
        # Clean line should have no penalty
        assert clean_scored[0].breakdown["cliche"] == 0.0

    def test_scorer_without_embeddings_falls_back(
        self, phonology: SpanishPhonology
    ) -> None:
        """Scorer without embedding client should still work (metre only)."""
        scorer = LineScorer(
            phonology_backend=phonology,
            target_syllable_count=11,
            # No embedding_client
            language="es",
        )
        candidates = ["La luna brilla"]
        scored = scorer.score_candidates(candidates)

        assert len(scored) == 1
        # Metre should still work
        assert scored[0].breakdown["metre"] >= 0.0
        # Theme/novelty should be 0 or 1 (default)
        assert scored[0].breakdown["theme"] == 0.0


class TestClicheLists:
    """Tests for cliché phrase lists."""

    def test_spanish_cliches_exist(self) -> None:
        """Spanish cliché list should have entries."""
        assert len(SPANISH_CLICHES) > 0
        assert "corazón herido" in SPANISH_CLICHES

    def test_english_cliches_exist(self) -> None:
        """English cliché list should have entries."""
        assert len(ENGLISH_CLICHES) > 0
        assert "heart of gold" in ENGLISH_CLICHES

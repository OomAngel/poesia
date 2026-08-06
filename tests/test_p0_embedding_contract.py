"""P0 RAG/LLM hardening: embedding validation at the retriever boundary.

These tests verify that malformed embeddings (the P0 scalar/batch confusion
bug) are caught at ingest/retrieve time and exposed explicitly, rather than
silently degrading to 0.0 scores. Pure validation logic itself is tested in
test_embedding_validation.py; this file covers the integration boundary.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.graphrag import GraphRAGRetriever
from poesia.memoria.library import PoemRecord


def _record(poem_id: str, theme: str) -> PoemRecord:
    """Helper to create a test poem record."""
    return PoemRecord(
        id=poem_id,
        lines=["test line one", "test line two"],
        language="es",
        form="soneto",
        theme=theme,
        created_at=datetime.now(),
        tags=[],
    )


def test_malformed_manual_embeddings_caught_at_ingest() -> None:
    """Nested list (scalar/batch confusion), dimension, and NaN are rejected."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()

    malformed_nested = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
    with pytest.raises(ValueError, match="nested list"):
        retriever.ingest([_record("p1", "test theme")],
                         embeddings={"p1": malformed_nested}, embedding_client=client)

    with pytest.raises(ValueError, match="dimension mismatch"):
        retriever.ingest([_record("p1", "test theme")],
                         embeddings={"p1": [0.1, 0.2, 0.3]}, embedding_client=client)

    with pytest.raises(ValueError, match="non-finite"):
        retriever.ingest([_record("p1", "test theme")],
                         embeddings={"p1": [0.1] * 383 + [float("nan")]},
                         embedding_client=client)


def test_invalid_query_embedding_caught_at_retrieve() -> None:
    """Malformed query embeddings are caught at retrieve time."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    retriever.ingest([_record("p1", "test theme")], embedding_client=client)

    malformed_query = [[0.1] * 384, [0.2] * 384]
    with pytest.raises(ValueError, match="(?i)invalid query embedding"):
        retriever.retrieve(malformed_query)  # type: ignore[arg-type]


def test_broken_embed_client_failures_are_exposed() -> None:
    """A buggy adapter's malformed embed_one output raises, not silent fallback."""

    class BrokenEmbeddingClient:
        @property
        def model_id(self) -> str:
            return "broken-client"

        @property
        def dimension(self) -> int:
            return 384

        def embed(self, texts: list[str], text_type: str = "query") -> list[list[float]]:
            return [[0.1] * 384 for _ in texts]

        def embed_one(self, text: str, text_type: str = "query") -> list[float]:
            # BUG: returns nested list instead of flat vector
            return [[0.1] * 384]  # type: ignore[return-value]

    retriever = GraphRAGRetriever(storage_path=":memory:")
    with pytest.raises(ValueError, match="(?i)failed to auto-embed record p1"):
        retriever.ingest([_record("p1", "test theme")],
                         embedding_client=BrokenEmbeddingClient())


def test_scorer_validates_theme_embedding_at_construction() -> None:
    """LineScorer validates theme embeddings when built with an embedding client."""
    from poesia.evaluation.scorer import LineScorer
    from poesia.phonology.spanish import SpanishPhonology

    class BrokenEmbeddingClient:
        @property
        def model_id(self) -> str:
            return "broken"

        @property
        def dimension(self) -> int:
            return 384

        def embed_one(self, text: str) -> list[float]:
            return [[0.1] * 384]  # type: ignore[return-value]

    with pytest.raises(ValueError, match="(?i)invalid theme embedding"):
        LineScorer(
            phonology_backend=SpanishPhonology(),
            target_syllable_count=11,
            embedding_client=BrokenEmbeddingClient(),
            theme_text="amor eterno",
        )

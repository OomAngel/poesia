"""P0 RAG/LLM hardening: embedding contract enforcement tests.

These tests verify that the critical P0 bug (scalar/batch confusion) and
other embedding validation failures are caught early and exposed explicitly
rather than silently degrading to 0.0 scores.
"""

from __future__ import annotations

import pytest

from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.graphrag import GraphRAGRetriever
from poesia.memoria.library import PoemRecord
from datetime import datetime


def _record(poem_id: str, theme: str, lines: list[str] | None = None) -> PoemRecord:
    """Helper to create a test poem record."""
    return PoemRecord(
        id=poem_id,
        lines=lines or ["test line one", "test line two"],
        language="es",
        form="soneto",
        theme=theme,
        created_at=datetime.now(),
        tags=[],
    )


def test_malformed_embedding_from_manual_dict_is_caught() -> None:
    """P0: Manually-provided malformed embeddings are caught at ingest."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()

    # Simulate the P0 bug: nested list from scalar/batch confusion
    # This is what embed("abc") produces: shape (3, 384) instead of (384,)
    malformed_nested = [
        [0.1] * 384,  # Character 'a'
        [0.2] * 384,  # Character 'b'
        [0.3] * 384,  # Character 'c'
    ]

    records = [_record("p1", "test theme")]
    embeddings = {"p1": malformed_nested}

    # Should raise ValueError with clear message
    with pytest.raises(ValueError) as exc_info:
        retriever.ingest(records, embeddings=embeddings, embedding_client=client)

    err_msg = str(exc_info.value).lower()
    assert "invalid embedding for record p1" in err_msg
    assert "nested list" in err_msg


def test_dimension_mismatch_is_caught() -> None:
    """P0: Embeddings with wrong dimension are caught at ingest."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()  # dimension = 384

    records = [_record("p1", "test theme")]
    # Provide embedding with wrong dimension
    embeddings = {"p1": [0.1, 0.2, 0.3]}  # Only 3 dims, expected 384

    with pytest.raises(ValueError) as exc_info:
        retriever.ingest(records, embeddings=embeddings, embedding_client=client)

    err_msg = str(exc_info.value)
    assert "dimension mismatch" in err_msg.lower()
    assert "expected 384" in err_msg
    assert "got 3" in err_msg


def test_nan_in_embedding_is_caught() -> None:
    """P0: NaN values in embeddings are caught at ingest."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()

    records = [_record("p1", "test theme")]
    # Embedding with NaN
    embedding_with_nan = [0.1] * 383 + [float("nan")]
    embeddings = {"p1": embedding_with_nan}

    with pytest.raises(ValueError) as exc_info:
        retriever.ingest(records, embeddings=embeddings, embedding_client=client)

    err_msg = str(exc_info.value).lower()
    assert "non-finite" in err_msg


def test_invalid_query_embedding_is_caught() -> None:
    """P0: Invalid query embeddings are caught at retrieve time."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()

    # Ingest valid record
    records = [_record("p1", "test theme")]
    retriever.ingest(records, embedding_client=client)

    # Try to retrieve with malformed query (nested list)
    malformed_query = [[0.1] * 384, [0.2] * 384]

    with pytest.raises(ValueError) as exc_info:
        retriever.retrieve(malformed_query)  # type: ignore

    err_msg = str(exc_info.value).lower()
    assert "invalid query embedding" in err_msg
    assert "nested list" in err_msg


def test_auto_embed_validation_exposes_failures() -> None:
    """P0: Auto-embedding validation failures are exposed, not silenced."""
    # This test simulates what would happen if embed_one() returned
    # a malformed result (e.g., from a buggy adapter)

    class BrokenEmbeddingClient:
        """Mock client that returns nested lists (the P0 bug)."""

        @property
        def model_id(self) -> str:
            return "broken-client"

        @property
        def dimension(self) -> int:
            return 384

        def embed(self, texts: list[str], text_type: str = "query") -> list[list[float]]:
            # Correct implementation
            return [[0.1] * 384 for _ in texts]

        def embed_one(self, text: str, text_type: str = "query") -> list[float]:
            # BUG: returns nested list instead of flat vector
            # This simulates the scalar/batch confusion
            return [[0.1] * 384]  # type: ignore

    retriever = GraphRAGRetriever(storage_path=":memory:")
    broken_client = BrokenEmbeddingClient()

    records = [_record("p1", "test theme")]

    # Should raise ValueError with clear message, not silent fallback
    with pytest.raises(ValueError) as exc_info:
        retriever.ingest(records, embedding_client=broken_client)

    err_msg = str(exc_info.value).lower()
    assert "failed to auto-embed record p1" in err_msg
    assert "nested list" in err_msg


def test_scorer_theme_embedding_validation() -> None:
    """P0: LineScorer validates theme embeddings at construction."""
    from poesia.evaluation.scorer import LineScorer
    from poesia.phonology.spanish import SpanishPhonology

    class BrokenEmbeddingClient:
        """Mock client that returns invalid embeddings."""

        @property
        def model_id(self) -> str:
            return "broken"

        @property
        def dimension(self) -> int:
            return 384

        def embed_one(self, text: str) -> list[float]:
            # Return nested list (the P0 bug)
            return [[0.1] * 384]  # type: ignore

    phonology = SpanishPhonology()
    broken_client = BrokenEmbeddingClient()

    # Should raise ValueError when trying to embed theme
    with pytest.raises(ValueError) as exc_info:
        LineScorer(
            phonology_backend=phonology,
            target_syllable_count=11,
            embedding_client=broken_client,
            theme_text="amor eterno",
        )

    err_msg = str(exc_info.value).lower()
    assert "invalid theme embedding" in err_msg


def test_p0_complete_validation_journey() -> None:
    """P0: Complete end-to-end validation from ingest through retrieval."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()

    # Valid ingest
    records = [
        _record("p1", "noche estrellada"),
        _record("p2", "amor perdido"),
    ]
    retriever.ingest(records, embedding_client=client)

    # Valid retrieval
    query = client.embed_one("luna brillante")
    results = retriever.retrieve(query, k=2)

    # Should get actual results with non-zero scores
    assert len(results) == 2
    poem_ids = [pid for pid, _ in results]
    assert "p1" in poem_ids
    assert "p2" in poem_ids

    # All scores should be non-zero (validated embeddings)
    scores = [score for _, score in results]
    assert all(s > 0.0 for s in scores), (
        "P0 validation ensures compatible embeddings, so scores must be non-zero"
    )

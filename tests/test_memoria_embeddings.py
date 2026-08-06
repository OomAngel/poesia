"""Tests for MemorIA embedding clients.

Stub behavior is deterministic and self-contained; real sentence-transformers
model loading is an integration concern, gated so the unit suite stays fast
and hermetic (no model downloads in CI).
"""

from __future__ import annotations

import pytest

from poesia.memoria.embeddings import (
    StubEmbeddingClient,
    get_embedding_client,
)


def test_stub_embedding_client_contract() -> None:
    """Stub: correct dimension, deterministic per text, distinct across texts."""
    client = StubEmbeddingClient()
    assert client.model_id == "stub-embedding-client"
    assert client.dimension == 384

    emb = client.embed_one("same text")
    assert len(emb) == 384
    assert all(isinstance(v, float) for v in emb)
    assert emb == client.embed_one("same text")  # deterministic
    assert emb != client.embed_one("text two")   # distinct across texts

    batch = client.embed(["hello world", "goodbye moon", "test phrase"])
    assert len(batch) == 3
    assert all(len(e) == 384 for e in batch)


def test_get_embedding_client_with_stub() -> None:
    client = get_embedding_client(use_stub=True)
    assert isinstance(client, StubEmbeddingClient)


# Real sentence-transformers model loading is a slow integration concern.
# Keep it explicit and skippable rather than a silent 3.7s hit on every run.
def _has_sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _has_sentence_transformers(),
    reason="sentence-transformers not installed",
)
def test_sentence_transformer_client_real_integration() -> None:
    """Real model round-trip — runs only where sentence-transformers exists."""
    from poesia.memoria.embeddings import SentenceTransformerClient

    client = SentenceTransformerClient("all-MiniLM-L6-v2")
    emb = client.embed_one("test sentence")
    assert len(emb) == 384
    assert all(isinstance(v, float) for v in emb)


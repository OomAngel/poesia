"""Tests for MemorIA embedding clients."""

from __future__ import annotations

import pytest

from poesia.memoria.embeddings import (
    StubEmbeddingClient,
    get_embedding_client,
)


def _has_sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def test_stub_embedding_client_properties() -> None:
    client = StubEmbeddingClient()
    assert client.model_id == "stub-embedding-client"
    assert client.dimension == 384


def test_stub_embedding_client_embed_returns_correct_shape() -> None:
    client = StubEmbeddingClient()
    texts = ["hello world", "goodbye moon", "test phrase"]
    embeddings = client.embed(texts)

    assert len(embeddings) == 3
    for emb in embeddings:
        assert len(emb) == 384
        assert all(isinstance(v, float) for v in emb)


def test_stub_embedding_client_embed_one() -> None:
    client = StubEmbeddingClient()
    emb = client.embed_one("single text")
    assert len(emb) == 384


def test_stub_embedding_client_deterministic() -> None:
    client = StubEmbeddingClient()
    emb1 = client.embed_one("same text")
    emb2 = client.embed_one("same text")
    assert emb1 == emb2


def test_stub_embedding_client_different_texts_different_embeddings() -> None:
    client = StubEmbeddingClient()
    emb1 = client.embed_one("text one")
    emb2 = client.embed_one("text two")
    assert emb1 != emb2


def test_get_embedding_client_with_stub() -> None:
    client = get_embedding_client(use_stub=True)
    assert isinstance(client, StubEmbeddingClient)


def test_get_embedding_client_default_returns_sentence_transformer() -> None:
    # This test only checks the type, doesn't actually load the model
    from poesia.memoria.embeddings import SentenceTransformerClient

    client = get_embedding_client(use_stub=False)
    assert isinstance(client, SentenceTransformerClient)
    assert client.model_id == "intfloat/multilingual-e5-base"


# Integration test — only runs if sentence-transformers is installed
@pytest.mark.skipif(
    not _has_sentence_transformers(),
    reason="sentence-transformers not installed",
)
def test_sentence_transformer_client_integration() -> None:
    from poesia.memoria.embeddings import SentenceTransformerClient

    # Use a small model for faster testing
    client = SentenceTransformerClient("all-MiniLM-L6-v2")
    emb = client.embed_one("test sentence")

    assert len(emb) == 384  # MiniLM dimension
    assert all(isinstance(v, float) for v in emb)

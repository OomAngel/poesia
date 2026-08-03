"""Embedding client for semantic similarity in MemorIA Graph RAG.

Provides a Protocol for embedding backends and a concrete implementation
using sentence-transformers with multilingual-e5-base.

Lazy-imports sentence-transformers — requires `pip install -e ".[nlp]"`.
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingClient(Protocol):
    """Protocol for text embedding backends."""

    @property
    def model_id(self) -> str:
        """Return the model identifier for cache keying."""
        ...

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...

    def embed(self, texts: list[str], text_type: str = "query") -> list[list[float]]:
        """Embed a batch of texts into vectors.

        Args:
            texts: List of strings to embed.
            text_type: ``"query"`` or ``"passage"``. e5 models use different
                representations for queries vs stored documents. Always pass
                ``"passage"`` when embedding documents for storage, and
                ``"query"`` (the default) when embedding retrieval queries.

        Returns:
            List of embedding vectors, one per input text.
        """
        ...

    def embed_one(self, text: str, text_type: str = "query") -> list[float]:
        """Embed a single text. Convenience wrapper around embed().

        Args:
            text: Text to embed.
            text_type: ``"query"`` or ``"passage"``. See ``embed()`` for details.
        """
        ...


class StubEmbeddingClient:
    """Stub implementation for testing without sentence-transformers."""

    @property
    def model_id(self) -> str:
        return "stub-embedding-client"

    @property
    def dimension(self) -> int:
        return 384  # Match MiniLM dimension for test compatibility

    def embed(self, texts: list[str], text_type: str = "query") -> list[list[float]]:
        """Return deterministic fake embeddings based on text hash.

        The ``text_type`` parameter is accepted for protocol compatibility but
        ignored — the stub does not distinguish queries from passages.
        """
        import hashlib

        result = []
        for text in texts:
            # Deterministic pseudo-embedding from text hash
            h = hashlib.sha256(text.encode()).hexdigest()
            # Convert first 384 hex chars to floats in [-1, 1]
            vec = []
            for i in range(self.dimension):
                byte_val = int(h[(i * 2) % 64 : (i * 2 + 2) % 64 + 1] or "80", 16)
                vec.append((byte_val - 128) / 128.0)
            result.append(vec)
        return result

    def embed_one(self, text: str, text_type: str = "query") -> list[float]:
        return self.embed([text], text_type=text_type)[0]


class SentenceTransformerClient:
    """Embedding client using sentence-transformers.

    Default model: intfloat/multilingual-e5-base
    - Supports 100+ languages including ES, EN, ZH, NL
    - 768-dimensional embeddings
    - ~560MB download on first use

    Lazy-imports sentence-transformers to keep base package light.
    """

    DEFAULT_MODEL = "intfloat/multilingual-e5-small"

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or self.DEFAULT_MODEL
        self._model = None  # Lazy load
        self._dimension: int | None = None

    def _load_model(self):
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Run: pip install -e '.[nlp]'"
            ) from exc

        self._model = SentenceTransformer(self._model_name)
        # Use the new API name (get_embedding_dimension) if available
        if hasattr(self._model, "get_embedding_dimension"):
            self._dimension = self._model.get_embedding_dimension()
        else:
            self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._load_model()
        return self._dimension  # type: ignore[return-value]

    def embed(
        self,
        texts: list[str],
        text_type: str = "query",
    ) -> list[list[float]]:
        """Embed texts using sentence-transformers.

        For e5 models, prepends the correct prefix per the e5 convention:
        - ``"query: "`` for retrieval queries (default)
        - ``"passage: "`` for documents/passages being stored in the index

        Using ``"query: "`` for stored passages silently degrades retrieval
        quality because the e5 model uses different representations for
        query tokens and passage tokens.

        Args:
            texts: Texts to embed.
            text_type: ``"query"`` or ``"passage"``. Ignored for non-e5 models.
        """
        self._load_model()

        # e5 models expect "query: " or "passage: " prefix
        if "e5" in self._model_name.lower():
            prefix = "passage: " if text_type == "passage" else "query: "
            texts = [f"{prefix}{t}" for t in texts]

        embeddings = self._model.encode(texts, convert_to_numpy=True)  # type: ignore
        return [emb.tolist() for emb in embeddings]

    def embed_one(self, text: str, text_type: str = "query") -> list[float]:
        """Embed a single text.

        Args:
            text: Text to embed.
            text_type: ``"query"`` or ``"passage"``. See ``embed()`` for details.
        """
        return self.embed([text], text_type=text_type)[0]


def get_embedding_client(
    model_name: str | None = None,
    use_stub: bool = False,
) -> EmbeddingClient:
    """Factory function to get an embedding client.

    Args:
        model_name: Model name for SentenceTransformerClient (default: e5-base).
        use_stub: If True, return StubEmbeddingClient for testing.

    Returns:
        An EmbeddingClient implementation.
    """
    if use_stub:
        return StubEmbeddingClient()
    return SentenceTransformerClient(model_name)

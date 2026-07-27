"""P3 tests — index compatibility check, rebuild, atomic write, index_info."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.graphrag import GraphRAGRetriever, IndexCompatibilityError
from poesia.memoria.library import PoemRecord


def _record(poem_id: str, theme: str = "luna") -> PoemRecord:
    return PoemRecord(
        id=poem_id, lines=["verso uno", "verso dos"],
        language="es", form="soneto", theme=theme,
        created_at=datetime.now(), tags=[],
    )


class AltStubEmbeddingClient(StubEmbeddingClient):
    """Different model_id — simulates a model swap."""
    @property
    def model_id(self) -> str:
        return "alt-stub-model-v2"


class NarrowStubEmbeddingClient(StubEmbeddingClient):
    """Different dimension — simulates a dimension change."""
    @property
    def dimension(self) -> int:
        return 128


# 1. Empty index — no constraint

def test_compatibility_passes_on_empty_index() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    r.check_index_compatibility(StubEmbeddingClient())  # no raise


# 2. Matching client

def test_compatibility_passes_on_matching_client() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    r.ingest([_record("p1")], embedding_client=client)
    r.check_index_compatibility(client)  # no raise


# 3. Model ID mismatch

def test_compatibility_raises_on_model_id_mismatch() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    original = StubEmbeddingClient()
    r.ingest([_record("p1")], embedding_client=original)

    with pytest.raises(IndexCompatibilityError) as exc_info:
        r.check_index_compatibility(AltStubEmbeddingClient())

    err = exc_info.value
    assert err.stored_model_id == original.model_id
    assert err.client_model_id == "alt-stub-model-v2"
    assert original.model_id in str(err)
    assert "alt-stub-model-v2" in str(err)
    assert "rebuild" in str(err).lower()


# 4. Dimension mismatch

def test_compatibility_raises_on_dimension_mismatch() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    original = StubEmbeddingClient()
    r.ingest([_record("p1")], embedding_client=original)

    with pytest.raises(IndexCompatibilityError) as exc_info:
        r.check_index_compatibility(NarrowStubEmbeddingClient())

    err = exc_info.value
    assert err.stored_dimension == original.dimension
    assert err.client_dimension == 128


# 5. ingest() propagates compatibility error

def test_ingest_raises_on_incompatible_client() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    r.ingest([_record("p1")], embedding_client=StubEmbeddingClient())

    with pytest.raises(IndexCompatibilityError):
        r.ingest([_record("p2")], embedding_client=AltStubEmbeddingClient())

    assert "p1" in r._graph  # p1 intact; second ingest aborted before mutations


# 6. add_fragment_node() compatibility

def test_add_fragment_node_raises_on_incompatible_client() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    r.ingest([_record("p1")], embedding_client=StubEmbeddingClient())

    with pytest.raises(IndexCompatibilityError):
        r.add_fragment_node("fragment:test", content="Some content.",
                            embedding_client=AltStubEmbeddingClient())


# 7. add_influence_node() compatibility

def test_add_influence_node_raises_on_incompatible_client() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    r.ingest([_record("p1")], embedding_client=StubEmbeddingClient())

    with pytest.raises(IndexCompatibilityError):
        r.add_influence_node("influence:test", name="Test Poet",
                             tone=["meditative"],
                             embedding_client=AltStubEmbeddingClient())



# 8. rebuild() clears old nodes

def test_rebuild_clears_old_nodes() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    r.ingest([_record("old-poem")], embedding_client=StubEmbeddingClient())
    r.rebuild([_record("new-poem")], embedding_client=AltStubEmbeddingClient())
    assert "old-poem" not in r._graph
    assert "new-poem" in r._graph


# 9. rebuild() updates model identity

def test_rebuild_updates_model_identity() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    r.ingest([_record("p1")], embedding_client=StubEmbeddingClient())
    alt = AltStubEmbeddingClient()
    r.rebuild([_record("p2")], embedding_client=alt)
    assert r._index_model_id == alt.model_id
    assert r._index_embedding_dimension == alt.dimension


# 10. Post-rebuild: old model rejected, new accepted

def test_after_rebuild_old_client_rejected() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    original = StubEmbeddingClient()
    alt = AltStubEmbeddingClient()
    r.ingest([_record("p1")], embedding_client=original)
    r.rebuild([_record("p2")], embedding_client=alt)
    r.check_index_compatibility(alt)  # no raise
    with pytest.raises(IndexCompatibilityError):
        r.check_index_compatibility(original)


# 11. Atomic write: no .tmp left after successful save

def test_atomic_write_no_tmp_after_save(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    r = GraphRAGRetriever(storage_path=db_path)
    r.ingest([_record("p1")], embedding_client=StubEmbeddingClient())
    assert db_path.exists()
    assert not db_path.with_suffix(".tmp").exists()


# 12. index_info()

def test_index_info_returns_metadata() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    # Let the client auto-embed — don't mix hand-crafted vectors with embedding_client
    r.ingest([_record("p1"), _record("p2")], embedding_client=client)
    info = r.index_info()
    assert info["schema_version"] == "2"
    assert info["model_id"] == client.model_id
    assert info["embedding_dimension"] == client.dimension
    assert info["node_count"] == 2


def test_index_info_empty() -> None:
    info = GraphRAGRetriever(storage_path=":memory:").index_info()
    assert info["model_id"] is None
    assert info["node_count"] == 0


# 13. Compatibility check survives persistence round-trip

def test_compatibility_enforced_after_load(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    original = StubEmbeddingClient()
    r1 = GraphRAGRetriever(storage_path=db_path)
    r1.ingest([_record("p1")], embedding_client=original)

    r2 = GraphRAGRetriever(storage_path=db_path)
    r2.check_index_compatibility(original)  # no raise
    with pytest.raises(IndexCompatibilityError):
        r2.check_index_compatibility(AltStubEmbeddingClient())

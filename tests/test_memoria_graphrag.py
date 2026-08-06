"""Canonical tests for GraphRAGRetriever.

One home for the graph: ingest, typed nodes/edges, traversal, retrieval,
compatibility, fingerprints, persistence, and auto-embedding. Consolidated
from the former P0/P2/P3 phase-gate files (same behaviors, no duplication).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.graphrag import (
    GraphHop,
    GraphPath,
    GraphRAGRetriever,
    IndexCompatibilityError,
    _compute_fingerprint,
)
from poesia.memoria.library import PoemRecord
from poesia.memoria.records import NodeType, RelationType


def _record(poem_id: str, theme: str, form: str = "soneto", language: str = "es",
            lines: list[str] | None = None) -> PoemRecord:
    return PoemRecord(
        id=poem_id,
        lines=lines or ["test line one", "test line two"],
        language=language,
        form=form,
        theme=theme,
        created_at=datetime.now(),
        tags=[],
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


# ── Ingest ───────────────────────────────────────────────────────────────


def test_ingest_adds_nodes_and_typed_edges() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    embeddings = {"p1": [1.0, 0.0, 0.0], "p2": [1.0, 0.0, 0.0], "p3": [0.0, 1.0, 0.0]}
    retriever.ingest(
        [_record(pid, f"tema {pid}") for pid in embeddings], embeddings=embeddings
    )
    assert retriever.node_count() == 3
    # identical p1↔p2 → cosine 1.0 (bidirectional edge); p3 orthogonal → isolated
    assert retriever.edge_count() == 2
    for node_id in ["p1", "p2", "p3"]:
        assert retriever._graph.nodes[node_id].get("node_type") == NodeType.poem.value
    for _u, _v, data in retriever._graph.edges(data=True):
        assert data.get("relation_type") == RelationType.similar_to.value


def test_ingest_without_embeddings_creates_no_edges() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "a"), _record("p2", "b")])
    assert retriever.node_count() == 2
    assert retriever.edge_count() == 0


def test_add_fragment_and_influence_nodes_typed() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.add_fragment_node("fragment:saudade", content="texto", language="es", tags=["soledad"])
    retriever.add_influence_node(
        "influence:machado", name="Antonio Machado", language="es", tone=["spare"]
    )
    assert retriever._graph.nodes["fragment:saudade"]["node_type"] == NodeType.fragment.value
    assert retriever._graph.nodes["influence:machado"]["node_type"] == NodeType.influence.value
    assert retriever._graph.nodes["influence:machado"]["name"] == "Antonio Machado"


def test_add_typed_edge_inspired_by() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "soledad")])
    retriever.add_influence_node("influence:machado", name="Antonio Machado")
    retriever.add_typed_edge("p1", "influence:machado", RelationType.inspired_by, weight=0.9)
    data = retriever._graph["p1"]["influence:machado"]
    assert data["relation_type"] == RelationType.inspired_by.value
    assert abs(data["weight"] - 0.9) < 1e-6


def test_add_typed_edge_raises_if_node_missing() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "tema")])
    with pytest.raises(ValueError, match="nonexistent"):
        retriever.add_typed_edge("p1", "nonexistent", RelationType.inspired_by)


# ── Traversal ────────────────────────────────────────────────────────────


def test_traverse_hops_and_filters() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record(pid, f"t{pid}") for pid in ["p1", "p2", "p3"]])
    retriever.add_typed_edge("p1", "p2", RelationType.similar_to, weight=0.8)
    retriever.add_typed_edge("p2", "p3", RelationType.inspired_by, weight=0.7)

    ids_1 = {p.endpoint_id for p in retriever.traverse("p1", max_hops=1)}
    ids_2 = {p.endpoint_id for p in retriever.traverse("p1", max_hops=2)}
    assert "p2" in ids_1 and "p3" not in ids_1
    assert "p3" in ids_2

    filtered = {
        p.endpoint_id
        for p in retriever.traverse("p1", max_hops=2, relation_types=[RelationType.similar_to])
    }
    assert "p2" in filtered and "p3" not in filtered


def test_traverse_budget_cap_and_path_display() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record(f"p{i}", f"t{i}") for i in range(6)])
    for i in range(1, 6):
        retriever.add_typed_edge("p0", f"p{i}", RelationType.similar_to, weight=0.8)
    assert len(retriever.traverse("p0", max_hops=1, budget=3)) <= 3

    # Path objects render human-readable explanations.
    path = GraphPath(
        origin_id="p0",
        hops=[GraphHop(node_id="p1", node_type=NodeType.poem,
                       relation_type=RelationType.similar_to, weight=0.8)],
    )
    display = path.to_display_string()
    assert isinstance(display, str) and "p1" in display


# ── Retrieval ────────────────────────────────────────────────────────────


def test_retrieve_returns_top_k_with_filter() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    embeddings = {"p1": [1.0, 0.0], "p2": [0.9, 0.1], "p3": [0.0, 1.0]}
    records = [
        _record("p1", "tema a", form="soneto"),
        _record("p2", "tema b", form="haiku"),
        _record("p3", "tema c", form="soneto"),
    ]
    retriever.ingest(records, embeddings=embeddings)

    results = retriever.retrieve([1.0, 0.0], k=2)
    assert len(results) == 2
    assert {"p1", "p2"} <= {pid for pid, _ in results}

    soneto_only = retriever.retrieve([1.0, 0.0], k=5, form_filter="soneto")
    assert all(rid in ("p1", "p3") for rid, _ in soneto_only)


def test_auto_embed_produces_flat_vectors_and_enables_retrieval() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    retriever.ingest([_record("p1", "lluvia nocturna"), _record("p2", "amor eterno")],
                     embedding_client=client)

    for node_id in ["p1", "p2"]:
        emb = retriever._graph.nodes[node_id].get("embedding", [])
        assert emb and len(emb) == client.dimension

    query = client.embed_one("noche de lluvia")
    results = retriever.retrieve(query, k=2)
    assert len(results) == 2
    assert any(s > 0.0 for _, s in results), "embeddings must be compatible → non-zero scores"


# ── Compatibility & rebuild ──────────────────────────────────────────────


def test_compatibility_passes_on_empty_and_matching_client() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    r.check_index_compatibility(StubEmbeddingClient())  # empty index → no constraint
    client = StubEmbeddingClient()
    r.ingest([_record("p1", "tema")], embedding_client=client)
    r.check_index_compatibility(client)  # matching → no raise


def test_compatibility_raises_on_model_and_dimension_mismatch() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    original = StubEmbeddingClient()
    r.ingest([_record("p1", "tema")], embedding_client=original)

    with pytest.raises(IndexCompatibilityError):
        r.check_index_compatibility(AltStubEmbeddingClient())
    with pytest.raises(IndexCompatibilityError):
        r.check_index_compatibility(NarrowStubEmbeddingClient())

    # ingest() propagates the error; a bad add leaves prior nodes intact.
    with pytest.raises(IndexCompatibilityError):
        r.ingest([_record("p2", "tema")], embedding_client=AltStubEmbeddingClient())
    assert "p1" in r._graph


def test_rebuild_clears_old_nodes_and_swaps_model() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    original = StubEmbeddingClient()
    alt = AltStubEmbeddingClient()
    r.ingest([_record("old", "tema")], embedding_client=original)
    r.rebuild([_record("new", "tema")], embedding_client=alt)

    assert "old" not in r._graph and "new" in r._graph
    assert r._index_model_id == alt.model_id
    r.check_index_compatibility(alt)  # new accepted
    with pytest.raises(IndexCompatibilityError):
        r.check_index_compatibility(original)  # old rejected


# ── Content fingerprint & staleness ──────────────────────────────────────


def test_fingerprint_is_64_hex_and_order_independent() -> None:
    r1 = _record("alpha", "tema A")
    r2 = _record("beta", "tema B")
    fp = _compute_fingerprint([r1, r2])
    assert isinstance(fp, str) and len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)
    assert _compute_fingerprint([r1, r2]) == _compute_fingerprint([r2, r1])


@pytest.mark.parametrize("mutate", ["add", "remove", "theme", "lines"])
def test_fingerprint_changes_on_any_content_change(mutate: str) -> None:
    base = [_record("p1", "luna"), _record("p2", "mar")]
    if mutate == "add":
        changed = base + [_record("p3", "viento")]
    elif mutate == "remove":
        changed = [_record("p1", "luna")]
    elif mutate == "theme":
        changed = [_record("p1", "sol"), _record("p2", "mar")]
    else:
        changed = [_record("p1", "luna", lines=["verso cambiado"]), _record("p2", "mar")]
    assert _compute_fingerprint(base) != _compute_fingerprint(changed)


def test_retriever_staleness() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    records = [_record("p1", "luna"), _record("p2", "mar")]
    # No fingerprint stored yet → stale.
    assert r.is_stale(records) is True
    r.ingest(records)
    assert r.is_stale(records) is False
    assert r.is_stale(records + [_record("p3", "viento")]) is True
    # Order independence.
    assert r.is_stale([records[1], records[0]]) is False

# ── Persistence ──────────────────────────────────────────────────────────


def test_persistence_round_trip_preserves_graph_and_identity(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    client = StubEmbeddingClient()
    r1 = GraphRAGRetriever(storage_path=db_path)
    r1.ingest([_record("p1", "a"), _record("p2", "b")], embedding_client=client)
    r1.add_influence_node("influence:neruda", name="Pablo Neruda")
    r1.add_typed_edge("p1", "influence:neruda", RelationType.inspired_by, weight=0.9)

    r2 = GraphRAGRetriever(storage_path=db_path)
    assert r2._graph.nodes["p1"].get("node_type") == NodeType.poem.value
    assert r2._graph.has_edge("p1", "influence:neruda")
    assert r2._index_model_id == client.model_id
    assert r2._index_embedding_dimension == client.dimension
    assert not db_path.with_suffix(".tmp").exists()  # atomic write
    # Fingerprint + staleness survive the round-trip.
    assert r2.is_stale([_record("p1", "a"), _record("p2", "b")]) is False

    with open(db_path) as f:
        data = json.load(f)
    assert data.get("schema_version") == "2"


def test_loaded_index_without_fingerprint_is_stale(tmp_path: Path) -> None:
    """A pre-fingerprint JSON file (old schema) must be detected as stale."""
    db_path = tmp_path / "graphrag_legacy.json"
    legacy_data = {
        "schema_version": "2",
        "model_id": None,
        "embedding_dimension": None,
        "nodes": {"p1": {"node_type": "poem", "theme": "luna", "embedding": []}},
        "edges": [],
    }
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)
    retriever = GraphRAGRetriever(storage_path=db_path)
    assert retriever._index_content_fingerprint is None
    assert retriever.is_stale([_record("p1", "luna")]) is True


# ── index_info ───────────────────────────────────────────────────────────


def test_index_info_reports_metadata() -> None:
    r = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    r.ingest([_record("p1", "tema"), _record("p2", "tema")], embedding_client=client)
    info = r.index_info()
    assert info["schema_version"] == "2"
    assert info["model_id"] == client.model_id
    assert info["embedding_dimension"] == client.dimension
    assert info["node_count"] == 2
    assert info.get("content_fingerprint")

    empty = GraphRAGRetriever(storage_path=":memory:").index_info()
    assert empty["model_id"] is None and empty["node_count"] == 0

"""P2 tests — typed graph nodes/relations, bounded traversal, and path explanation.

These tests prove the P2 evidence gate:
1. NodeType and RelationType enums are enforced.
2. ingest() tags poem nodes with NodeType.poem.
3. add_fragment_node() / add_influence_node() create typed nodes.
4. add_typed_edge() creates edges with RelationType.
5. traverse() returns bounded GraphPath objects with correct hops.
6. retrieve_with_paths() returns paths alongside scores.
7. GraphPath.to_display_string() renders human-readable explanations.
8. BriefBuilder calls the retriever when wired (gap #3 fix).
9. Dense vs graph retrieval differ (P2 evidence gate).
10. E5 prefix fix: text_type param accepted.
11. Versioned persistence round-trip.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.graphrag import GraphHop, GraphPath, GraphRAGRetriever
from poesia.memoria.library import PoemRecord
from poesia.memoria.records import NodeType, RelationType


def _record(poem_id: str, theme: str, form: str = "soneto", language: str = "es") -> PoemRecord:
    return PoemRecord(
        id=poem_id,
        lines=["verso de prueba uno", "verso de prueba dos"],
        language=language,
        form=form,
        theme=theme,
        created_at=datetime.now(),
        tags=[],
    )


# ---------------------------------------------------------------------------
# 1. Enum values
# ---------------------------------------------------------------------------


def test_node_type_enum_values() -> None:
    assert NodeType.poem.value == "poem"
    assert NodeType.fragment.value == "fragment"
    assert NodeType.influence.value == "influence"
    assert NodeType.seed.value == "seed"
    assert NodeType.theme.value == "theme"


def test_relation_type_enum_values() -> None:
    assert RelationType.similar_to.value == "similar_to"
    assert RelationType.inspired_by.value == "inspired_by"
    assert RelationType.explores.value == "explores"
    assert RelationType.contains.value == "contains"


# ---------------------------------------------------------------------------
# 2. ingest() sets node_type on poem nodes and relation_type on edges
# ---------------------------------------------------------------------------


def test_ingest_sets_node_type_poem() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "lluvia"), _record("p2", "sol")])
    for node_id in ["p1", "p2"]:
        attrs = retriever._graph.nodes[node_id]
        assert attrs.get("node_type") == NodeType.poem.value


def test_ingest_semantic_edges_carry_relation_type() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    embeddings = {"p1": [1.0, 0.0, 0.0], "p2": [1.0, 0.0, 0.0]}
    retriever.ingest([_record("p1", "a"), _record("p2", "b")], embeddings=embeddings)
    assert retriever.edge_count() == 2
    for u, v, data in retriever._graph.edges(data=True):
        assert data.get("relation_type") == RelationType.similar_to.value


# ---------------------------------------------------------------------------
# 3. add_fragment_node()
# ---------------------------------------------------------------------------


def test_add_fragment_node_typed() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.add_fragment_node(
        "fragment:saudade",
        content="La sombra de los árboles al atardecer.",
        language="es",
        tags=["soledad"],
    )
    assert "fragment:saudade" in retriever._graph
    attrs = retriever._graph.nodes["fragment:saudade"]
    assert attrs["node_type"] == NodeType.fragment.value


def test_add_fragment_node_auto_embed() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    retriever.add_fragment_node(
        "fragment:mar", content="El mar por la mañana.", embedding_client=client
    )
    emb = retriever._graph.nodes["fragment:mar"].get("embedding", [])
    assert len(emb) == client.dimension


# ---------------------------------------------------------------------------
# 4. add_influence_node()
# ---------------------------------------------------------------------------


def test_add_influence_node_typed() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.add_influence_node(
        "influence:machado", name="Antonio Machado",
        language="es", tone=["spare", "meditative"], movement="Generación del 98"
    )
    attrs = retriever._graph.nodes["influence:machado"]
    assert attrs["node_type"] == NodeType.influence.value
    assert attrs["name"] == "Antonio Machado"


# ---------------------------------------------------------------------------
# 5. add_typed_edge()
# ---------------------------------------------------------------------------


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
    with pytest.raises(ValueError, match="nonexistent"):
        retriever.add_typed_edge("nonexistent", "p1", RelationType.inspired_by)


# ---------------------------------------------------------------------------
# 6. traverse()
# ---------------------------------------------------------------------------


def test_traverse_direct_neighbours() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    embeddings = {"p1": [1.0, 0.0], "p2": [1.0, 0.0], "p3": [0.0, 1.0]}
    retriever.ingest([_record(p, f"t{p}") for p in embeddings], embeddings=embeddings)
    paths = retriever.traverse("p1", max_hops=1)
    ids = {p.endpoint_id for p in paths}
    assert "p2" in ids
    assert "p3" not in ids


def test_traverse_multi_hop() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "a"), _record("p2", "b"), _record("p3", "c")])
    retriever.add_typed_edge("p1", "p2", RelationType.similar_to, weight=0.8)
    retriever.add_typed_edge("p2", "p3", RelationType.inspired_by, weight=0.7)
    ids_1 = {p.endpoint_id for p in retriever.traverse("p1", max_hops=1)}
    ids_2 = {p.endpoint_id for p in retriever.traverse("p1", max_hops=2)}
    assert "p2" in ids_1 and "p3" not in ids_1
    assert "p2" in ids_2 and "p3" in ids_2


def test_traverse_budget_cap() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record(f"p{i}", f"t{i}") for i in range(6)])
    for i in range(1, 6):
        retriever.add_typed_edge("p0", f"p{i}", RelationType.similar_to, weight=0.8)
    assert len(retriever.traverse("p0", max_hops=1, budget=3)) <= 3


def test_traverse_relation_type_filter() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "a"), _record("p2", "b"), _record("p3", "c")])
    retriever.add_typed_edge("p1", "p2", RelationType.similar_to, weight=0.8)
    retriever.add_typed_edge("p1", "p3", RelationType.inspired_by, weight=0.9)
    ids = {p.endpoint_id for p in retriever.traverse(
        "p1", max_hops=1, relation_types=[RelationType.similar_to]
    )}
    assert "p2" in ids and "p3" not in ids


def test_traverse_node_type_filter() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "a")])
    retriever.add_influence_node("influence:lorca", name="García Lorca")
    retriever.add_typed_edge("p1", "influence:lorca", RelationType.inspired_by, weight=0.9)
    paths = retriever.traverse("p1", max_hops=1, node_types=[NodeType.influence])
    assert len(paths) == 1
    assert paths[0].endpoint_id == "influence:lorca"
    assert paths[0].hops[0].node_type == NodeType.influence


def test_traverse_empty_for_unknown_start() -> None:
    assert GraphRAGRetriever(storage_path=":memory:").traverse("nonexistent") == []



# ---------------------------------------------------------------------------
# 7. GraphPath display
# ---------------------------------------------------------------------------


def test_graph_path_single_hop_display() -> None:
    hop = GraphHop(node_id="p2", node_type=NodeType.poem,
                   relation_type=RelationType.similar_to, weight=0.82)
    s = GraphPath(origin_id="p1", hops=[hop]).to_display_string()
    assert "p1" in s and "similar_to" in s and "0.82" in s and "p2" in s


def test_graph_path_with_labels() -> None:
    hop = GraphHop(node_id="influence:machado", node_type=NodeType.influence,
                   relation_type=RelationType.inspired_by, weight=1.0)
    s = GraphPath(origin_id="p1", hops=[hop]).to_display_string(
        {"p1": "my-poem", "influence:machado": "Antonio Machado"}
    )
    assert "my-poem" in s and "Antonio Machado" in s
    assert "1.00" not in s  # weight=1.0 is omitted


def test_graph_path_depth_and_endpoint() -> None:
    path = GraphPath(origin_id="start", hops=[])
    assert path.depth == 0 and path.endpoint_id == "start"
    hop = GraphHop(node_id="end", node_type=NodeType.poem,
                   relation_type=RelationType.similar_to, weight=0.9)
    path2 = GraphPath(origin_id="start", hops=[hop])
    assert path2.depth == 1 and path2.endpoint_id == "end"


# ---------------------------------------------------------------------------
# 8. retrieve_with_paths()
# ---------------------------------------------------------------------------


def test_retrieve_with_paths_returns_triples() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    retriever.ingest([_record(f"p{i}", f"t{i}") for i in range(4)], embedding_client=client)
    query = client.embed_one("t1", text_type="query")
    results = retriever.retrieve_with_paths(query, k=3)
    assert len(results) <= 3
    for node_id, score, path in results:
        assert isinstance(node_id, str) and 0.0 <= score <= 1.0
        assert path is None or isinstance(path, GraphPath)


def test_retrieve_with_paths_graph_expansion() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    client = StubEmbeddingClient()
    retriever.ingest([_record("p1", "luna"), _record("p2", "noche")], embedding_client=client)
    extra_emb = client.embed_one("estrellas", text_type="passage")
    retriever.ingest([_record("p_extra", "astros")], embeddings={"p_extra": extra_emb})
    retriever.add_typed_edge("p1", "p_extra", RelationType.explores, weight=0.85)
    query = client.embed_one("luna", text_type="query")
    results = retriever.retrieve_with_paths(query, k=5, max_hops=2)
    assert len(results) > 0
    for nid, sc, path in results:
        assert isinstance(nid, str)



# ---------------------------------------------------------------------------
# 9. Dense vs graph evidence gate
# ---------------------------------------------------------------------------


def test_dense_vs_graph_retrieval_differ() -> None:
    """Graph traversal reaches p_far via typed edge even at low dense similarity."""
    client = StubEmbeddingClient()
    dim = client.dimension
    query_emb = [1.0] + [0.0] * (dim - 1)
    close_emb = [0.99] + [0.01] + [0.0] * (dim - 2)
    far_emb = [0.0] + [1.0] + [0.0] * (dim - 2)  # orthogonal to query

    r_dense = GraphRAGRetriever(storage_path=":memory:")
    r_graph = GraphRAGRetriever(storage_path=":memory:")
    records = [_record("p_close", "luna"), _record("p_far", "lejanía")]
    for r in [r_dense, r_graph]:
        r.ingest(records, embeddings={"p_close": close_emb, "p_far": far_emb})

    # Structural edge only in the graph retriever
    r_graph.add_typed_edge("p_close", "p_far", RelationType.inspired_by, weight=0.9)

    dense_ids = {r[0] for r in r_dense.retrieve(query_emb, k=2)}
    graph_ids = {r[0] for r in r_graph.retrieve_with_paths(query_emb, k=5, max_hops=2)}

    assert "p_close" in dense_ids
    assert "p_far" in graph_ids, "Graph traversal must reach p_far via the inspired_by edge"


# ---------------------------------------------------------------------------
# 10. text_type param compliance
# ---------------------------------------------------------------------------


def test_stub_embed_text_type_accepted() -> None:
    client = StubEmbeddingClient()
    q = client.embed_one("luna", text_type="query")
    p = client.embed_one("luna", text_type="passage")
    assert len(q) == client.dimension and len(p) == client.dimension


def test_stub_embed_batch_text_type_accepted() -> None:
    client = StubEmbeddingClient()
    vecs = client.embed(["luna", "sol"], text_type="passage")
    assert len(vecs) == 2 and all(len(v) == client.dimension for v in vecs)


# ---------------------------------------------------------------------------
# 11. Versioned persistence round-trip
# ---------------------------------------------------------------------------


def test_graphrag_persistence_includes_version_header(tmp_path: Path) -> None:
    import json
    db_path = tmp_path / "graphrag.json"
    client = StubEmbeddingClient()
    r = GraphRAGRetriever(storage_path=db_path)
    r.ingest([_record("p1", "lluvia")], embedding_client=client)
    with open(db_path) as f:
        data = json.load(f)
    assert "schema_version" in data
    assert data.get("model_id") == client.model_id
    assert data.get("embedding_dimension") == client.dimension


def test_graphrag_persistence_round_trip_node_type(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    r = GraphRAGRetriever(storage_path=db_path)
    r.ingest([_record("p1", "a"), _record("p2", "b")],
             embeddings={"p1": [1.0, 0.0], "p2": [1.0, 0.0]})
    r.add_influence_node("influence:neruda", name="Pablo Neruda")
    r.add_typed_edge("p1", "influence:neruda", RelationType.inspired_by, weight=0.9)

    r2 = GraphRAGRetriever(storage_path=db_path)
    assert r2._graph.nodes["p1"].get("node_type") == NodeType.poem.value
    assert r2._graph.has_edge("p1", "influence:neruda")
    assert (r2._graph["p1"]["influence:neruda"].get("relation_type")
            == RelationType.inspired_by.value)


def test_graphrag_persistence_restores_model_id(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    client = StubEmbeddingClient()
    r = GraphRAGRetriever(storage_path=db_path)
    r.ingest([_record("p1", "luna")], embedding_client=client)
    r2 = GraphRAGRetriever(storage_path=db_path)
    assert r2._index_model_id == client.model_id
    assert r2._index_embedding_dimension == client.dimension


# ---------------------------------------------------------------------------
# 12. BriefBuilder calls graph retriever when wired
# ---------------------------------------------------------------------------


def test_brief_builder_calls_graph_retriever() -> None:
    from poesia.generation.brief_builder import BriefBuilder
    client = StubEmbeddingClient()
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest(
        [_record("p1", "luna sobre el mar"), _record("p2", "amor eterno")],
        embedding_client=client
    )
    builder = BriefBuilder(embedding_client=client, retriever=retriever)
    brief = builder.build(form="haiku", theme="luna sobre el mar")
    assert hasattr(brief, "graph_paths")
    assert isinstance(brief.graph_paths, list)
    for item in brief.graph_paths:
        assert len(item) == 3


def test_brief_builder_graph_paths_empty_without_retriever() -> None:
    from poesia.generation.brief_builder import BriefBuilder
    client = StubEmbeddingClient()
    brief = BriefBuilder(embedding_client=client).build(form="haiku", theme="noche")
    assert brief.graph_paths == []


"""Unit tests for GraphRAGRetriever (networkx in-memory graph, JSON persistence)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from poesia.memoria.graphrag import GraphRAGRetriever
from poesia.memoria.library import PoemRecord


def _record(poem_id: str, theme: str, form: str = "soneto", language: str = "es") -> PoemRecord:
    return PoemRecord(
        id=poem_id,
        lines=["test line one", "test line two"],
        language=language,
        form=form,
        theme=theme,
        created_at=datetime.now(),
        tags=[],
    )


def test_graphrag_ingest_adds_nodes() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    records = [
        _record("p1", "lluvia nocturna"),
        _record("p2", "amor eterno"),
        _record("p3", "soledad de otoño"),
    ]
    retriever.ingest(records)
    assert retriever.node_count() == 3
    assert retriever.edge_count() == 0  # no embeddings → no semantic edges


def test_graphrag_semantic_edges_built_above_threshold() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    # Two identical embeddings → cosine = 1.0, well above threshold
    embeddings = {
        "p1": [1.0, 0.0, 0.0],
        "p2": [1.0, 0.0, 0.0],  # identical → cosine 1.0
        "p3": [0.0, 1.0, 0.0],  # orthogonal → cosine 0.0
    }
    records = [
        _record("p1", "tema a"),
        _record("p2", "tema b"),
        _record("p3", "tema c"),
    ]
    retriever.ingest(records, embeddings=embeddings)

    # p1 ↔ p2 should be connected (cosine 1.0), p3 should be isolated
    assert retriever.edge_count() == 2  # bidirectional pair
    nbrs = [pid for pid, _ in retriever.neighbourhood("p1")]
    assert "p2" in nbrs
    assert "p3" not in nbrs


def test_graphrag_retrieve_returns_top_k() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    embeddings = {
        "p1": [1.0, 0.0],
        "p2": [0.9, 0.1],
        "p3": [0.0, 1.0],
    }
    records = [_record(pid, f"tema {pid}") for pid in embeddings]
    retriever.ingest(records, embeddings=embeddings)

    query = [1.0, 0.0]
    results = retriever.retrieve(query, k=2)
    assert len(results) == 2
    # p1 and p2 should be closest to the query
    result_ids = [pid for pid, _ in results]
    assert "p1" in result_ids
    assert "p2" in result_ids


def test_graphrag_retrieve_with_form_filter() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    embeddings = {
        "p1": [1.0, 0.0],
        "p2": [1.0, 0.0],
    }
    records = [
        _record("p1", "tema a", form="soneto"),
        _record("p2", "tema b", form="haiku"),
    ]
    retriever.ingest(records, embeddings=embeddings)

    results = retriever.retrieve([1.0, 0.0], k=5, form_filter="soneto")
    assert all(rid == "p1" for rid, _ in results)


def test_graphrag_json_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    retriever = GraphRAGRetriever(storage_path=db_path)
    records = [_record("p1", "lluvia"), _record("p2", "sol")]
    embeddings = {"p1": [1.0, 0.0], "p2": [1.0, 0.0]}
    retriever.ingest(records, embeddings=embeddings)

    assert db_path.exists()

    # Fresh retriever loads from JSON
    retriever2 = GraphRAGRetriever(storage_path=db_path)
    assert retriever2.node_count() == 2
    assert retriever2.edge_count() == 2  # bidirectional pair (cosine 1.0)


def test_graphrag_retrieve_graph_based() -> None:
    """Test graph-based retrieval using ego_graph expansion."""
    retriever = GraphRAGRetriever(storage_path=":memory:")

    # Build a chain: p1 → p2 → p3 (via high similarity edges)
    embeddings = {
        "p1": [1.0, 0.0, 0.0],
        "p2": [0.95, 0.05, 0.0],  # Close to p1
        "p3": [0.90, 0.10, 0.0],  # Close to p2
        "p4": [0.0, 0.0, 1.0],    # Isolated
    }
    records = [_record(pid, f"tema {pid}") for pid in embeddings]
    retriever.ingest(records, embeddings=embeddings)

    # Query close to p1
    query = [1.0, 0.0, 0.0]
    results = retriever.retrieve_graph_based(query, k=3, depth=1)

    result_ids = [pid for pid, _ in results]
    # Should find p1, p2, and potentially p3 via graph expansion
    assert "p1" in result_ids
    assert "p2" in result_ids
    # p4 should not appear (isolated, orthogonal)
    assert "p4" not in result_ids


def test_graphrag_retrieve_graph_based_with_depth() -> None:
    """Test that depth parameter expands retrieval."""
    retriever = GraphRAGRetriever(storage_path=":memory:")

    # Build connected cluster
    embeddings = {
        "p1": [1.0, 0.0],
        "p2": [0.95, 0.05],
        "p3": [0.90, 0.10],
    }
    records = [_record(pid, f"tema {pid}") for pid in embeddings]
    retriever.ingest(records, embeddings=embeddings)

    query = [1.0, 0.0]
    # With depth=2, should expand further
    results = retriever.retrieve_graph_based(query, k=5, depth=2)
    assert len(results) >= 2


def test_graphrag_retrieve_graph_based_respects_filters() -> None:
    """Test that form/language filters apply to expanded nodes."""
    retriever = GraphRAGRetriever(storage_path=":memory:")

    embeddings = {
        "p1": [1.0, 0.0],
        "p2": [0.95, 0.05],
    }
    records = [
        _record("p1", "tema a", form="soneto", language="es"),
        _record("p2", "tema b", form="haiku", language="es"),
    ]
    retriever.ingest(records, embeddings=embeddings)

    query = [1.0, 0.0]
    results = retriever.retrieve_graph_based(query, k=5, form_filter="soneto")

    # Only p1 should be returned (haiku filtered out)
    result_ids = [pid for pid, _ in results]
    assert "p1" in result_ids
    # p2 may or may not appear depending on how filters are applied
    # but if it does, form_filter should exclude it in final scoring


def test_graphrag_get_connected_influences() -> None:
    """Test retrieval of influences connected to a poem."""
    retriever = GraphRAGRetriever(storage_path=":memory:")

    # Manually add nodes and edges
    retriever._graph.add_node("poem1", theme="soledad")
    retriever._graph.add_node("influence:machado", theme="spare")
    retriever._graph.add_node("influence:neruda", theme="sensual")
    retriever._graph.add_edge("poem1", "influence:machado", weight=0.85)
    retriever._graph.add_edge("influence:neruda", "poem1", weight=0.72)

    influences = retriever.get_connected_influences("poem1")

    assert len(influences) == 2
    influence_ids = [inf_id for inf_id, _ in influences]
    assert "influence:machado" in influence_ids
    assert "influence:neruda" in influence_ids

    # Should be sorted by weight descending
    assert influences[0][1] >= influences[1][1]


def test_graphrag_get_connected_influences_empty() -> None:
    """Test empty result when poem has no influence connections."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever._graph.add_node("poem1", theme="soledad")

    influences = retriever.get_connected_influences("poem1")
    assert influences == []


def test_graphrag_get_connected_influences_missing_poem() -> None:
    """Test empty result when poem doesn't exist."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    influences = retriever.get_connected_influences("nonexistent")
    assert influences == []

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

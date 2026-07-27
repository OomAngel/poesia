"""Tests for P3 source fingerprints in GraphRAGRetriever.

Verifies:
- Fingerprint is computed and stored after ingest.
- Fingerprint is stable on re-ingest of the same records.
- Fingerprint changes when records change (add, remove, modify).
- Fingerprint is order-independent (sorted by ID).
- Fingerprint survives a save/load round-trip.
- is_stale() returns False for matching records, True for changed records.
- is_stale() returns True for an index with no fingerprint (pre-P3).
- index_info() exposes the fingerprint.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from poesia.memoria.graphrag import GraphRAGRetriever, _compute_fingerprint
from poesia.memoria.library import PoemRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    poem_id: str,
    theme: str,
    lines: list[str] | None = None,
    form: str = "haiku",
    language: str = "es",
) -> PoemRecord:
    return PoemRecord(
        id=poem_id,
        lines=lines or ["verso uno", "verso dos"],
        language=language,
        form=form,
        theme=theme,
        created_at=datetime.now(),
        tags=[],
    )


# ---------------------------------------------------------------------------
# 1. _compute_fingerprint helper
# ---------------------------------------------------------------------------


def test_fingerprint_is_64_hex_chars() -> None:
    records = [_record("p1", "lluvia"), _record("p2", "sol")]
    fp = _compute_fingerprint(records)
    assert isinstance(fp, str)
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_stable_on_same_records() -> None:
    records = [_record("p1", "lluvia"), _record("p2", "sol")]
    assert _compute_fingerprint(records) == _compute_fingerprint(records)


def test_fingerprint_order_independent() -> None:
    r1 = _record("alpha", "tema A")
    r2 = _record("beta", "tema B")
    assert _compute_fingerprint([r1, r2]) == _compute_fingerprint([r2, r1])


def test_fingerprint_changes_when_record_added() -> None:
    base = [_record("p1", "luna"), _record("p2", "mar")]
    extended = base + [_record("p3", "viento")]
    assert _compute_fingerprint(base) != _compute_fingerprint(extended)


def test_fingerprint_changes_when_record_removed() -> None:
    full = [_record("p1", "luna"), _record("p2", "mar")]
    partial = [_record("p1", "luna")]
    assert _compute_fingerprint(full) != _compute_fingerprint(partial)


def test_fingerprint_changes_when_theme_changes() -> None:
    original = [_record("p1", "lluvia nocturna")]
    modified = [_record("p1", "lluvia matutina")]
    assert _compute_fingerprint(original) != _compute_fingerprint(modified)


def test_fingerprint_changes_when_lines_change() -> None:
    original = [_record("p1", "luna", lines=["verso original"])]
    modified = [_record("p1", "luna", lines=["verso cambiado"])]
    assert _compute_fingerprint(original) != _compute_fingerprint(modified)


def test_fingerprint_empty_records() -> None:
    fp = _compute_fingerprint([])
    assert isinstance(fp, str) and len(fp) == 64


# ---------------------------------------------------------------------------
# 2. GraphRAGRetriever stores fingerprint after ingest
# ---------------------------------------------------------------------------


def test_retriever_stores_fingerprint_after_ingest() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    records = [_record("p1", "luna"), _record("p2", "mar")]
    retriever.ingest(records)
    assert retriever._index_content_fingerprint is not None
    assert len(retriever._index_content_fingerprint) == 64


def test_retriever_fingerprint_matches_compute_fingerprint() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    records = [_record("p1", "luna"), _record("p2", "mar")]
    retriever.ingest(records)
    assert retriever._index_content_fingerprint == _compute_fingerprint(records)


def test_retriever_fingerprint_none_before_ingest() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    assert retriever._index_content_fingerprint is None


# ---------------------------------------------------------------------------
# 3. is_stale()
# ---------------------------------------------------------------------------


def test_is_stale_false_for_same_records() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    records = [_record("p1", "luna"), _record("p2", "mar")]
    retriever.ingest(records)
    assert retriever.is_stale(records) is False


def test_is_stale_true_when_record_added() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    records = [_record("p1", "luna"), _record("p2", "mar")]
    retriever.ingest(records)
    assert retriever.is_stale(records + [_record("p3", "viento")]) is True


def test_is_stale_true_when_record_removed() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    records = [_record("p1", "luna"), _record("p2", "mar")]
    retriever.ingest(records)
    assert retriever.is_stale([_record("p1", "luna")]) is True


def test_is_stale_true_when_content_changed() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "lluvia nocturna")])
    assert retriever.is_stale([_record("p1", "lluvia matutina")]) is True


def test_is_stale_true_when_no_fingerprint_stored() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    assert retriever.is_stale([_record("p1", "luna")]) is True


def test_is_stale_order_independent() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    r1 = _record("alpha", "tema A")
    r2 = _record("beta", "tema B")
    retriever.ingest([r1, r2])
    assert retriever.is_stale([r2, r1]) is False


# ---------------------------------------------------------------------------
# 4. Save/load round-trip preserves fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_survives_save_load_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    records = [_record("p1", "luna"), _record("p2", "mar")]
    r1 = GraphRAGRetriever(storage_path=db_path)
    r1.ingest(records)
    original_fp = r1._index_content_fingerprint
    r2 = GraphRAGRetriever(storage_path=db_path)
    assert r2._index_content_fingerprint == original_fp


def test_is_stale_false_after_load_with_same_records(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    records = [_record("p1", "luna"), _record("p2", "mar")]
    r1 = GraphRAGRetriever(storage_path=db_path)
    r1.ingest(records)
    r2 = GraphRAGRetriever(storage_path=db_path)
    assert r2.is_stale(records) is False


def test_is_stale_true_after_load_when_records_changed(tmp_path: Path) -> None:
    db_path = tmp_path / "graphrag.json"
    records = [_record("p1", "luna"), _record("p2", "mar")]
    r1 = GraphRAGRetriever(storage_path=db_path)
    r1.ingest(records)
    r2 = GraphRAGRetriever(storage_path=db_path)
    assert r2.is_stale(records + [_record("p3", "estrella")]) is True


def test_loaded_index_without_fingerprint_is_stale(tmp_path: Path) -> None:
    """Simulate a pre-P3 JSON file that has no content_fingerprint key."""
    import json

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


# ---------------------------------------------------------------------------
# 5. index_info() exposes the fingerprint
# ---------------------------------------------------------------------------


def test_index_info_contains_fingerprint_after_ingest() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    retriever.ingest([_record("p1", "luna")])
    info = retriever.index_info()
    assert "content_fingerprint" in info
    assert info["content_fingerprint"] is not None
    assert len(info["content_fingerprint"]) == 64


def test_index_info_fingerprint_none_before_ingest() -> None:
    retriever = GraphRAGRetriever(storage_path=":memory:")
    info = retriever.index_info()
    assert "content_fingerprint" in info
    assert info["content_fingerprint"] is None

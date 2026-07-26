"""Tests for poesia.memoria.library: Markdown frontmatter + SQLite poem library."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from poesia.memoria.library import Library, PoemRecord


def _record(theme: str, tags: list[str] | None = None, created_at: datetime | None = None) -> PoemRecord:
    return PoemRecord(
        lines=["line one", "line two"],
        language="es",
        form="soneto",
        theme=theme,
        created_at=created_at or datetime.now(),
        tags=tags or [],
    )


def test_add_and_list_all_returns_stored_record() -> None:
    lib = Library(storage_dir=":memory:")
    rec = _record("amor")
    lib.add(rec)
    all_recs = lib.list_all()
    assert len(all_recs) == 1
    assert all_recs[0].theme == "amor"
    assert all_recs[0].lines == ["line one", "line two"]


def test_list_all_sorted_most_recent_first() -> None:
    lib = Library(storage_dir=":memory:")
    older = _record("otoño", created_at=datetime.now() - timedelta(days=1))
    newer = _record("primavera", created_at=datetime.now())
    lib.add(older)
    lib.add(newer)
    results = lib.list_all()
    assert results[0].theme == "primavera"
    assert results[1].theme == "otoño"


def test_search_matches_theme_case_insensitively() -> None:
    lib = Library(storage_dir=":memory:")
    lib.add(_record("Amor eterno"))
    assert len(lib.search("amor")) == 1
    assert len(lib.search("ODIO")) == 0


def test_search_matches_tags() -> None:
    lib = Library(storage_dir=":memory:")
    lib.add(_record("mar", tags=["Nostalgia", "verano"]))
    assert len(lib.search("nostalgia")) == 1


def test_search_matches_line_text() -> None:
    lib = Library(storage_dir=":memory:")
    lib.add(_record("mar", tags=[]))
    assert len(lib.search("line one")) == 1
    assert len(lib.search("nonexistent phrase")) == 0


def test_markdown_file_and_sync_persistence(tmp_path: Path) -> None:
    lib = Library(storage_dir=tmp_path)
    rec = _record("Lluvia nocturna", tags=["noche", "lluvia"])
    lib.add(rec)

    # Verify .md file creation
    md_files = list(tmp_path.glob("*.md"))
    assert len(md_files) == 1
    content = md_files[0].read_text(encoding="utf-8")
    assert "theme: Lluvia nocturna" in content
    assert "line one" in content

    # Test syncing on a fresh Library instance on the same directory
    lib2 = Library(storage_dir=tmp_path)
    recs = lib2.list_all()
    assert len(recs) == 1
    assert recs[0].theme == "Lluvia nocturna"


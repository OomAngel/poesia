"""Tests for poesia.memoria.library: the Phase 0/1 in-memory poem library."""

from __future__ import annotations

from datetime import datetime, timedelta

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
    lib = Library()
    rec = _record("amor")
    lib.add(rec)
    assert lib.list_all() == [rec]


def test_list_all_sorted_most_recent_first() -> None:
    lib = Library()
    older = _record("otoño", created_at=datetime.now() - timedelta(days=1))
    newer = _record("primavera", created_at=datetime.now())
    lib.add(older)
    lib.add(newer)
    results = lib.list_all()
    assert results[0] is newer
    assert results[1] is older


def test_search_matches_theme_case_insensitively() -> None:
    lib = Library()
    lib.add(_record("Amor eterno"))
    assert len(lib.search("amor")) == 1
    assert len(lib.search("ODIO")) == 0


def test_search_matches_tags() -> None:
    lib = Library()
    lib.add(_record("mar", tags=["Nostalgia", "verano"]))
    assert len(lib.search("nostalgia")) == 1


def test_search_matches_line_text() -> None:
    lib = Library()
    lib.add(_record("mar", tags=[]))
    assert len(lib.search("line one")) == 1
    assert len(lib.search("nonexistent phrase")) == 0


def test_poem_record_defaults() -> None:
    rec = PoemRecord(lines=["a"], language="en", form="haiku", theme="silence")
    assert rec.tags == []
    assert isinstance(rec.created_at, datetime)

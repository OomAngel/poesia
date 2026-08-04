"""Tests for poesia.memoria.library: Markdown frontmatter + SQLite poem library."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from poesia.memoria.library import Library, PoemProvenance, PoemRecord


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


def test_provenance_persisted_to_markdown(tmp_path: Path) -> None:
    """P1: Provenance metadata should be written to markdown frontmatter."""
    lib = Library(storage_dir=tmp_path)

    provenance = PoemProvenance(
        model="gemini-1.5-flash",
        embedding_model="multilingual-e5-base",
        brief_level="standard",
        seeds=["luna", "noche"],
        tone=["melancholic", "intimate"],
        fragments_used=["frag_001", "frag_002"],
        influences_used=["neruda", "lorca"],
    )

    rec = PoemRecord(
        lines=["La luna brilla", "sobre la noche oscura"],
        language="es",
        form="copla",
        theme="noche de luna",
        tags=["luna"],
        provenance=provenance,
    )
    lib.add(rec)

    # Verify provenance fields in markdown
    md_files = list(tmp_path.glob("*.md"))
    assert len(md_files) == 1
    content = md_files[0].read_text(encoding="utf-8")

    assert "model: gemini-1.5-flash" in content
    assert "embedding_model: multilingual-e5-base" in content
    assert "brief_level: standard" in content
    assert "seeds: [luna, noche]" in content
    assert "tone: [melancholic, intimate]" in content
    assert "fragments_used: [frag_001, frag_002]" in content
    assert "influences_used: [neruda, lorca]" in content


def test_provenance_optional_fields_omitted(tmp_path: Path) -> None:
    """P1: Empty provenance fields should not appear in markdown."""
    lib = Library(storage_dir=tmp_path)

    # Provenance with only model set
    provenance = PoemProvenance(model="stub")

    rec = PoemRecord(
        lines=["Test line"],
        language="es",
        form="haiku",
        theme="test",
        provenance=provenance,
    )
    lib.add(rec)

    md_files = list(tmp_path.glob("*.md"))
    content = md_files[0].read_text(encoding="utf-8")

    assert "model: stub" in content
    # These should NOT appear since they're empty/None
    assert "embedding_model:" not in content
    assert "seeds: []" not in content
    assert "tone: []" not in content


def test_record_without_provenance_still_works(tmp_path: Path) -> None:
    """P1: Records without provenance should work as before."""
    lib = Library(storage_dir=tmp_path)

    rec = PoemRecord(
        lines=["Simple line"],
        language="es",
        form="verso",
        theme="simple",
        # No provenance
    )
    lib.add(rec)

    md_files = list(tmp_path.glob("*.md"))
    content = md_files[0].read_text(encoding="utf-8")

    # Should have basic fields
    assert "theme: simple" in content
    assert "Simple line" in content
    # Should not have provenance fields
    assert "model:" not in content


def test_get_returns_record_with_lines_and_content(tmp_path: Path) -> None:
    """Library.get() must return a fully-populated PoemRecord (content mirror)."""
    lib = Library(storage_dir=tmp_path)
    rec = _record("luna nocturna")
    lib.add(rec)
    assert rec.id is not None

    fetched = lib.get(rec.id)
    assert fetched is not None
    assert fetched.id == rec.id
    assert fetched.lines == ["line one", "line two"]
    assert "line one" in fetched.content
    # Round-trip: the CLI reads poem.content.split("\\n") to recover the lines.
    assert fetched.content.split("\n") == fetched.lines


def test_attach_image_adds_frontmatter_field(tmp_path: Path) -> None:
    lib = Library(storage_dir=tmp_path)
    rec = _record("luna nocturna")
    lib.add(rec)
    assert rec.id is not None

    lib.attach_image(rec.id, "illustrations/luna_nocturna.png")

    md_files = list(tmp_path.glob("*.md"))
    content = md_files[0].read_text(encoding="utf-8")
    assert "image: illustrations/luna_nocturna.png" in content


def test_attach_image_replaces_existing_field(tmp_path: Path) -> None:
    lib = Library(storage_dir=tmp_path)
    rec = _record("luna nocturna")
    lib.add(rec)
    assert rec.id is not None

    lib.attach_image(rec.id, "illustrations/v1.png")
    lib.attach_image(rec.id, "illustrations/v2.png")

    content = (tmp_path / f"{rec.id}.md").read_text(encoding="utf-8")
    assert content.count("image:") == 1
    assert "image: illustrations/v2.png" in content


def test_attach_image_unknown_poem_raises(tmp_path: Path) -> None:
    lib = Library(storage_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        lib.attach_image("no_such_poem", "illustrations/x.png")


def test_title_round_trips_markdown_and_sqlite(tmp_path: Path) -> None:
    """A record's title is written to frontmatter and restored everywhere."""
    lib = Library(storage_dir=tmp_path)
    rec = _record("cosecha de esperanza", tags=["quinoa"])
    rec.title = "A Harvest Hope"
    lib.add(rec)

    content = (tmp_path / f"{rec.id}.md").read_text(encoding="utf-8")
    assert "title: A Harvest Hope" in content

    # A fresh Library instance (re-sync from Markdown) must restore the title.
    lib2 = Library(storage_dir=tmp_path)
    fetched = lib2.get(rec.id)
    assert fetched is not None
    assert fetched.title == "A Harvest Hope"

    # list_all and search carry the title too.
    assert lib2.list_all()[0].title == "A Harvest Hope"
    assert lib2.search("cosecha")[0].title == "A Harvest Hope"


def test_title_omitted_from_frontmatter_when_empty(tmp_path: Path) -> None:
    """Records without a title keep clean, backward-compatible frontmatter."""
    lib = Library(storage_dir=tmp_path)
    lib.add(_record("luna"))
    rec = lib.list_all()[0]
    assert rec.id is not None
    content = (tmp_path / f"{rec.id}.md").read_text(encoding="utf-8")
    assert "title:" not in content


def test_existing_database_is_migrated_with_title_column(tmp_path: Path) -> None:
    """Pre-existing library.db (old schema) is upgraded without data loss."""
    import sqlite3

    db_path = tmp_path / "library.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE poems (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            language TEXT NOT NULL,
            form TEXT NOT NULL,
            theme TEXT NOT NULL,
            created_at TEXT NOT NULL,
            tags TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO poems (id, filename, language, form, theme, created_at, tags, content)
        VALUES ('old_1', 'old_1.md', 'es', 'soneto', 'luna antigua',
                '2026-01-01T00:00:00', '', 'verso viejo')
        """
    )
    conn.commit()
    conn.close()

    lib = Library(storage_dir=tmp_path)
    # Existing record survives; old rows default to an empty title.
    old = lib.get("old_1")
    assert old is not None
    assert old.title == ""

    # New records can store a title in the migrated database.
    rec = _record("luna nueva")
    rec.title = "Luna Nueva"
    lib.add(rec)
    assert rec.id is not None
    assert lib.get(rec.id) is not None
    assert lib.get(rec.id).title == "Luna Nueva"  # type: ignore[union-attr]


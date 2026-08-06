"""P1 Integration test: Complete end-to-end RAG generation journey.

Tests the full pipeline from RAG_LLM_ENGINEERING_HARDENING_PLAN.md P1.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from poesia.cli import app
from poesia.memoria.library import Library, PoemProvenance, PoemRecord


@pytest.fixture
def temp_home(tmp_path: Path) -> Path:
    """Create a temporary home directory with library structure."""
    poems_dir = tmp_path / ".poesia" / "poems"
    poems_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestP1EndToEndJourney:
    """Integration tests for P1 end-to-end RAG journey."""

    def test_write_generates_poem(self, runner: CliRunner) -> None:
        """Basic write command should generate a poem."""
        result = runner.invoke(app, ["write", "--theme", "luna", "--form", "haiku"])
        assert result.exit_code == 0
        assert "Theme: luna" in result.output

    def test_write_with_save_creates_file(
        self, runner: CliRunner, temp_home: Path
    ) -> None:
        """Write with --save should persist poem to library."""
        old_home = os.environ.get("HOME")
        try:
            os.environ["HOME"] = str(temp_home)
            result = runner.invoke(app, [
                "write", "--theme", "luna", "--form", "haiku", "--save"
            ])
            assert result.exit_code == 0
            assert "Saved to library" in result.output

            md_files = list((temp_home / ".poesia" / "poems").glob("*.md"))
            assert len(md_files) == 1
        finally:
            if old_home:
                os.environ["HOME"] = old_home

    def test_write_with_use_library_loads_poems(
        self, runner: CliRunner, temp_home: Path
    ) -> None:
        """--use-library should load existing poems for context."""
        old_home = os.environ.get("HOME")
        try:
            os.environ["HOME"] = str(temp_home)

            # Pre-populate library
            library = Library()
            library.add(PoemRecord(
                lines=["Luna de plata"], language="es", form="haiku", theme="luna"
            ))

            # Test without --brief to avoid slow embedding load
            result = runner.invoke(app, [
                "write", "--theme", "noche", "--form", "haiku",
                "--use-library"
            ])
            assert result.exit_code == 0
            assert "Loaded 1 poems from library" in result.output
        finally:
            if old_home:
                os.environ["HOME"] = old_home


class TestLibraryProvenance:
    """Provenance is written to markdown frontmatter."""

    def test_provenance_saved_to_markdown(self, tmp_path: Path) -> None:
        """Provenance should be written to markdown frontmatter."""
        library = Library(storage_dir=tmp_path)
        record = PoemRecord(
            lines=["test"], language="es", form="haiku", theme="test",
            provenance=PoemProvenance(model="gemini", seeds=["luna"])
        )
        library.add(record)

        content = list(tmp_path.glob("*.md"))[0].read_text()
        assert "model: gemini" in content
        assert "seeds: [luna]" in content

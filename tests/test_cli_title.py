"""Test the write CLI's --no-title flag (auto title suggestion opt-out)."""

from __future__ import annotations

from typer.testing import CliRunner

from poesia.cli import app


def test_no_title_flag_is_accepted() -> None:
    """--no-title parses cleanly and stub runs never suggest a title."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["write", "--theme", "luna", "--form", "haiku", "--no-title", "--yes"],
    )
    assert result.exit_code == 0
    assert "Suggested title" not in result.output
    assert "luna" in result.output.lower()

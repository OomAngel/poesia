"""Test CLI --show-alternatives flag."""

from __future__ import annotations

from typer.testing import CliRunner

from poesia.cli import app


def test_write_without_alternatives_shows_only_poem():
    """Default behavior: show only the final poem."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "write",
            "--theme",
            "luna",
            "--form",
            "haiku",
            "--llm",
            "stub",
        ],
    )

    assert result.exit_code == 0
    assert "luna" in result.output.lower()
    # Should NOT show alternatives section
    assert "Other lines to consider" not in result.output
    assert "syllables=" not in result.output


def test_write_with_alternatives_shows_candidates():
    """With --show-alternatives, display candidates in plain language."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "write",
            "--theme",
            "luna",
            "--form",
            "haiku",
            "--show-alternatives",
            "3",
            "--llm",
            "stub",
        ],
    )

    assert result.exit_code == 0

    # Should show alternatives section
    assert "Other lines to consider" in result.output

    # Should show line numbers and targets in plain language
    assert "Line 1" in result.output
    assert "syllables" in result.output
    assert "on the nose" in result.output

    # Should NOT show raw score internals
    assert "metre=" not in result.output
    assert "theme=" not in result.output
    assert "novelty=" not in result.output

    # Should show kept marker
    assert "✓" in result.output


def test_alternatives_shows_correct_line_count():
    """Alternatives section should match the number of lines generated."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "write",
            "--theme",
            "noche",
            "--form",
            "haiku",  # 3 lines
            "--show-alternatives",
            "2",
            "--llm",
            "stub",
        ],
    )

    assert result.exit_code == 0

    # Should show 3 line sections (haiku has 3 lines)
    assert "Line 1" in result.output
    assert "Line 2" in result.output
    assert "Line 3" in result.output
    # Should not have Line 4
    assert "Line 4" not in result.output


def test_verbose_flag_reveals_internal_details():
    """Internal diagnostics (LLM backend, scoring mode) are hidden unless --verbose."""
    runner = CliRunner()
    default = runner.invoke(app, ["write", "--theme", "luna", "--form", "haiku", "--llm", "stub"])
    verbose = runner.invoke(
        app, ["write", "--theme", "luna", "--form", "haiku", "--verbose", "--llm", "stub"]
    )

    assert default.exit_code == 0
    assert "Using LLM:" not in default.output
    assert "Scoring mode:" not in default.output
    assert "Scaffolding" in default.output or "proposals" in default.output

    assert verbose.exit_code == 0
    assert "Using LLM:" in verbose.output
    assert "Scoring mode:" in verbose.output


def test_write_output_frames_draft_as_scaffolding():
    """The draft is framed as proposals, never as the poem itself."""
    runner = CliRunner()
    result = runner.invoke(app, ["write", "--theme", "luna", "--form", "haiku", "--llm", "stub"])
    assert result.exit_code == 0
    assert "proposals" in result.output.lower()
    assert "scaffolding" in result.output.lower()


def test_alternatives_respects_limit():
    """Should show only N alternatives per line."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "write",
            "--theme",
            "sol",
            "--form",
            "haiku",
            "--show-alternatives",
            "2",  # Only top 2
            "--llm",
            "stub",
        ],
    )

    assert result.exit_code == 0

    # Each line section should have entries 1 and 2
    output_lines = result.output.split("\n")

    # Count ranking markers in Line 1 section
    line1_section = []
    in_line1 = False
    for line in output_lines:
        if "Line 1" in line:
            in_line1 = True
        elif "Line 2" in line:
            in_line1 = False
        elif in_line1 and line.strip().startswith(("1.", "2.", "3.")):
            line1_section.append(line)

    # Should have exactly 2 candidates (1. and 2.), not 3.
    assert len(line1_section) == 2
    assert any("1." in line for line in line1_section)
    assert any("2." in line for line in line1_section)

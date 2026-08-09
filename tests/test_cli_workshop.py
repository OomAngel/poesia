"""Tests for the workshop flow (poesia workshop).

The workshop walks the four movements (outlet → shaping → teaching →
linking) from docs/POSITIONING.md. These tests drive it through CliRunner
with injected stdin: Enter = top candidate for each line.
"""

from __future__ import annotations

from typer.testing import CliRunner

from poesia.cli import app


def test_workshop_outlet_prompt_and_poem(tmp_path) -> None:  # noqa: ANN001
    """Outlet prompt feeds the theme; a haiku is shaped and taught."""
    runner = CliRunner()
    # 3 haiku lines → 3 Enter presses choose the top candidate.
    result = runner.invoke(
        app,
        ["workshop", "--form", "haiku", "--outlet", "lo que no pude decir"],
        input="\n\n\n",
    )
    assert result.exit_code == 0
    assert "Carrying:" in result.output
    assert "lo que no pude decir" in result.output
    assert "1 · Outlet" in result.output
    assert "2 · Shaping" in result.output
    assert "3 · Teaching" in result.output
    assert "Your poem, as shaped" in result.output
    # Every line should have been scanned against its haiku target (5-7-5).
    assert (
        "Exact match" in result.output or "Short by" in result.output or "Over by" in result.output
    )


def test_workshop_empty_outlet_exits_cleanly() -> None:
    """An empty outlet has nothing to shape — exits non-zero with a message."""
    runner = CliRunner()
    result = runner.invoke(app, ["workshop", "--outlet", "   "])
    assert result.exit_code == 1
    assert "empty outlet" in result.output


def test_workshop_save_stores_poem_with_reflection(tmp_path) -> None:  # noqa: ANN001
    """--save stores the poem with the outlet kept as its reflection."""
    from unittest.mock import patch

    from poesia.memoria.library import PoemRecord

    captured: list[PoemRecord] = []

    class FakeLibrary:
        def __init__(self) -> None:
            pass

        def add(self, record: PoemRecord) -> None:
            captured.append(record)

        def attach_image(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

    runner = CliRunner()
    with patch("poesia.memoria.library.Library", FakeLibrary):
        result = runner.invoke(
            app,
            ["workshop", "--form", "haiku", "--save", "--no-title", "--outlet", "miedo al lunes"],
            input="\n\n\n",
        )
    assert result.exit_code == 0
    assert "Kept in memoria" in result.output
    assert "4 · Linking" in result.output
    assert captured
    assert captured[0].reflection == "miedo al lunes"
    assert captured[0].theme == "miedo al lunes"


def test_workshop_empty_outlet_prompt_interrupted() -> None:
    """Ctrl-D at the outlet prompt closes the workshop gracefully (exit 0)."""
    runner = CliRunner()
    result = runner.invoke(app, ["workshop", "--form", "haiku"], input="")
    assert result.exit_code == 0
    assert "Nothing carried today" in result.output

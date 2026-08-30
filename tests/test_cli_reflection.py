"""Test the write CLI's reflection option (memoria provenance, POSITIONING §7.4)."""

from __future__ import annotations

from typer.testing import CliRunner

from poesia.cli import app


def test_reflection_flag_is_stored_on_save() -> None:
    """--reflection reaches the PoemRecord saved to the library."""
    from unittest.mock import patch

    from poesia.memoria.library import PoemRecord

    captured: list[PoemRecord] = []

    class FakeLibrary:
        def add(self, record: PoemRecord) -> None:
            captured.append(record)

        def attach_image(self, *args, **kwargs) -> None:  # noqa: ARG002
            return None

    runner = CliRunner()
    with patch("poesia.memoria.library.Library", FakeLibrary):
        result = runner.invoke(
            app,
            [
                "write",
                "--theme",
                "luna",
                "--form",
                "haiku",
                "--yes",
                "--save",
                "--reflection",
                "lo escribí cuando no podía dormir",
                "--llm",
                "stub",
            ],
        )
    assert result.exit_code == 0
    assert "Saved to library" in result.output
    assert captured
    assert captured[0].reflection == "lo escribí cuando no podía dormir"


def test_reflection_prompt_skipped_with_yes() -> None:
    """--yes skips the interactive reflection prompt (scriptable flow)."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["write", "--theme", "luna", "--form", "haiku", "--yes", "--llm", "stub"],
    )
    assert result.exit_code == 0
    assert "What were you carrying" not in result.output

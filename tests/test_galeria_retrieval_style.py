"""CLI tests for ``galeria illustrate --style-from-retrieval``.

Covers the graceful-degradation contract: the flag must never hard-fail when
embeddings or the retrieval index are unavailable — it warns and still
illustrates with the base style.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from poesia.cli import app

runner = CliRunner()


def test_style_from_retrieval_degrades_gracefully_without_index(
    tmp_path: Path, monkeypatch: object
) -> None:
    """With no retrieval index, the flag warns and the command still runs."""
    monkeypatch.setenv("HOME", str(tmp_path))
    poem = tmp_path / "poema.txt"
    poem.write_text("La luna sobre el agua.\nLa noche callada.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "galeria",
            "illustrate",
            str(poem),
            "--style-from-retrieval",
            "--backend",
            "stub",
            "--dry-run",
            "--output",
            str(tmp_path / "auca.png"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "skipped" in result.stdout.lower()

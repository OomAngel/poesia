"""CLI tests for --semantic scoring (clean semantic ranking, no context)."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from poesia.cli import app


class FakeEmbeddingClient:
    """Deterministic stand-in so the CLI test never loads a real model."""

    dimension = 3

    def embed_one(self, text: str, text_type: str = "passage") -> list[float]:
        return [0.1, 0.2, 0.3]


def test_semantic_enables_theme_novelty_scoring() -> None:
    runner = CliRunner()
    with patch(
        "poesia.memoria.embeddings.get_embedding_client",
        return_value=FakeEmbeddingClient(),
    ):
        result = runner.invoke(
            app,
            [
                "write",
                "--theme",
                "luna",
                "--form",
                "haiku",
                "--semantic",
                "--verbose",
                "--llm",
                "stub",
            ],
        )
    assert result.exit_code == 0
    assert "metre + theme + novelty" in result.output


def test_semantic_degrades_gracefully_without_embeddings() -> None:
    runner = CliRunner()
    with patch(
        "poesia.memoria.embeddings.get_embedding_client",
        side_effect=RuntimeError("sentence-transformers not installed"),
    ):
        result = runner.invoke(
            app,
            [
                "write",
                "--theme",
                "luna",
                "--form",
                "haiku",
                "--semantic",
                "--verbose",
                "--llm",
                "stub",
            ],
        )
    assert result.exit_code == 0
    assert "metre only (semantic scoring unavailable)" in result.output

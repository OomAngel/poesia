"""P5 — Provider and operational controls.

Tests:
1. Privacy confirmation prompt when --brief + hosted LLM + fragments exist.
2. --yes flag skips the privacy confirmation.
3. PoemProvenance extended fields (provider, n_candidates, latency_ms).
4. Saved frontmatter includes new provenance fields.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from poesia.cli import app


# ---------------------------------------------------------------------------
# Save with full provenance includes P5 fields
# ---------------------------------------------------------------------------


def test_save_includes_latency_in_provenance(tmp_path: Path) -> None:
    """Saved files should contain latency_ms metadata."""
    import os
    old_home = os.environ.get("HOME")
    try:
        os.environ["HOME"] = str(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, [
            "write", "--theme", "luna", "--form", "haiku", "--save",
        ])
        assert result.exit_code == 0

        poems_dir = tmp_path / ".poesia" / "poems"
        md_files = list(poems_dir.glob("*.md"))
        assert md_files

        content = md_files[0].read_text(encoding="utf-8")
        assert "latency_ms:" in content, (
            f"Expected 'latency_ms:' in saved frontmatter. Content:\n{content}"
        )
    finally:
        os.environ["HOME"] = old_home

# ---------------------------------------------------------------------------
# Privacy confirmation (CLI integration)
# ---------------------------------------------------------------------------


def test_privacy_prompt_appears_with_brief_and_hosted_llm() -> None:
    """When --brief + hosted LLM + fragments exist, a privacy notice should appear."""
    from unittest.mock import patch

    from poesia.memoria.embeddings import StubEmbeddingClient

    runner = CliRunner()
    with patch("urllib.request.urlopen"), patch(
        "poesia.memoria.embeddings.get_embedding_client",
        return_value=StubEmbeddingClient(),
    ):
        result = runner.invoke(app, [
            "write", "--theme", "luna", "--form", "haiku",
            "--brief", "--llm", "groq",
        ], input="no\n")
    assert result.exit_code == 0
    assert "PRIVACY NOTICE" in result.stdout
    assert "cancelled" in result.stdout


def test_yes_flag_skips_privacy_prompt() -> None:
    """--yes should suppress the privacy confirmation."""
    from unittest.mock import patch

    from poesia.memoria.embeddings import StubEmbeddingClient

    runner = CliRunner()
    with patch("urllib.request.urlopen"), patch(
        "poesia.memoria.embeddings.get_embedding_client",
        return_value=StubEmbeddingClient(),
    ):
        result = runner.invoke(app, [
            "write", "--theme", "luna", "--form", "haiku",
            "--brief", "--llm", "groq", "--yes",
        ])
    assert "PRIVACY NOTICE" not in result.stdout, (
        "--yes should suppress the privacy notice"
    )


@pytest.mark.parametrize(
    "extra_args",
    [
        ["--llm", "groq"],              # no --brief → no notice
        ["--brief", "--llm", "stub"],   # stub LLM → no notice
    ],
)
def test_no_privacy_prompt_without_warrant(extra_args: list[str]) -> None:
    """Without the warrant (hosted LLM + --brief), no privacy notice appears."""
    from unittest.mock import patch

    from poesia.memoria.embeddings import StubEmbeddingClient

    runner = CliRunner()
    with patch("urllib.request.urlopen"), patch(
        "poesia.memoria.embeddings.get_embedding_client",
        return_value=StubEmbeddingClient(),
    ):
        result = runner.invoke(app, [
            "write", "--theme", "luna", "--form", "haiku", *extra_args,
        ])
    assert "PRIVACY NOTICE" not in result.stdout



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
from poesia.memoria.library import PoemProvenance


# ---------------------------------------------------------------------------
# PoemProvenance extended fields
# ---------------------------------------------------------------------------


def test_provenance_p5_fields_round_trip() -> None:
    """P5 extended fields store values and default to None."""
    prov = PoemProvenance(provider="groq", n_candidates=16, latency_ms=1234, temperature=0.8)
    assert prov.provider == "groq"
    assert prov.n_candidates == 16
    assert prov.latency_ms == 1234
    assert prov.temperature == 0.8

    defaults = PoemProvenance()
    assert defaults.provider is None
    assert defaults.n_candidates is None
    assert defaults.latency_ms is None
    assert defaults.temperature is None
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


def test_no_privacy_prompt_without_brief() -> None:
    """Without --brief, no privacy notice should appear even with hosted LLM."""
    from unittest.mock import patch

    runner = CliRunner()
    with patch("urllib.request.urlopen"):
        result = runner.invoke(app, [
            "write", "--theme", "luna", "--form", "haiku",
            "--llm", "groq",
        ])
    assert "PRIVACY NOTICE" not in result.stdout


def test_no_privacy_prompt_with_stub_llm() -> None:
    """With --brief but stub LLM, no privacy notice should appear."""
    from unittest.mock import patch

    from poesia.memoria.embeddings import StubEmbeddingClient

    runner = CliRunner()
    with patch(
        "poesia.memoria.embeddings.get_embedding_client",
        return_value=StubEmbeddingClient(),
    ):
        result = runner.invoke(app, [
            "write", "--theme", "luna", "--form", "haiku",
            "--brief", "--llm", "stub",
        ])
    assert "PRIVACY NOTICE" not in result.stdout



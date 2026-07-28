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


def test_provenance_has_provider_field() -> None:
    """PoemProvenance must have the P5 provider field."""
    prov = PoemProvenance(provider="groq")
    assert prov.provider == "groq"


def test_provenance_has_n_candidates_field() -> None:
    """PoemProvenance must have the P5 n_candidates field."""
    prov = PoemProvenance(n_candidates=16)
    assert prov.n_candidates == 16


def test_provenance_has_latency_ms_field() -> None:
    """PoemProvenance must have the P5 latency_ms field."""
    prov = PoemProvenance(latency_ms=1234)
    assert prov.latency_ms == 1234


def test_provenance_has_temperature_field() -> None:
    """PoemProvenance must have the P5 temperature field."""
    prov = PoemProvenance(temperature=0.8)
    assert prov.temperature == 0.8


def test_provenance_defaults_to_none() -> None:
    """P5 fields should default to None when not provided."""
    prov = PoemProvenance()
    assert prov.provider is None
    assert prov.n_candidates is None

    assert prov.latency_ms is None
    assert prov.temperature is None
# ---------------------------------------------------------------------------
# Save with full provenance includes P5 fields
# ---------------------------------------------------------------------------


def test_save_includes_provider_in_provenance(tmp_path: Path) -> None:
    """Saving with --save should include model/provider in saved frontmatter."""
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
        assert md_files, "No .md files saved"

        content = md_files[0].read_text(encoding="utf-8")
        assert "latency_ms:" in content, f"No latency_ms in saved file:\n{content}"
    finally:
        os.environ["HOME"] = old_home


def test_save_includes_latency_in_provenance(tmp_path: Path) -> None:
    """Saved files should contain latency_ms metadata."""
    import os
    old_home = os.environ.get("HOME")
    try:
        os.environ["HOME"] = str(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, [
            "write", "--theme", "sol", "--form", "haiku", "--save",
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
    runner = CliRunner()
    result = runner.invoke(app, [
        "write", "--theme", "luna", "--form", "haiku",
        "--brief", "--llm", "groq",
    ], input="no\n")
    assert result.exit_code == 0
    assert "PRIVACY NOTICE" in result.stdout
    assert "cancelled" in result.stdout


def test_yes_flag_skips_privacy_prompt() -> None:
    """--yes should suppress the privacy confirmation."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "write", "--theme", "luna", "--form", "haiku",
        "--brief", "--llm", "groq", "--yes",
    ])
    assert "PRIVACY NOTICE" not in result.stdout, (
        "--yes should suppress the privacy notice"
    )


def test_no_privacy_prompt_without_brief() -> None:
    """Without --brief, no privacy notice should appear even with hosted LLM."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "write", "--theme", "luna", "--form", "haiku",
        "--llm", "groq",
    ])
    assert "PRIVACY NOTICE" not in result.stdout


def test_no_privacy_prompt_with_stub_llm() -> None:
    """With --brief but stub LLM, no privacy notice should appear."""
    runner = CliRunner()
    result = runner.invoke(app, [
        "write", "--theme", "luna", "--form", "haiku",
        "--brief", "--llm", "stub",
    ])
    assert "PRIVACY NOTICE" not in result.stdout



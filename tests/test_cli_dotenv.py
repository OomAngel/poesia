"""Tests for the CLI's best-effort ``.env`` loading."""

from __future__ import annotations

import os
from pathlib import Path

from poesia.cli import _load_dotenv


def test_load_dotenv_sets_variables(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CLOUDFLARE_ACCOUNT_ID=acct-123\nCLOUDFLARE_API_TOKEN=tok-456\n",
        encoding="utf-8",
    )
    # ensure the variables are unset before the test
    for key in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"):
        os.environ.pop(key, None)

    _load_dotenv(str(env_file))

    assert os.environ.get("CLOUDFLARE_ACCOUNT_ID") == "acct-123"
    assert os.environ.get("CLOUDFLARE_API_TOKEN") == "tok-456"


def test_load_dotenv_existing_env_wins(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CLOUDFLARE_API_TOKEN=from-dotenv\n", encoding="utf-8")

    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "from-shell")

    _load_dotenv(str(env_file))

    assert os.environ["CLOUDFLARE_API_TOKEN"] == "from-shell"


def test_load_dotenv_missing_file_does_not_raise(tmp_path: Path) -> None:
    # must not raise even though the file does not exist
    _load_dotenv(str(tmp_path / "does-not-exist.env"))

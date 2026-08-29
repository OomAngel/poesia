"""Shared pytest configuration.

Two things this conftest exists for:

1. MLflow's async trace-exporter flush hangs the pytest process at shutdown
   (it waits on the backend queue even when PG is down). Tests don't need
   MLflow tracing at all, so disable it globally — no more ``-p no:mlflow``
   workaround needed, and ``pytest`` exits promptly.

2. ``poesia.cli`` used to load the project's real ``.env`` at *import* time,
   which meant merely importing a test file that touches ``poesia.cli``
   (many do, for ``CliRunner`` tests) leaked real provider API keys into
   ``os.environ`` for the rest of the pytest session, regardless of which
   test happened to run first — silently turning "no key configured" tests
   into live authenticated calls against production provider APIs.

   The structural fix: ``.env`` loading now lives in ``poesia.cli.main()``,
   a thin wrapper around ``app`` used only by the installed ``poesia``
   script — never by ``import poesia.cli`` or ``CliRunner(app, ...)``. This
   fixture is now defense-in-depth against real credentials already present
   in the *ambient* shell environment, not the load-bearing fix. Tests that
   specifically need a key set one via ``monkeypatch.setenv``.
"""

from __future__ import annotations

import os

import pytest


def pytest_configure() -> None:
    # Best-effort: disable MLflow tracing before any test imports it. This is
    # a test-only default; CI and real runs set their own MLFLOW_* env vars.
    os.environ.setdefault("MLFLOW_TRACKING_URI", "file:./mlruns-test")
    # MLflow checks this env var to skip trace export entirely — the reliable
    # switch, vs. calling mlflow.tracing.disable() which can race the decorator.
    os.environ.setdefault("MLFLOW_TRACING_DISABLED", "true")


_PROVIDER_CREDENTIAL_VARS = (
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN",
)


@pytest.fixture(autouse=True)
def _isolate_provider_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip real provider credentials from every test's environment."""
    for var in _PROVIDER_CREDENTIAL_VARS:
        monkeypatch.delenv(var, raising=False)

"""Shared pytest configuration.

The one thing this conftest exists for: MLflow's async trace-exporter flush
hangs the pytest process at shutdown (it waits on the backend queue even when
PG is down). Tests don't need MLflow tracing at all, so disable it globally —
no more ``-p no:mlflow`` workaround needed, and ``pytest`` exits promptly.
"""

from __future__ import annotations

import os


def pytest_configure() -> None:
    # Best-effort: disable MLflow tracing before any test imports it. This is
    # a test-only default; CI and real runs set their own MLFLOW_* env vars.
    os.environ.setdefault("MLFLOW_TRACKING_URI", "file:./mlruns-test")
    # MLflow checks this env var to skip trace export entirely — the reliable
    # switch, vs. calling mlflow.tracing.disable() which can race the decorator.
    os.environ.setdefault("MLFLOW_TRACING_DISABLED", "true")

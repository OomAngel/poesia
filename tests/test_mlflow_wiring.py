"""Regression test for the MLflow wiring in ``scripts/benchmark_metre.py``.

Under MLflow 3.x the filesystem tracking backend (``file:./mlruns``) was
removed and now raises ``MlflowException``. ``_log_mlflow`` wrapped that in a
blank ``except``, so the benchmark *appeared* to log while actually doing
nothing. This test asserts a run is genuinely queryable with the right metric
and params — not merely that the call didn't crash.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_benchmark() -> object:
    path = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_metre.py"
    spec = importlib.util.spec_from_file_location("benchmark_metre", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_benchmark_logs_run_to_mlflow(tmp_path, monkeypatch):
    import mlflow

    mod = _load_benchmark()
    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.setenv("DATABASE_URL", uri)

    mod._log_mlflow(
        {
            "backend": "stub",
            "form": "soneto:es",
            "correct": 2,
            "total": 3,
            "pct": 66.67,
            "samples": ["  ✓ 11/11  una línea de prueba"],
        },
        "line",
        "la luna",
    )

    mlflow.set_tracking_uri(uri)
    runs = mlflow.search_runs(experiment_ids=["0"])
    assert len(runs) == 1
    row = runs.iloc[0]
    assert row["params.backend"] == "stub"
    assert row["params.form"] == "soneto:es"
    assert row["params.mode"] == "line"
    assert row["metrics.metre_accuracy"] == 66.67
    assert row["metrics.correct_lines"] == 2
    assert row["metrics.total_lines"] == 3

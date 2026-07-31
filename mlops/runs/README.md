# Legacy Runs Directory — DEPRECATED (Phase 1, 2026-07-30)

This directory previously contained `experiments.jsonl` and per-run `.json` files
as the custom experiment database. As of Phase 1 consolidation, **all experiment
tracking now goes exclusively to MLflow** (`mlruns/mlflow.db`).

The files in this directory are kept for historical reference only. New training
runs no longer write here. Use instead:

    python mlops/experiments.py list          # List all experiments from MLflow
    mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db   # MLflow UI

If you encounter any script that reads from `mlops/runs/experiments.jsonl`,
it is outdated — update it to query MLflow directly.

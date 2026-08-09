#!/usr/bin/env python3
"""Hyperparameter optimization with Optuna + MLflow.

Searches LoRA hyperparameters efficiently using Bayesian optimization
instead of grid search. Each trial runs a shortened training cycle and
logs results to MLflow under a parent study experiment.

Usage:
    # Full search (30 trials, ~2h on GPU)
    python scripts/hpo_search.py --study-name lora-v1 --n-trials 30

    # Quick sanity (5 trials, ~20min)
    python scripts/hpo_search.py --study-name lora-quick --n-trials 5 \
        --base-config mlops/configs/train_v1.yaml

    # Resume interrupted study
    python scripts/hpo_search.py --study-name lora-v1 --resume

    # View results
    optuna-dashboard sqlite:///mlruns/optuna.db
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

import mlflow
import optuna
from optuna.integration import MLflowCallback

SEARCH_SPACE = {
    "lora_r": {"type": "int", "low": 8, "high": 64, "step": 8},
    "lora_alpha": {"type": "int", "low": 16, "high": 128, "step": 16},
    "lora_dropout": {"type": "float", "low": 0.0, "high": 0.3},
    "learning_rate": {"type": "float", "low": 5e-5, "high": 5e-4, "log": True},
    "batch_size": {"type": "int", "low": 4, "high": 16, "step": 4},
    "gradient_accumulation": {"type": "int", "low": 1, "high": 4, "step": 1},
}

_OPTUNA_DB = os.environ.get("OPTUNA_DB", "sqlite:///mlruns/optuna.db")


def _suggest(trial, param, spec):
    ptype = spec["type"]
    if ptype == "int":
        return trial.suggest_int(param, spec["low"], spec["high"], step=spec.get("step", 1))
    elif ptype == "float":
        return trial.suggest_float(param, spec["low"], spec["high"], log=spec.get("log", False))
    raise ValueError(f"Unknown type: {ptype}")


def _build_config(base_config, trial):
    import yaml

    cfg = dict(base_config)
    for param, spec in SEARCH_SPACE.items():
        cfg[param] = _suggest(trial, param, spec)
    cfg["epochs"] = min(cfg.get("epochs", 10), 5)
    cfg["run_name"] = f"hpo-trial-{trial.number}"
    cfg["experiment"] = f"hpo-{cfg.get('experiment', 'search')}"
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, prefix=f"hpo_{trial.number}_"
    )
    yaml.dump(cfg, tmp)
    tmp_path = tmp.name
    tmp.close()
    return tmp_path


def objective(trial, base_config_path):
    with open(base_config_path) as f:
        import yaml

        base_cfg = yaml.safe_load(f)
    config_path = _build_config(base_cfg, trial)
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "scripts/train_poetry_lora.py", config_path],
            capture_output=True,
            text=True,
            timeout=7200,
        )
        slur_dev = None
        for line in result.stdout.split("\n"):
            if "Avg syllable deviation" in line:
                import re

                match = re.search(r"(\d+\.?\d*)", line)
                if match:
                    slur_dev = float(match.group(1))
                    break
        if slur_dev is None:
            import glob

            eval_files = glob.glob("models/poetry-lora-hpo*/eval_results.json")
            if eval_files:
                with open(eval_files[0]) as f:
                    data = json.load(f)
                slur_dev = data.get("summary", {}).get("avg_syllable_deviation")
        if slur_dev is None:
            raise ValueError(f"No eval metric for trial {trial.number}")
        return slur_dev
    except subprocess.TimeoutExpired:
        return float("inf")
    except Exception as e:
        print(f"Trial {trial.number} failed: {e}")
        return float("inf")
    finally:
        try:
            os.unlink(config_path)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-name", default="poesia-hpo-v1")
    parser.add_argument("--n-trials", type=int, default=20)
    parser.add_argument("--base-config", default="mlops/configs/train_v1.yaml")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    tracking_uri = os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db")
    mlflow_callback = MLflowCallback(
        tracking_uri=tracking_uri,
        metric_name="eval_syllable_deviation",
        create_experiment=False,
    )

    storage = optuna.storages.RDBStorage(
        url=_OPTUNA_DB,
        engine_kwargs={"connect_args": {"timeout": 30}},
    )

    study = optuna.create_study(
        study_name=args.study_name,
        storage=storage,
        direction="minimize",
        load_if_exists=args.resume,
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10, interval_steps=1),
    )

    print(f"Starting HPO study: {args.study_name}")
    print(f"  Trials: {args.n_trials}")
    print(f"  Search space: {list(SEARCH_SPACE.keys())}")
    print(f"  Base config: {args.base_config}")
    print(f"  Resume: {args.resume}")
    print()

    study.optimize(
        lambda trial: objective(trial, args.base_config),
        n_trials=args.n_trials,
        callbacks=[mlflow_callback],
        show_progress_bar=True,
    )

    print(f"\n\\U0001f3f4 Best trial: {study.best_trial.number}")
    print(f"   Best eval_syllable_deviation: {study.best_trial.value:.4f}")
    print(f"   Best params: {study.best_trial.params}")

    mlflow.set_experiment(f"hpo-{args.study_name}")
    with mlflow.start_run(run_name="best_params"):
        for k, v in study.best_trial.params.items():
            mlflow.log_param(f"best_{k}", v)
        mlflow.log_metric("best_eval_syllable_deviation", study.best_trial.value)
        mlflow.log_param("study_name", args.study_name)
        mlflow.log_param("n_trials", args.n_trials)

    print("\nView results:")
    print(f"  MLflow: mlflow ui --backend-store-uri {tracking_uri}")
    print(f"  Optuna: optuna-dashboard {_OPTUNA_DB}")


if __name__ == "__main__":
    main()

"""Experiments database — queries MLflow directly (Phase 1 consolidation).

This replaces the legacy JSONL-backed experiments CLI.
All experiment data now lives in MLflow (SQLite at mlruns/mlflow.db).

Usage:
    python mlops/experiments.py list                          # List all runs
    python mlops/experiments.py list --experiment soneto      # Filter by experiment
    python mlops/experiments.py best --metric line_count_accuracy  # Best by metric
    python mlops/experiments.py compare --ids run1_id run2_id # Side-by-side
    python mlops/experiments.py tag --id run_id --add "r=64"  # Add tags
"""

import argparse
import os
from datetime import datetime

import mlflow
from mlflow.tracking import MlflowClient


_TRACKING_URI = os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db")


def _client() -> MlflowClient:
    mlflow.set_tracking_uri(_TRACKING_URI)
    return MlflowClient(_TRACKING_URI)


def _run_to_dict(run, experiment_name: str) -> dict:
    """Convert an MLflow run to a flat dict for display."""
    data = run.data
    info = run.info
    return {
        "run_id": info.run_id,
        "experiment": experiment_name,
        "run_name": data.tags.get("mlflow.runName", info.run_id[:8]),
        "status": info.status,
        "start_time": (
            datetime.fromtimestamp(info.start_time / 1000).isoformat()
            if info.start_time else None
        ),
        "tags": sorted(k for k in data.tags if k != "mlflow.runName"),
        "model": data.params.get("model", "?"),
        "lora_r": int(data.params.get("lora_r", 0)),
        "epochs": int(data.params.get("epochs", 0)),
        "learning_rate": float(data.params.get("learning_rate", 0)),
        "loss_fn": data.params.get("loss_fn", "ce"),
        "config": data.params.get("config", ""),
        "data_records": int(data.params.get("data_records", 0)),
        "data_sha256": data.params.get("data_sha256", ""),
        "adapter_path": data.params.get("adapter_path", ""),
        "git_commit": data.params.get("git_commit", ""),
        "train_loss": data.metrics.get("train_loss"),
        "eval_loss": data.metrics.get("eval_loss"),
        "eval_line_count_accuracy": data.metrics.get("eval_line_count_accuracy"),
        "eval_syllable_deviation": data.metrics.get("eval_syllable_deviation"),
        "eval_avg_line_count": data.metrics.get("eval_avg_line_count"),
        "train_duration_seconds": data.metrics.get("train_duration_seconds"),
    }


def _load_runs() -> list:
    """Load all runs across all experiments from MLflow."""
    client = _client()
    all_runs = []
    for exp in client.search_experiments():
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["attributes.start_time DESC"],
        )
        for r in runs:
            all_runs.append(_run_to_dict(r, exp.name))
    return all_runs


def cmd_list(args):
    runs = _load_runs()
    if args.experiment:
        runs = [r for r in runs if args.experiment.lower() in r["experiment"].lower()]
    if not runs:
        print("No runs found.")
        return
    header = (
        f"{'Run ID':<12} {'Experiment':<20} {'Name':<22} "
        f"{'Loss':<8} {'Line%':<8} {'Syll Dev':<9} {'R':<3} {'Status':<10}"
    )
    print(header)
    print("-" * len(header))
    for r in runs:
        loss = f"{r['train_loss']:.3f}" if r["train_loss"] is not None else "-"
        line_acc = (
            f"{r['eval_line_count_accuracy']:.0%}"
            if r["eval_line_count_accuracy"] is not None else "-"
        )
        syll_dev = (
            f"{r['eval_syllable_deviation']:.1f}"
            if r["eval_syllable_deviation"] is not None else "-"
        )
        print(
            f"{r['run_id'][:10]:<12} "
            f"{r['experiment'][:18]:<20} "
            f"{r['run_name'][:20]:<22} "
            f"{loss:<8} {line_acc:<8} {syll_dev:<9} "
            f"{r['lora_r']:<3} {r['status'][:8]:<10}"
        )


def cmd_best(args):
    runs = _load_runs()
    metric = args.metric
    valid = [(r, r.get(metric)) for r in runs if r.get(metric) is not None]
    if not valid:
        print(f"No runs have metric '{metric}'")
        return
    higher_better = ["eval_line_count_accuracy", "eval_avg_line_count"]
    reverse = metric in higher_better
    valid.sort(key=lambda x: x[1], reverse=reverse)
    best_run, best_val = valid[0]
    print(f"\n\\U0001f3f4 Best run by {metric} = {best_val:.4f}")
    print(f"  Experiment: {best_run['experiment']}")
    print(f"  Run name:   {best_run['run_name']}")
    print(f"  Run ID:     {best_run['run_id']}")
    if best_run.get("adapter_path"):
        print(f"  Adapter:    {best_run['adapter_path']}")
    print(f"\n  All metrics:")
    for k, v in sorted(best_run.items()):
        if k in ("run_id", "experiment", "run_name", "config",
                 "git_commit", "tags", "adapter_path", "status"):
            continue
        if v is not None:
            print(f"    {k}: {v}")


def cmd_compare(args):
    runs = _load_runs()
    target_ids = args.ids
    selected = [
        r for r in runs
        if r["run_id"][:8] in target_ids or r["run_id"] in target_ids
    ]
    if len(selected) < 2:
        print(f"Need at least 2 matching runs. Found {len(selected)}.")
        return
    print(f"\n{'Metric':<30}", end="")
    for r in selected:
        name = r.get("run_name", r["run_id"][:12])
        print(f"{name:<22}", end="")
    print()
    print("-" * (30 + 22 * len(selected)))
    metrics = [
        "lora_r", "epochs", "learning_rate", "train_loss",
        "eval_line_count_accuracy", "eval_syllable_deviation",
        "eval_avg_line_count", "train_duration_seconds", "data_records",
    ]
    for m in metrics:
        print(f"{m:<30}", end="")
        for r in selected:
            val = r.get(m)
            if val is None:
                print(f"{'─':<22}", end="")
            elif isinstance(val, float):
                print(f"{val:.4f}{'':<17}", end="")
            elif isinstance(val, int):
                print(f"{val:<22}", end="")
            else:
                print(f"{str(val)[:20]:<22}", end="")
        print()


def cmd_tag(args):
    client = _client()
    runs = _load_runs()
    target = next(
        (r for r in runs
         if r["run_id"].startswith(args.id) or r["run_name"] == args.id),
        None,
    )
    if target is None:
        print(f"No run matching '{args.id}'")
        return
    if args.add:
        client.set_tag(target["run_id"], args.add, "true")
        print(f"Added tag '{args.add}' to {target['run_id'][:8]}")
    if args.remove:
        client.delete_tag(target["run_id"], args.remove)
        print(f"Removed tag '{args.remove}' from {target['run_id'][:8]}")


def main():
    parser = argparse.ArgumentParser(
        description="MLflow-backed experiment DB (Phase 1)."
    )
    sub = parser.add_subparsers(dest="command")
    p_list = sub.add_parser("list")
    p_list.add_argument("--experiment", "-e", default=None)
    p_best = sub.add_parser("best")
    p_best.add_argument(
        "--metric", default="eval_line_count_accuracy",
        help="Metric to optimize (default: line_count_accuracy)",
    )
    p_comp = sub.add_parser("compare")
    p_comp.add_argument("--ids", nargs="+", required=True)
    p_tag = sub.add_parser("tag")
    p_tag.add_argument("--id", required=True)
    p_tag.add_argument("--add", default=None)
    p_tag.add_argument("--remove", default=None)
    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "best":
        cmd_best(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "tag":
        cmd_tag(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

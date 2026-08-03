"""List and compare training runs from MLflow (Phase 1 consolidation).

Usage:
    python mlops/list_runs.py          # List all runs
    python mlops/list_runs.py --compare  # Compare runs side by side (all)
"""

import os
import sys

import mlflow
from mlflow.tracking import MlflowClient

_TRACKING_URI = os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db")


def _load_runs():
    mlflow.set_tracking_uri(_TRACKING_URI)
    client = MlflowClient(_TRACKING_URI)
    runs = []
    for exp in client.search_experiments():
        for r in client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["attributes.start_time DESC"],
        ):
            data = r.data
            runs.append(
                {
                    "run_id": r.info.run_id,
                    "experiment": exp.name,
                    "model": data.params.get("model", "?"),
                    "lora_r": data.params.get("lora_r", "?"),
                    "epochs": data.params.get("epochs", "?"),
                    "learning_rate": data.params.get("learning_rate", "?"),
                    "train_loss": data.metrics.get("train_loss"),
                    "status": r.info.status,
                    "adapter_path": data.params.get("adapter_path", ""),
                }
            )
    return runs


def main():
    runs = _load_runs()
    if not runs:
        print("No runs found.")
        sys.exit(0)

    header = (
        f"{'Run ID':<12} {'Experiment':<20} {'Model':<28} "
        f"{'R':<3} {'Ep':<3} {'LR':<10} {'Loss':<8} {'Status':<10} {'Adapter'}"
    )
    print(header)
    print("-" * len(header))

    for r in runs:
        lr = r.get("learning_rate", "?")
        lr_str = f"{float(lr):.0e}" if lr != "?" and lr else str(lr)
        loss = r.get("train_loss")
        loss_str = f"{loss:.4f}" if loss is not None else "-"
        status = r["status"]
        adapter = r.get("adapter_path", "")[:20] if r.get("adapter_path") else "-"
        print(
            f"{r['run_id'][:10]:<12} "
            f"{r['experiment'][:18]:<20} "
            f"{r['model'][:26]:<28} "
            f"{str(r['lora_r']):<3} "
            f"{str(r['epochs']):<3} {lr_str:<10} {loss_str:<8} "
            f"{status[:8]:<10} {adapter}"
        )

    if "--compare" in sys.argv and len(runs) >= 2:
        print(f"\n=== COMPARISON: {len(runs)} runs ===")
        print(f"{'Metric':<20}", end="")
        for r in runs:
            print(f"{r['run_id'][:12]:<15}", end="")
        print()
        print("-" * (20 + 15 * len(runs)))

        for m in ["lora_r", "epochs", "learning_rate", "train_loss"]:
            print(f"{m:<20}", end="")
            for r in runs:
                v = r.get(m, "-")
                if isinstance(v, float):
                    v = f"{v:.4f}"
                elif m == "learning_rate" and v != "?":
                    try:
                        v = f"{float(v):.0e}"
                    except (ValueError, TypeError):
                        pass
                print(f"{str(v):<15}", end="")
            print()


if __name__ == "__main__":
    main()

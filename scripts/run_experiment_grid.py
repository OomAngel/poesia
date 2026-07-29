#!/usr/bin/env python3
"""Run a grid of training experiments comparing models, techniques, and loss functions.

Each combination is logged as a separate MLflow run with all params recorded.

Usage:
    # Run specific grid
    python scripts/run_experiment_grid.py --grid mlops/grids/quick_compare.json

    # Run all defined grids
    python scripts/run_experiment_grid.py --all
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime


GRID_DEFINITIONS = {
    "loss_compare": {
        "description": "Compare CE vs Composite vs DPO loss on same data",
        "experiments": [
            {"config": "mlops/configs/train_v1.yaml", "tags": ["baseline-ce"]},
            {"config": "mlops/configs/train_composite.yaml", "tags": ["composite-loss"]},
            {"config": "mlops/configs/dpo_v1.yaml", "tags": ["dpo"]},
        ],
    },
    "lora_rank": {
        "description": "Compare LoRA ranks: r=16 vs r=32 vs r=64",
        "experiments": [
            {"config": "mlops/configs/train_v1.yaml", "tags": ["r16"]},
            {"config": "mlops/configs/train_multiform.yaml", "tags": ["r32"]},
            {"config": "mlops/configs/train_multiform.yaml", "overrides": {"lora_r": 64}, "tags": ["r64"]},
        ],
    },
    "data_quality": {
        "description": "Compare unfiltered vs filtered vs distilled data",
        "experiments": [
            {"config": "mlops/configs/train_v1.yaml", "tags": ["data-raw"]},
            {"config": "mlops/configs/train_v1.yaml",
             "overrides": {"train_data": "seeds/poetry_corpus/training_data_structured/sonetos_filtered_t2.jsonl"},
             "tags": ["data-filtered"]},
            {"config": "mlops/configs/train_distilled.yaml", "tags": ["data-distilled"]},
        ],
    },
}


def run_experiment(config_path, tags=None, overrides=None):
    """Run one training experiment and log it to MLflow."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n{'='*60}")
    print(f"Run: {run_id}")
    print(f"Config: {config_path}")
    print(f"Tags: {tags or []}")
    print(f"Overrides: {overrides or {}}")
    print(f"{'='*60}")

    env = os.environ.copy()
    if overrides:
        for k, v in overrides.items():
            env[f"OVERRIDE_{k.upper()}"] = str(v)

    result = subprocess.run(
        [sys.executable, "scripts/train_poetry_lora.py", config_path],
        cwd="/home/angel/dev/poesia",
        env=env,
        capture_output=False,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", default=None, help="Grid name to run")
    parser.add_argument("--all", action="store_true", help="Run all grids")
    args = parser.parse_args()

    if args.grid:
        grids = {args.grid: GRID_DEFINITIONS[args.grid]}
    elif args.all:
        grids = GRID_DEFINITIONS
    else:
        print("Available grids:")
        for name, defn in GRID_DEFINITIONS.items():
            print(f"  {name}: {defn['description']} ({len(defn['experiments'])} exps)")
        print("\nUsage: python scripts/run_experiment_grid.py --grid <name>")
        return

    results = []
    for grid_name, grid_def in grids.items():
        print(f"\n>>> Grid: {grid_name} — {grid_def['description']}")
        for exp in grid_def["experiments"]:
            success = run_experiment(
                exp["config"],
                tags=exp.get("tags"),
                overrides=exp.get("overrides"),
            )
            results.append({
                "grid": grid_name,
                "config": exp["config"],
                "tags": exp.get("tags"),
                "success": success,
            })
            time.sleep(5)  # Let system settle between runs

    print(f"\n{'='*60}")
    print("Grid Results:")
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['grid']}: {r['config']} ({', '.join(r['tags'] or [])})")


if __name__ == "__main__":
    main()

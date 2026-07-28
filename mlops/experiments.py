"""Experiments database — MLflow-style tracking but in JSONL.

Usage:
    python mlops/experiments.py list                          # List all runs
    python mlops/experiments.py list --experiment soneto      # Filter by experiment
    python mlops/experiments.py best --metric line_count_accuracy  # Best by metric
    python mlops/experiments.py compare --ids run1_id run2_id # Side-by-side
    python mlops/experiments.py tag --id run_id --add "r=64"  # Add tags to a run
"""

import argparse, json, sys, os, glob
from pathlib import Path
from datetime import datetime


def load_db() -> list[dict]:
    """Load all runs from the experiments database."""
    db_path = Path("mlops/runs/experiments.jsonl")
    if not db_path.exists():
        # Fallback: load individual JSON files
        runs = []
        for f in sorted(Path("mlops/runs").glob("*.json")):
            if f.name == "ab_comparison.json":
                continue
            with open(f) as fh:
                runs.append(json.load(fh))
        return runs
    
    runs = []
    with open(db_path) as f:
        for line in f:
            if line.strip():
                runs.append(json.loads(line))
    return runs


def save_db(runs: list[dict]):
    """Overwrite the experiments database."""
    db_path = Path("mlops/runs/experiments.jsonl")
    with open(db_path, "w") as f:
        for r in runs:
            f.write(json.dumps(r) + "\n")


def cmd_list(args):
    runs = load_db()
    if args.experiment:
        runs = [r for r in runs if r.get("experiment") == args.experiment]
    
    if not runs:
        print("No runs found.")
        return
    
    # Determine columns
    cols = ["run_id", "experiment", "run_name", "tags", "lora_r", "epochs", 
            "train_loss", "eval_line_count_accuracy", "eval_syllable_deviation", "status"]
    
    header = f"{'Run ID':<20} {'Experiment':<20} {'Name':<22} {'Tags':<20} {'R':<3} {'Ep':<3} {'Loss':<8} {'Line%':<8} {'Syll Dev':<9} {'Status'}"
    print(header)
    print("-" * len(header))
    
    for r in runs:
        tags = ", ".join(r.get("tags", []))[:18]
        loss = f"{r.get('train_loss', 0):.3f}" if r.get("train_loss") else "-"
        line_acc = f"{r.get('eval_line_count_accuracy', 0):.0%}" if r.get("eval_line_count_accuracy") else "-"
        syll_dev = f"{r.get('eval_syllable_deviation', 0):.1f}" if r.get("eval_syllable_deviation") else "-"
        
        print(f"{r.get('run_id', '?')[:18]:<20} "
              f"{r.get('experiment', '?')[:18]:<20} "
              f"{r.get('run_name', '?')[:20]:<22} "
              f"{tags:<20} "
              f"{str(r.get('lora_r', '?')):<3} "
              f"{str(r.get('epochs', '?')):<3} "
              f"{loss:<8} "
              f"{line_acc:<8} "
              f"{syll_dev:<9} "
              f"{r.get('status', '?')}")


def cmd_best(args):
    runs = load_db()
    metric = args.metric
    
    # Filter to runs that have this metric
    valid = [(r, r.get(metric)) for r in runs if r.get(metric) is not None]
    if not valid:
        print(f"No runs have metric '{metric}'")
        return
    
    # Higher is better for accuracy, lower for loss/deviation
    higher_better = ["eval_line_count_accuracy", "eval_avg_line_count"]
    reverse = metric in higher_better
    
    valid.sort(key=lambda x: x[1], reverse=reverse)
    
    best_run, best_val = valid[0]
    print(f"\n🏆 Best run by '{metric}': {best_val}")
    print(f"  Run ID: {best_run.get('run_id')}")
    print(f"  Experiment: {best_run.get('experiment')}")
    print(f"  Run name: {best_run.get('run_name')}")
    print(f"  Tags: {best_run.get('tags')}")
    print(f"  Config: {best_run.get('config')}")
    print(f"  Git commit: {best_run.get('git_commit')}")
    print(f"  Duration: {best_run.get('duration_s', 0):.0f}s")
    if best_run.get("adapter_path"):
        print(f"  Adapter: {best_run['adapter_path']}")
    
    print(f"\n  All metrics:")
    for k in sorted(best_run.keys()):
        if k in ("run_id", "experiment", "run_name", "config", "git_commit", "tags", "adapter_path", "status"):
            continue
        if best_run[k] is not None:
            print(f"    {k}: {best_run[k]}")


def cmd_compare(args):
    runs = load_db()
    target_ids = args.ids
    selected = [r for r in runs if r.get("run_id", "")[:8] in target_ids or r.get("run_id") in target_ids]
    
    if len(selected) < 2:
        print(f"Need at least 2 matching runs. Found {len(selected)}.")
        return
    
    print(f"\n{'Metric':<30}", end="")
    for r in selected:
        name = r.get("run_name", r.get("run_id", "?")[:12])
        print(f"{name:<22}", end="")
    print()
    print("-" * (30 + 22 * len(selected)))
    
    metrics = ["lora_r", "epochs", "learning_rate", "train_loss", 
               "eval_line_count_accuracy", "eval_syllable_deviation",
               "eval_avg_line_count", "duration_s", "data_records"]
    
    for m in metrics:
        print(f"{m:<30}", end="")
        for r in selected:
            val = r.get(m)
            if val is None:
                print(f"{'-':<22}", end="")
            elif isinstance(val, float):
                print(f"{val:.4f}{'':<17}", end="")
            elif isinstance(val, int):
                print(f"{val:<22}", end="")
            else:
                print(f"{str(val)[:20]:<22}", end="")
        print()


def cmd_tag(args):
    runs = load_db()
    for r in runs:
        if r.get("run_id", "").startswith(args.id) or r.get("run_name") == args.id:
            current_tags = r.get("tags", [])
            if args.add:
                if args.add not in current_tags:
                    current_tags.append(args.add)
                    r["tags"] = current_tags
                    print(f"Added tag '{args.add}' to {r.get('run_id')}")
            if args.remove:
                if args.remove in current_tags:
                    current_tags.remove(args.remove)
                    r["tags"] = current_tags
                    print(f"Removed tag '{args.remove}' from {r.get('run_id')}")
            break
    
    save_db(runs)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    
    # list
    p_list = sub.add_parser("list")
    p_list.add_argument("--experiment", "-e", default=None)
    
    # best
    p_best = sub.add_parser("best")
    p_best.add_argument("--metric", default="eval_line_count_accuracy",
                       help="Metric to optimize (default: line_count_accuracy)")
    
    # compare
    p_comp = sub.add_parser("compare")
    p_comp.add_argument("--ids", nargs="+", required=True)
    
    # tag
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

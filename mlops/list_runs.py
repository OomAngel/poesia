"""List and compare training runs from mlops/runs/.

Usage:
    python mlops/list_runs.py          # List all runs
    python mlops/list_runs.py --compare  # Compare runs side by side
"""

import json, os, sys
from pathlib import Path

runs_dir = Path("mlops/runs")
if not runs_dir.exists():
    print("No runs found.")
    sys.exit(0)

runs = []
for f in sorted(runs_dir.glob("*.json")):
    with open(f) as fh:
        runs.append(json.load(fh))

if not runs:
    print("No runs found.")
    sys.exit(0)

# Header
fields = ["run_id", "model", "lora_r", "epochs", "learning_rate", "train_loss", "status", "adapter_path"]
header = f"{'Run ID':<20} {'Model':<30} {'R':<3} {'Ep':<3} {'LR':<10} {'Loss':<8} {'Status':<12} {'Adapter'}"
print(header)
print("-" * len(header))

for r in runs:
    run_id = r.get("run_id", "?")[:17]
    model = r.get("model", "?")[:28]
    lr = r.get("learning_rate", "?")
    lr_str = f"{lr:.0e}" if isinstance(lr, (int, float)) else str(lr)
    loss = r.get("train_loss", "?")
    loss_str = f"{loss:.4f}" if isinstance(loss, (int, float)) else str(loss)
    status = r.get("status", "?")
    adapter = r.get("adapter_path", "")[:20] if r.get("adapter_path") else "-"
    print(f"{run_id:<20} {model:<30} {str(r.get('lora_r', '?')):<3} "
          f"{str(r.get('epochs', '?')):<3} {lr_str:<10} {loss_str:<8} "
          f"{status:<12} {adapter}")

# Compare mode
if "--compare" in sys.argv and len(runs) >= 2:
    print(f"\n=== COMPARISON: {len(runs)} runs ===")
    print(f"{'Metric':<20}", end="")
    for r in runs:
        print(f"{r.get('run_id', '?')[:12]:<15}", end="")
    print()
    print("-" * (20 + 15 * len(runs)))
    
    metrics = ["lora_r", "epochs", "learning_rate", "train_loss", "train_samples"]
    for m in metrics:
        print(f"{m:<20}", end="")
        for r in runs:
            val = r.get(m, "-")
            if isinstance(val, float):
                val = f"{val:.4f}"
            print(f"{str(val):<15}", end="")
        print()

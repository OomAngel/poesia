"""PoesIA training pipeline orchestrator.

Runs the full pipeline: distill → train → evaluate → register.

Usage:
    python mlops/pipeline.py --distill 100
    python mlops/pipeline.py --train mlops/configs/train_distilled.yaml
    python mlops/pipeline.py --all --distill-count 100
"""

import argparse, json, os, subprocess, sys, yaml
from pathlib import Path


def run_step(description: str, command: list[str]) -> bool:
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"✗ STEP FAILED: {description}")
        return False
    print(f"✓ {description}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--distill", type=int, default=0, help="Generate N sonetos via Groq")
    parser.add_argument("--train", type=str, default=None, help="Path to training config YAML")
    parser.add_argument("--evaluate", type=str, default=None, help="Path to adapter to evaluate")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: distill → train → evaluate")
    parser.add_argument("--distill-count", type=int, default=100, help="Number of sonetos to distill")
    args = parser.parse_args()

    if args.all:
        print("=== FULL PIPELINE ===")
        # Step 1: Distill
        ok = run_step("Distill sonetos from Groq", [
            sys.executable, "scripts/distill_sonetos.py",
            "--count", str(args.distill_count),
        ])
        if not ok:
            sys.exit(1)
        
        # Step 2: Train
        config = "mlops/configs/train_distilled.yaml"
        ok = run_step("Train LoRA adapter", [
            sys.executable, "scripts/train_poetry_lora.py", config,
        ])
        if not ok:
            sys.exit(1)
        
        # Step 3: Evaluate
        with open(config) as f:
            cfg = yaml.safe_load(f)
        adapter = os.path.join(cfg["output_dir"], "final_adapter")
        ok = run_step("Evaluate adapter", [
            sys.executable, "mlops/evaluate_adapter.py", "--adapter", adapter,
        ])
        if not ok:
            sys.exit(1)
        
        print(f"\n{'='*60}")
        print("✅ FULL PIPELINE COMPLETE")
        print(f"{'='*60}")
        return

    if args.distill:
        run_step(f"Distill {args.distill} sonetos", [
            sys.executable, "scripts/distill_sonetos.py",
            "--count", str(args.distill),
        ])

    if args.train:
        run_step(f"Train with {args.train}", [
            sys.executable, "scripts/train_poetry_lora.py", args.train,
        ])

    if args.evaluate:
        run_step(f"Evaluate {args.evaluate}", [
            sys.executable, "mlops/evaluate_adapter.py", "--adapter", args.evaluate,
        ])


if __name__ == "__main__":
    main()

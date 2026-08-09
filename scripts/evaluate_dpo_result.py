#!/usr/bin/env python3
"""DPO Evaluation Harness — evaluate DPO adapter & compare vs CE baseline.

Usage:
    python scripts/evaluate_dpo_result.py              # eval both adapters
    python scripts/evaluate_dpo_result.py --wait        # wait for DPO to finish
    python scripts/evaluate_dpo_result.py --dry-run     # preview only
"""

import os
import subprocess
import sys
import time
import warnings

warnings.filterwarnings("ignore")

DPO_ADAPTER = "models/poetry-lora-dpo-expanded/final_adapter"
CE_ADAPTER = "models/poetry-lora-qwen3b/final_adapter"
THEMES = ["luna sobre el mar", "amor eterno", "noche estrellada", "sol naciente", "viento del sur"]
N_CANDIDATES = 4
POESIA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wait_for_dpo():
    """Poll until DPO training process exits."""
    print("Waiting for DPO training to finish...")
    while True:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        if "train_poetry_dpo" not in result.stdout:
            print("DPO process is gone.")
            # Check log for exit status
            log_path = "/tmp/dpo_training.log"
            if os.path.exists(log_path):
                with open(log_path) as f:
                    content = f.read()
                if "DPO exit:" in content:
                    exit_code = [l for l in content.split("\n") if "DPO exit:" in l][-1]
                    print(f"  {exit_code}")
            return
        print("  DPO still running — checking again in 30s...")
        time.sleep(30)


def evaluate_adapter(label, adapter_rel, base_model):
    """Generate poems and score syllable accuracy."""
    sys.path.insert(0, POESIA_ROOT)
    from poesia.generation.constrained_loop import ConstrainedLoop
    from poesia.generation.llm_client import LoRAClient
    from poesia.phonology.spanish import SpanishPhonology

    adapter_path = os.path.join(POESIA_ROOT, adapter_rel)
    if not os.path.isdir(adapter_path):
        print(f"  [SKIP] Adapter not found: {adapter_path}")
        return None

    print(f"\n  Evaluating: {label}")
    print(f"  Adapter: {adapter_rel}")
    client = LoRAClient(base_model=base_model, adapter_path=adapter_path)
    phon = SpanishPhonology()
    results = []

    for theme in THEMES:
        loop = ConstrainedLoop(language="es", form="soneto", llm=client)
        result = loop.run(theme=theme, n_candidates=N_CANDIDATES)

        correct = 0
        total_dev = 0.0
        for i, line in enumerate(result.lines):
            scan = phon.scan_line(line)
            dev = abs(scan.metrical_syllable_count - 11)
            total_dev += dev
            if dev <= 1:
                correct += 1

        avg_dev = total_dev / max(len(result.lines), 1)
        results.append(
            {
                "theme": theme,
                "lines": len(result.lines),
                "correct": correct,
                "avg_deviation": round(avg_dev, 2),
            }
        )
        print(
            f"    [{theme:20s}] lines={len(result.lines)} correct={correct}/{len(result.lines)} dev={avg_dev:.2f}"
        )

    total_lines = sum(r["lines"] for r in results)
    total_correct = sum(r["correct"] for r in results)
    avg_dev_all = sum(r["avg_deviation"] for r in results) / len(results)
    accuracy = (total_correct / total_lines * 100) if total_lines else 0

    print(f"\n  ═══ {label} Summary ═══")
    print(f"    Total lines: {total_lines}")
    print(f"    Metre accuracy: {accuracy:.1f}%")
    print(f"    Avg syllable deviation: {avg_dev_all:.2f}")

    return {
        "label": label,
        "total_lines": total_lines,
        "correct_lines": total_correct,
        "accuracy": accuracy,
        "avg_deviation": avg_dev_all,
        "themes": results,
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "eval"

    if mode == "--dry-run":
        print("═══ DPO Eval — Dry Run ═══")
        print(f"  Adapt: 1. DPO: {DPO_ADAPTER}")
        print(f"         2. CE:  {CE_ADAPTER}")
        print(f"  Themes ({len(THEMES)}): {THEMES}")
        print(f"  Candidates/line: {N_CANDIDATES}")
        print("  Est. time: ~5 min per adapter")
        return

    if mode == "--wait":
        wait_for_dpo()

    # Source env
    os.chdir(POESIA_ROOT)

    print("═══ DPO Evaluation Harness ═══")
    print(f"Started: {time.ctime()}\n")

    dpo_result = evaluate_adapter(
        "DPO (poetry-lora-dpo-expanded)", DPO_ADAPTER, "Qwen/Qwen2.5-1.5B-Instruct"
    )
    ce_result = evaluate_adapter(
        "CE Baseline (poetry-lora-qwen3b)", CE_ADAPTER, "Qwen/Qwen2.5-3B-Instruct"
    )

    if dpo_result and ce_result:
        print("\n═══════════════════════════════════════")
        print("       COMPARISON RESULTS")
        print("═══════════════════════════════════════")
        print(f"{'Metric':30s} {'DPO':>12s} {'CE (qwen3b)':>12s}")
        print("-" * 54)
        print(
            f"{'Metre accuracy':30s} {dpo_result['accuracy']:>11.1f}% {ce_result['accuracy']:>11.1f}%"
        )
        print(
            f"{'Avg syllable deviation':30s} {dpo_result['avg_deviation']:>11.2f}  {ce_result['avg_deviation']:>11.2f}"
        )
        print(
            f"{'Total lines':30s} {dpo_result['total_lines']:>11d}  {ce_result['total_lines']:>11d}"
        )
        winner = "DPO" if dpo_result["accuracy"] >= ce_result["accuracy"] else "CE Baseline"
        print(f"\n  🏆 Winner: {winner}")


if __name__ == "__main__":
    main()

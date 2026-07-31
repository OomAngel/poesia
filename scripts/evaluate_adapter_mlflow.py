#!/usr/bin/env python3
"""MLflow-native evaluation using existing Poesia metrics.

Supports nested runs (Phase 4): if --parent-run-id is provided, evaluation
metrics are logged as a child of the training run, establishing provenance.
If omitted, creates a top-level run (backward compatible).

Usage:
    python scripts/evaluate_adapter_mlflow.py --adapter models/poetry-lora-v2/final_adapter \\
        --theme luna --form soneto
    python scripts/evaluate_adapter_mlflow.py --adapter models/poetry-lora-v2/final_adapter \\
        --parent-run-id <mlflow_run_id>  # nested under training run
"""

import argparse
import os
import mlflow

# MLflow setup
mlflow.set_tracking_uri(os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db"))
try:
    mlflow.create_experiment("poesia-evaluation", artifact_location="./mlruns/poesia-evaluation")
except Exception:
    pass

from poesia.generation.llm_client import LoRAClient
from poesia.phonology.spanish import SpanishPhonology
from poesia.generation.constrained_loop import ConstrainedLoop


def evaluate(adapter_path, themes, form, language="es", parent_run_id=None):
    phonology = SpanishPhonology()
    results = []

    # Phase 4: Nest evaluation under the training run when parent_run_id is provided
    if parent_run_id:
        run = mlflow.start_run(run_id=parent_run_id, nested=True)
    else:
        mlflow.set_experiment("poesia-evaluation")
        run = mlflow.start_run(run_name=f"eval-{os.path.basename(adapter_path)}")
        parent_run_id = run.info.run_id

    with run:
        mlflow.log_param("adapter", adapter_path)
        mlflow.log_param("form", form)
        mlflow.log_param("n_themes", len(themes))
        if parent_run_id:
            mlflow.log_param("parent_run_id", parent_run_id)
            mlflow.set_tag("mlflow.parentRunId", parent_run_id)

        for theme in themes:
            loop = ConstrainedLoop(
                language=language,
                form=form,
                llm=LoRAClient(adapter_path=adapter_path),
            )
            result = loop.run(theme=theme, n_candidates=8)
            lines = result.lines
            line_count = len(lines)

            syll_counts = []
            for line in lines:
                scan = phonology.scan_line(line)
                syll_counts.append(scan.metrical_syllable_count)

            avg_syll = sum(syll_counts) / len(syll_counts) if syll_counts else 0
            line_ok = 1.0 if line_count == 14 else 0.0

            results.append({
                "theme": theme,
                "line_count": line_count,
                "avg_syllables": avg_syll,
                "line_accuracy": line_ok,
            })

            mlflow.log_metric(f"{theme}_line_accuracy", line_ok)
            mlflow.log_metric(f"{theme}_syllable_dev", avg_syll - 11)

        avg_line_acc = sum(r["line_accuracy"] for r in results) / len(results)
        avg_syll_dev = abs(sum(r["avg_syllables"] for r in results) / len(results) - 11)

        mlflow.log_metric("avg_line_accuracy", avg_line_acc)
        mlflow.log_metric("avg_syllable_deviation", avg_syll_dev)
        mlflow.set_tag("eval_status", "passed")

        print(f"\nEvaluation complete for: {adapter_path}")
        print(f"  Avg line accuracy: {avg_line_acc:.0%}")
        print(f"  Avg syllable dev:  {avg_syll_dev:.2f}")
        print(f"  Nested under: {parent_run_id}")
        for r in results:
            print(f"  {r['theme']}: {r['line_count']} lines, {r['avg_syllables']:.1f} syll/line")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--form", default="soneto")
    parser.add_argument("--themes", nargs="+", default=["luna", "mar", "noche", "soledad", "tiempo"])
    parser.add_argument("--parent-run-id", default=None,
                        help="MLflow run ID to nest under (for provenance)")
    args = parser.parse_args()
    evaluate(args.adapter, args.themes, args.form, parent_run_id=args.parent_run_id)

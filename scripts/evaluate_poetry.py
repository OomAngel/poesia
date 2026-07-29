"""Evaluate LoRA adapters using MLflow 3.x genai.evaluate API.

Uses custom scorers that wrap our LineScorer metrics (syllable accuracy,
rhyme, imagery) plus built-in MLflow scorers for fluency and correctness.

Usage:
    python scripts/evaluate_poetry.py --adapter models/poetry-lora-v2/final_adapter
"""

import argparse
import os

import mlflow
from mlflow.genai import scorer
from mlflow.genai.scorers import Fluency


# ── Custom scorers using our PoesIA evaluation tools ──────────────

@scorer(name="syllable_accuracy", aggregations=["mean"])
def syllable_accuracy(outputs) -> float:
    """Score 0-1: how many lines have correct syllable count (11)."""
    from poesia.phonology.spanish import SpanishPhonology
    phonology = SpanishPhonology()
    lines = [l.strip() for l in outputs.split("\n") if l.strip() and len(l.strip()) > 3]
    if not lines:
        return 0.0
    ok = 0
    for line in lines:
        try:
            scan = phonology.scan_line(line)
            if abs(scan.metrical_syllable_count - 11) <= 1:
                ok += 1
        except Exception:
            pass
    return ok / len(lines)


@scorer(name="line_count", aggregations=["mean"])
def line_count(outputs) -> float:
    """Score 0-1: 1.0 if exactly 14 lines (soneto constraint)."""
    lines = [l.strip() for l in outputs.split("\n") if l.strip() and len(l.strip()) > 3]
    return 1.0 if len(lines) == 14 else max(0.0, 1.0 - abs(14 - len(lines)) * 0.1)


@scorer(name="spanish_detected", aggregations=["mean"])
def spanish_detected(outputs) -> float:
    """Score 0-1: ratio of Spanish vs English words."""
    import re
    en_indicators = {"the", "and", "that", "with", "from", "your", "our",
                     "their", "this", "have", "will", "would", "could"}
    es_indicators = {"el", "la", "los", "las", "y", "que", "en", "de", "por",
                     "con", "un", "una", "su", "del", "no", "se", "le"}
    words = re.findall(r"[a-záéíóúüñ]+", outputs.lower())
    if not words:
        return 0.0
    en_count = sum(1 for w in words if w in en_indicators)
    es_count = sum(1 for w in words if w in es_indicators)
    total = en_count + es_count
    if total == 0:
        return 0.5
    return es_count / total


@scorer(name="imagery_present", aggregations=["mean"])
def imagery_present(outputs) -> int:
    """Count concrete nouns present (higher = more imagery)."""
    import re
    concrete = {"luna", "sol", "mar", "rio", "montaña", "piedra", "flor",
               "arbol", "nube", "lluvia", "viento", "fuego", "luz",
               "sombra", "estrella", "cielo", "agua", "tierra", "viento"}
    words = set(re.findall(r"[a-záéíóúüñ]+", outputs.lower()))
    # Normalize: 0-5 concrete nouns = 0, 6+ = 1
    found = len(words & concrete)
    return min(found, 10)


# ── Prediction function ─────────────────────────────────────────

def build_predict_fn(adapter_path: str):
    """Build a prediction function that uses the given LoRA adapter."""
    from poesia.generation.llm_client import LoRAClient
    from poesia.generation.constrained_loop import ConstrainedLoop

    client = LoRAClient(adapter_path=adapter_path)

    def predict(theme: str) -> str:
        """Generate a soneto for the given theme."""
        loop = ConstrainedLoop(
            language="es",
            form="soneto",
            llm=client,
        )
        result = loop.run(theme=theme, n_candidates=8)
        return "\n".join(result.lines)

    return predict


# ── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True, help="Path to LoRA adapter")
    parser.add_argument("--themes", nargs="+", default=["luna", "mar", "noche", "soledad", "tiempo"])
    args = parser.parse_args()

    # Set up MLflow
    mlflow.set_tracking_uri(os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db"))
    mlflow.set_experiment("poesia-evaluation")

    # Build eval dataset: list of dicts with "inputs" key
    eval_data = [{"inputs": {"theme": t}} for t in args.themes]

    # Build prediction function
    predict_fn = build_predict_fn(args.adapter)

    # Wrap to match the dataset format
    def predict_wrapper(theme: str) -> str:
        return predict_fn(theme)

    # Run evaluation with MLflow 3.x genai API
    results = mlflow.genai.evaluate(
        data=eval_data,
        predict_fn=predict_wrapper,
        scorers=[
            Fluency(),
            syllable_accuracy,
            line_count,
            spanish_detected,
            imagery_present,
        ],
        model=args.adapter,
    )

    print(f"\nEvaluation results for: {args.adapter}")
    for metric, score in results.metrics.items():
        if isinstance(score, float):
            print(f"  {metric}: {score:.3f}")
        else:
            print(f"  {metric}: {score}")


if __name__ == "__main__":
    main()

"""Compare base model vs fine-tuned model output quality.

Usage:
    python mlops/compare.py

Generates the same prompt with both models and scores the outputs.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from poesia.generation.llm_client import LoRAClient
from poesia.phonology.spanish import SpanishPhonology

TEST_THEMES = [
    "luna sobre el mar",
    "soledad del bosque",
    "primavera que vuelve",
    "el amor perdido",
]


def score_poem(lines: list[str], language: str = "es") -> dict:
    """Score a poem for formal validity."""
    if language == "es":
        phonology = SpanishPhonology()
    else:
        return {"error": "Only Spanish supported"}

    valid_lines = 0
    total_syllables = 0
    for line in lines:
        scan = phonology.scan_line(line)
        if scan.is_valid:
            valid_lines += 1
        total_syllables += scan.metrical_syllable_count

    return {
        "lines": len(lines),
        "valid_lines": valid_lines,
        "valid_pct": round(valid_lines / len(lines) * 100, 1) if lines else 0,
        "avg_syllables": round(total_syllables / len(lines), 1) if lines else 0,
    }


def main():
    print("=" * 60)
    print("Model Comparison: Base vs Fine-tuned")
    print("=" * 60)

    adapter_path = os.path.join(
        os.path.dirname(__file__), "..", "models", "poetry-lora-3b", "final_adapter"
    )

    if not os.path.exists(adapter_path):
        print(f"\n⚠ No adapter found at {adapter_path}")
        print("  Run 'python scripts/train_poetry_lora.py' first.")
        print("  Using base model only for now.\n")
        models = {"Base (Qwen 2.5 3B)": LoRAClient()}
    else:
        models = {
            "Base (Qwen 2.5 3B)": LoRAClient(adapter_path=None),
            "Fine-tuned": LoRAClient(adapter_path=adapter_path),
        }

    for theme in TEST_THEMES:
        print(f"\n{'─' * 60}")
        print(f"Theme: {theme}")
        print(f"{'─' * 60}")

        for name, client in models.items():
            prompt = f"Write a Spanish haiku about {theme}.\n"
            lines = client.generate(prompt, n=1, temperature=0.8)
            scores = score_poem(lines)

            print(f"\n  [{name}]")
            for line in lines:
                print(f"    {line}")
            print(f"    Valid: {scores['valid_pct']}%  Avg syllables: {scores['avg_syllables']}")


if __name__ == "__main__":
    main()

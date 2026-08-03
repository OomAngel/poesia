"""Evaluate a trained adapter by generating sample poems and scoring them.

Usage:
    python mlops/evaluate_adapter.py --adapter models/poetry-lora-v2/final_adapter
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from poesia.generation.llm_client import OutlinesClient
from poesia.phonology.spanish import SpanishPhonology

TEST_THEMES = ["luna", "mar", "sol", "noche", "amor"]


def evaluate(adapter_path: str) -> dict:
    client = OutlinesClient(adapter_path=adapter_path)
    client._load()
    phonology = SpanishPhonology()

    results = {"themes": {}}
    all_line_counts = []
    all_syllable_devs = []

    for theme in TEST_THEMES:
        prompt = f"Write a soneto in Spanish.\nSyllables per line: 11.\nRhyme scheme: ABBA ABBA CDC DCD.\nTheme: {theme}.\n\n"
        lines = []
        for i in range(14):
            line_prompt = f"{prompt}\nWrite line {i + 1} of 14.\n"
            result = client.generate(line_prompt, n=1, temperature=0.8)
            if result and result[0]:
                lines.append(result[0])

        # Score
        line_count = len(lines)
        all_line_counts.append(line_count)

        syll_devs = []
        for line in lines:
            scan = phonology.scan_line(line)
            syll_devs.append(abs(scan.metrical_syllable_count - 11))
        avg_dev = sum(syll_devs) / len(syll_devs) if syll_devs else 0
        all_syllable_devs.extend(syll_devs)

        results["themes"][theme] = {
            "lines": line_count,
            "target_lines": 14,
            "avg_syllable_deviation": round(avg_dev, 2),
            "output": lines[:4],  # first 4 lines as sample
        }

    results["summary"] = {
        "avg_line_count": round(sum(all_line_counts) / len(all_line_counts), 1),
        "avg_syllable_deviation": round(sum(all_syllable_devs) / len(all_syllable_devs), 2)
        if all_syllable_devs
        else 0,
        "line_count_accuracy": round(
            sum(1 for c in all_line_counts if c == 14) / len(all_line_counts), 3
        ),
    }
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True, help="Path to adapter directory")
    args = parser.parse_args()
    results = evaluate(args.adapter)
    print(json.dumps(results, indent=2, ensure_ascii=False))

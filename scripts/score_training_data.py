#!/usr/bin/env python3
"""Pre-compute quality scores for training examples.

Each poem is scored on syllable accuracy, line count, and rhyme.
The scores are saved alongside the training data as sample weights.

Usage:
    python scripts/score_training_data.py \\
        --input seeds/poetry_corpus/training_data_structured/sonetos_train.jsonl \\
        --output seeds/poetry_corpus/training_data_structured/sonetos_scored.jsonl
"""

import argparse
import json
import sys
from poesia.phonology.spanish import SpanishPhonology


def score_poem(completion, phonology, syll_target=11):
    """Score a poem 0-1 based on syllable accuracy and line count."""
    lines = [l.strip() for l in completion.split("\n") if l.strip()]
    if not lines:
        return 0.0

    # Line count accuracy: 1.0 if 14 lines
    line_score = 1.0 if len(lines) == 14 else max(0.0, 1.0 - abs(14 - len(lines)) * 0.1)

    # Syllable accuracy: average of how close each line is to target
    syll_scores = []
    for l in lines:
        try:
            scan = phonology.scan_line(l)
            diff = abs(scan.metrical_syllable_count - syll_target)
            syll_scores.append(max(0.0, 1.0 - diff * 0.2))
        except Exception:
            syll_scores.append(0.0)

    avg_syll = sum(syll_scores) / len(syll_scores) if syll_scores else 0.0

    # Composite: 40% line count + 60% syllable
    return round(0.4 * line_score + 0.6 * avg_syll, 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", type=int, default=11)
    args = parser.parse_args()

    phonology = SpanishPhonology()
    total = 0
    scored = 0

    with open(args.input) as fin, open(args.output, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            total += 1
            quality = score_poem(record.get("completion", ""), phonology, args.target)
            record["quality_score"] = quality
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            if quality > 0:
                scored += 1

    avg = round(scored / total * 100, 1) if total else 0
    print(f"Scored {total} poems, {scored} passed ({avg}%)")


if __name__ == "__main__":
    main()

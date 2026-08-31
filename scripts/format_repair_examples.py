#!/usr/bin/env python3
"""Format harvested repair pairs (real, from RepairDatasetHook, and synthetic,
from generate_synthetic_repair_pairs.py) into prompt/completion pairs ready
for fine-tuning — using the EXACT prompt template LoRAClient.repair() sends
at inference time (src/poesia/generation/llm_client.py), so the fine-tune
sees the same input distribution it will be asked to handle. Closing this
prompt-format gap is the whole point (docs/GENERATION_QUALITY_PLAN.md):
without it, more repair data wouldn't help, since the model would still be
trained on a different task shape than the one it's evaluated on.

Only resolved=True attempts are kept — an unresolved attempt has no
correct completion to train on.

Usage:
    python scripts/format_repair_examples.py [--output PATH]
    python scripts/format_repair_examples.py --split \\
        --train-output mlops/data/train_repair.jsonl \\
        --eval-output mlops/data/eval_repair.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random

from poesia.generation.llm_client import LORA_REPAIR_PROMPT_TEMPLATE

INPUT_PATHS = [
    "seeds/poetry_corpus/repair_examples/repair_log.jsonl",
    "seeds/poetry_corpus/repair_examples/synthetic_repair_pairs.jsonl",
]
DEFAULT_OUTPUT = "seeds/poetry_corpus/repair_examples/repair_finetune.jsonl"


def format_record(record: dict) -> dict | None:
    if not record.get("resolved"):
        return None
    before = record.get("before")
    after = record.get("after")
    defect_description = record.get("defect_description")
    if not before or not after or not defect_description:
        return None
    prompt = LORA_REPAIR_PROMPT_TEMPLATE.format(defect_description=defect_description, line=before)
    return {"prompt": prompt, "completion": after.strip()}


def split_train_eval(
    records: list[dict], eval_ratio: float, seed: int
) -> tuple[list[dict], list[dict]]:
    """Shuffle deterministically and split off an eval slice. Returns
    (train, eval); eval always gets at least 1 record if records is non-empty."""
    rng = random.Random(seed)
    shuffled = list(records)
    rng.shuffle(shuffled)
    n_eval = max(1, int(len(shuffled) * eval_ratio)) if shuffled else 0
    return shuffled[n_eval:], shuffled[:n_eval]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--split",
        action="store_true",
        help="Also write a shuffled train/eval split (for fine-tune configs).",
    )
    parser.add_argument("--train-output", default="mlops/data/train_repair.jsonl")
    parser.add_argument("--eval-output", default="mlops/data/eval_repair.jsonl")
    parser.add_argument("--eval-ratio", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    formatted = []
    seen_prompts: set[str] = set()
    for path in INPUT_PATHS:
        if not os.path.exists(path):
            print(f"[skip] {path} not found")
            continue
        n_read = 0
        n_kept = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n_read += 1
                record = json.loads(line)
                out = format_record(record)
                if out is None:
                    continue
                if out["prompt"] in seen_prompts:
                    continue
                seen_prompts.add(out["prompt"])
                formatted.append(out)
                n_kept += 1
        print(f"{path}: read {n_read}, kept {n_kept}")

    with open(args.output, "w", encoding="utf-8") as f:
        for record in formatted:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(formatted)} fine-tune-ready repair examples to {args.output}")

    if args.split:
        train_examples, eval_examples = split_train_eval(formatted, args.eval_ratio, args.seed)

        os.makedirs(os.path.dirname(args.train_output), exist_ok=True)
        with open(args.train_output, "w", encoding="utf-8") as f:
            for record in train_examples:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        with open(args.eval_output, "w", encoding="utf-8") as f:
            for record in eval_examples:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Train: {len(train_examples)} -> {args.train_output}")
        print(f"Eval:  {len(eval_examples)} -> {args.eval_output}")


if __name__ == "__main__":
    main()

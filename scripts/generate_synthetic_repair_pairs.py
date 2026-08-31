#!/usr/bin/env python3
"""Generate synthetic defect->fix repair pairs from real, already-valid poem
lines, using the same phonology backend and defect-description builders the
live repair loop uses (poesia.generation.constrained_loop) — so these
examples land in the exact same shape as RepairDatasetHook's organically
harvested ones (see docs/GENERATION_QUALITY_PLAN.md for why that shape
matters: the fine-tune was never trained on the defect->fix task at all).

For each source line: treat it as already-correct (its own scan is the
"target"), then mechanically corrupt it in one of two ways:
  - metre: drop or insert a word to shift the syllable count
  - rhyme: replace the last word with one that breaks the rhyme

The corrupted line is "before", the untouched original is "after", and the
defect_description is built with the loop's own
_repair_defect_description/_rhyme_defect_parts so the wording matches what
the model sees at real repair time.

Usage:
    python scripts/generate_synthetic_repair_pairs.py [--limit N] [--seed N]
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import re

from poesia.generation.constrained_loop import _last_word, _rhyme_defect_parts
from poesia.phonology.spanish import SpanishPhonology

CORPUS_GLOB = "seeds/poetry_corpus/training_data_structured/*.jsonl"
OUTPUT_PATH = "seeds/poetry_corpus/repair_examples/synthetic_repair_pairs.jsonl"

FILLER_WORDS = ["muy", "ya", "tan", "más", "así", "aún"]
# Common Spanish words spanning a range of endings/stresses, used as
# rhyme-breaking replacements — deliberately unrelated to poetic register so
# they reliably land on a different rhyme_key than the line they replace.
WRONG_RHYME_WORDS = [
    "computadora",
    "problema",
    "ventana",
    "martillo",
    "azul",
    "efectivo",
    "reunión",
    "objeto",
    "sistema",
    "camino",
]


def _metre_defect_description(actual_syllables: int, target_syllables: int) -> str:
    return f"the line has {actual_syllables} syllables but must be exactly {target_syllables}"


def corrupt_syllables(
    phonology: SpanishPhonology, line: str, target_syllables: int, rng: random.Random
) -> tuple[str, int] | None:
    """Drop or insert a word to change the syllable count. None if it didn't
    actually change (e.g. dropped word happened to be metrically silent)."""
    words = line.split()
    if len(words) < 3:
        return None
    corrupted = list(words)
    if rng.random() < 0.5 and len(corrupted) > 3:
        idx = rng.randrange(0, len(corrupted) - 1)
        del corrupted[idx]
    else:
        idx = rng.randrange(1, len(corrupted))
        corrupted.insert(idx, rng.choice(FILLER_WORDS))
    corrupted_line = " ".join(corrupted)
    scan = phonology.scan_line(corrupted_line)
    if not scan.is_valid or scan.metrical_syllable_count == target_syllables:
        return None
    return corrupted_line, scan.metrical_syllable_count


def corrupt_rhyme(
    phonology: SpanishPhonology, line: str, target_rhyme_key: str, rng: random.Random
) -> tuple[str, str] | None:
    """Replace the last word with one that breaks the rhyme. Returns
    (corrupted_line, original_last_word) — the original last word becomes
    the example_word a real repair-loop call would supply, since it's a
    genuine rhyme-group member."""
    words = line.split()
    if not words:
        return None
    original_last = _last_word(line)
    candidates = list(WRONG_RHYME_WORDS)
    rng.shuffle(candidates)
    for candidate in candidates:
        test_line = " ".join(words[:-1] + [candidate])
        rk = phonology.rhyme_key(test_line).consonant
        if rk and rk != target_rhyme_key:
            return test_line, original_last
    return None


# Several gutenberg_*.jsonl corpus files have Project Gutenberg's English
# legal boilerplate leaking into the "completion" field alongside the actual
# poem (a pre-existing corpus contamination bug, not introduced here — see
# the flag raised in conversation). These are the tell-tale English function
# words that never legitimately appear in a Spanish verse line.
_BOILERPLATE_RE = re.compile(
    r"\b(the|and|shall|agreement|foundation|copyright|license|compliance|gutenberg|"
    r"disclaimer|trademark|indemnify)\b",
    re.IGNORECASE,
)


def extract_lines(corpus_glob: str) -> list[str]:
    lines: list[str] = []
    for path in sorted(glob.glob(corpus_glob)):
        with open(path, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                completion = record.get("completion", "")
                for line in completion.splitlines():
                    line = line.strip()
                    # Skip blank lines and anything too short to be a real verse line
                    if len(re.sub(r"[^\wáéíóúñü]", "", line, flags=re.IGNORECASE)) < 8:
                        continue
                    if _BOILERPLATE_RE.search(line):
                        continue
                    lines.append(line)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000, help="Max source lines to sample.")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    phonology = SpanishPhonology()

    lines = extract_lines(CORPUS_GLOB)
    rng.shuffle(lines)
    lines = lines[: args.limit]
    print(f"Sampled {len(lines)} source lines from {CORPUS_GLOB}")

    records = []
    for line in lines:
        scan = phonology.scan_line(line)
        if not scan.is_valid:
            continue
        target_syllables = scan.metrical_syllable_count
        target_rhyme_key = phonology.rhyme_key(line).consonant

        metre_result = corrupt_syllables(phonology, line, target_syllables, rng)
        if metre_result is not None:
            corrupted_line, actual_syllables = metre_result
            records.append(
                {
                    "before": corrupted_line,
                    "defect_description": _metre_defect_description(
                        actual_syllables, target_syllables
                    ),
                    "after": line,
                    "resolved": True,
                    "target_syllables": target_syllables,
                    "target_rhyme_key": None,
                    "attempt": 1,
                    "source": "synthetic",
                }
            )

        if target_rhyme_key:
            rhyme_result = corrupt_rhyme(phonology, line, target_rhyme_key, rng)
            if rhyme_result is not None:
                corrupted_line, example_word = rhyme_result
                defect_description = "; ".join(_rhyme_defect_parts(target_rhyme_key, example_word))
                records.append(
                    {
                        "before": corrupted_line,
                        "defect_description": defect_description,
                        "after": line,
                        "resolved": True,
                        "target_syllables": target_syllables,
                        "target_rhyme_key": target_rhyme_key,
                        "attempt": 1,
                        "source": "synthetic",
                    }
                )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} synthetic repair pairs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

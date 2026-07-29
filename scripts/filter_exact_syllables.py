#!/usr/bin/env python3
"""Filter training poems to those with syllable counts close to target.

Usage:
    # Exact match (all lines must match target exactly)
    python scripts/filter_exact_syllables.py \
        --input data.jsonl --output exact.jsonl --target 11

    # Tolerance: allow up to 2 lines off-target
    python scripts/filter_exact_syllables.py \
        --input data.jsonl --output close.jsonl --target 11 --max-off 2

    # Report only (no output file) — shows distribution
    python scripts/filter_exact_syllables.py \
        --input data.jsonl --target 11 --report-only

Given a JSONL dataset of structured poems, each record has:
    {"prompt": "...", "completion": "line1\\nline2\\n..."}

The script:
1. Extracts the completion text
2. Splits into lines (ignoring blank lines)
3. Counts syllables per line using phonology backend
4. Filters by configurable tolerance
"""

import json
import sys
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filter training poems by syllable count accuracy"
    )
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", default=None, help="Output JSONL file (omit for report-only)")
    parser.add_argument(
        "--target", type=int, default=11,
        help="Target syllable count per line (default: 11)",
    )
    parser.add_argument(
        "--max-off", type=int, default=0,
        help="Max lines allowed off-target (0 = exact match, default: 0)",
    )
    parser.add_argument(
        "--language", default="es",
        help="Language code for phonology backend (default: es)",
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="Print distribution stats without writing output",
    )
    args = parser.parse_args()

    # Load phonology backend
    if args.language == "es":
        from poesia.phonology.spanish import SpanishPhonology
        phonology = SpanishPhonology()
        lang_name = "Spanish"
    elif args.language == "en":
        from poesia.phonology.english import EnglishPhonology
        phonology = EnglishPhonology()
        lang_name = "English"
    else:
        print(f"Unsupported language: {args.language}")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    total = 0
    kept = 0
    off_line_counts: dict[int, int] = {}
    total_lines_scanned = 0
    total_off_lines = 0

    with open(input_path) as fin:
        fout = open(args.output, "w") if args.output and not args.report_only else None
        try:
            for line_num, line in enumerate(fin, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Warning: skipping invalid JSON on line {line_num}")
                    continue

                total += 1
                completion = record.get("completion", "")
                poem_lines = [
                    l.strip()
                    for l in completion.split("\n")
                    if l.strip() and not l.strip().startswith("\\n")
                ]

                if not poem_lines:
                    continue

                off_count = 0
                for pl in poem_lines:
                    try:
                        scan = phonology.scan_line(pl)
                        if scan.metrical_syllable_count != args.target:
                            off_count += 1
                    except Exception:
                        off_count += 1

                total_lines_scanned += len(poem_lines)
                total_off_lines += off_count
                off_line_counts[off_count] = off_line_counts.get(off_count, 0) + 1

                if off_count <= args.max_off:
                    if fout:
                        fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                    kept += 1
        finally:
            if fout:
                fout.close()

    avg_dev = total_off_lines / total if total > 0 else 0.0
    avg_lines = total_lines_scanned / total if total > 0 else 0.0

    print(f"\n=== Syllable filter results ===")
    print(f"Input:    {input_path}")
    if args.output:
        print(f"Output:   {args.output}")
    print(f"Target:   {args.target} syllables per line ({lang_name})")
    print(f"Max off:  {args.max_off} line(s) allowed off-target")
    print(f"Total:    {total} poems, {total_lines_scanned} lines ({avg_lines:.1f} avg/poem)")
    print(f"Kept:     {kept} poems ({kept/total*100:.1f}%)")
    print(f"Avg dev:  {avg_dev:.2f} lines off-target per poem")
    print(f"\nDistribution of off-target lines per poem:")
    max_count = max(off_line_counts.values()) if off_line_counts else 1
    for off_n in sorted(off_line_counts.keys()):
        bar_len = max(1, int(off_line_counts[off_n] / max_count * 40))
        bar = "█" * bar_len
        pct = off_line_counts[off_n] / total * 100
        if off_n <= args.max_off:
            cumul = sum(v for k, v in off_line_counts.items() if k <= off_n)
            print(f"  {off_n:2d} off: {off_line_counts[off_n]:4d} poems ({pct:4.1f}%)  {bar}  (cumulative kept: {cumul})")
        else:
            print(f"  {off_n:2d} off: {off_line_counts[off_n]:4d} poems ({pct:4.1f}%)  {bar}")


if __name__ == "__main__":
    main()

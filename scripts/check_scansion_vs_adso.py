#!/usr/bin/env python3
"""Check the Spanish syllable counter against hand-scanned gold (ADSO, 100 sonnets).

Every evaluation score in this repo (syllable deviation, metre pass rate) is computed by
`SpanishPhonology.scan_line`. This measures how often that counter agrees with expert
scansion, so an adapter score can be read against the counter's own error rate
(docs/RETRAINING_PLAN_2026-10.md §6 step 2).

Gold: seeds/poetry_corpus/eval_gold/adso_gold_100.jsonl (`metre`: one '+'/'-' string per
line, one character per metrical syllable). Reports exact agreement, off-by-one, larger
errors, and the signed bias, overall and as a table of (gold, counted) pairs.

Usage:
    python scripts/check_scansion_vs_adso.py
    python scripts/check_scansion_vs_adso.py --show 10   # print 10 disagreeing lines
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from poesia.phonology.spanish import SpanishPhonology

GOLD = Path("seeds/poetry_corpus/eval_gold/adso_gold_100.jsonl")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gold", type=Path, default=GOLD)
    ap.add_argument("--show", type=int, default=0, help="print N disagreeing lines")
    args = ap.parse_args()

    phon = SpanishPhonology()
    pairs: list[tuple[int, int, str]] = []
    for line in args.gold.open(encoding="utf-8"):
        rec = json.loads(line)
        verse_lines = [v for v in rec["completion"].split("\n") if v.strip()]
        for verse, met in zip(verse_lines, rec.get("metre", []), strict=False):
            if not met:
                continue
            gold = len(met.replace("|", ""))
            counted = phon.scan_line(verse).metrical_syllable_count
            pairs.append((gold, counted, verse))

    n = len(pairs)
    diffs = [c - g for g, c, _ in pairs]
    exact = sum(d == 0 for d in diffs)
    off1 = sum(abs(d) == 1 for d in diffs)
    print(f"lines scanned: {n} (gold: {args.gold})")
    print(f"exact agreement: {exact} ({exact / n:.1%})")
    print(f"off by one:      {off1} ({off1 / n:.1%})")
    print(f"off by 2+:       {n - exact - off1} ({(n - exact - off1) / n:.1%})")
    print(f"mean signed error (counted - gold): {sum(diffs) / n:+.2f}")
    print(f"mean absolute error: {sum(abs(d) for d in diffs) / n:.2f}")
    print("most common (gold, counted):", Counter((g, c) for g, c, _ in pairs).most_common(6))
    for g, c, verse in [p for p in pairs if p[0] != p[1]][: args.show]:
        print(f"  gold {g:2d} counted {c:2d}  {verse}")


if __name__ == "__main__":
    main()

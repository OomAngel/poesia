#!/usr/bin/env python3
"""Rescan stored Spanish benchmark poems with the corrected metre counter (2026-10-13).

Until ``phonology/spanish_metre.py`` the Spanish counter joined vowels after a final -n/-s
("los ojos" as 4 syllables) and matched ADSO's hand scansion on 59.3% of lines (now 93.5%).
Every Spanish metre figure measured before then (report §5) used the old counter, both to score
and, inside the loop, to choose lines. This rescans the stored lines (no model calls) and prints
old and new figures per file: exact-metre share and mean syllables off per line (target 11).

    python scripts/rescore_spanish_metre.py reports/eval_2026-10/*.json --out reports/eval_2026-10/b14-spanish-rescore.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from poesia.phonology.spanish import SpanishPhonology


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--target", type=int, default=11)
    ap.add_argument("--out")
    args = ap.parse_args()
    phon = SpanishPhonology()
    rows = []
    for f in sorted(args.files):
        try:
            d = json.load(open(f, encoding="utf-8"))
            poems = d["languages"]["es"]["poems"]
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        old = [s for p in poems for s in p.get("syllables", [])]
        lines = [ln for p in poems for ln in p["lines"] if ln.strip()]
        new = [phon.scan_line(ln).metrical_syllable_count for ln in lines]

        def stats(counts):
            n = max(len(counts), 1)
            return (
                round(sum(c == args.target for c in counts) / n, 3),
                round(sum(abs(c - args.target) for c in counts) / n, 2),
            )

        o, nw = stats(old), stats(new)
        rows.append(
            {
                "file": Path(f).name,
                "poems": len(poems),
                "lines": len(lines),
                "old_metre": o[0],
                "old_off": o[1],
                "new_metre": nw[0],
                "new_off": nw[1],
            }
        )
        print(
            f"{Path(f).name:45} {len(poems):3} poems  metre {o[0]:.0%} -> {nw[0]:.0%}   off/line {o[1]} -> {nw[1]}",
            flush=True,
        )
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

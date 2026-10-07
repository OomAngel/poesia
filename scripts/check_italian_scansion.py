#!/usr/bin/env python3
"""Italian counter vs expert-annotated endecasillabi (Biblioteca Italiana via Averell 10).

Every annotated line is an endecasillabo (11 positions, last stress on the 10th), with its
stress pattern (``---+-+--++-``). Reports exact-count agreement, mean error, and how often
the counter puts a stress on position 10.

    python scripts/check_italian_scansion.py [--dir data/external/averell/biblioteca_italiana-master/json]
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from poesia.phonology.base import Stress
from poesia.phonology.italian import ItalianPhonology


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default="data/external/averell/biblioteca_italiana-master/json")
    ap.add_argument("--show", type=int, default=8, help="print this many disagreements")
    args = ap.parse_args()
    phon = ItalianPhonology()
    by_author: dict[str, list[int]] = collections.defaultdict(list)
    tenth = total = 0
    misses = []
    for path in sorted(Path(args.dir).glob("*.json")):
        for poem in json.loads(path.read_text(encoding="utf-8")):
            for stanza in poem.get("text", []):
                for v in stanza:
                    gold = v.get("metrical_pattern")
                    if not gold:
                        continue
                    scan = phon.scan_line(v["verse"])
                    err = scan.metrical_syllable_count - len(gold)
                    by_author[poem["author"]].append(err)
                    total += 1
                    tenth += (
                        len(scan.stress_pattern) >= 10 and scan.stress_pattern[9] is Stress.PRIMARY
                    )
                    if err and len(misses) < args.show:
                        misses.append((v["verse"], scan.metrical_syllable_count, len(gold)))
    errs = [e for es in by_author.values() for e in es]
    print(
        f"lines {total}: exact {sum(e == 0 for e in errs) / total:.1%}, "
        f"mean |error| {sum(abs(e) for e in errs) / total:.2f}, "
        f"mean error {sum(errs) / total:+.2f}, stress on 10th {tenth / total:.1%}"
    )
    for author, es in by_author.items():
        print(f"  {author}: {len(es)} lines, exact {sum(e == 0 for e in es) / len(es):.1%}")
    hist = collections.Counter(errs)
    print("  error histogram:", dict(sorted(hist.items())))
    for verse, got, want in misses:
        print(f"  {got:>2}/{want}  {verse}")


if __name__ == "__main__":
    main()

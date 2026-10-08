#!/usr/bin/env python3
"""Check the French scanner against Métrique en Ligne (Averell corpus 9).

Every verse there carries the metre experts assigned (``12`` written ``6+6``, ``10`` as
``4+6``, ``8``). This counts how often the scanner's syllable count equals it, overall and
per metre, and lists the most frequent miss patterns for the next fix.

    python scripts/check_french_scansion.py [--limit N] [--show 20]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

from poesia.phonology.french import FrenchPhonology

GOLD = Path("data/external/averell/metrique-en-ligne-master/json")


def _metre(raw: str) -> int | None:
    parts = re.split(r"[+−-]", raw)
    if not all(p.isdigit() for p in parts):
        return None
    return sum(int(p) for p in parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()
    ph = FrenchPhonology()
    n = exact = 0
    err = collections.Counter()
    per = collections.defaultdict(lambda: [0, 0])
    misses = []
    for path in sorted(GOLD.glob("*.json")):
        for poem in json.loads(path.read_text(encoding="utf-8")):
            for stanza in poem.get("text", []):
                for v in stanza:
                    gold = _metre(v.get("metre", ""))
                    if gold is None:
                        continue
                    got = ph.scan_line(v["verse"]).metrical_syllable_count
                    n += 1
                    per[gold][0] += 1
                    err[got - gold] += 1
                    if got == gold:
                        exact += 1
                        per[gold][1] += 1
                    elif len(misses) < 20000:
                        misses.append((got - gold, v["verse"]))
                    if args.limit and n >= args.limit:
                        break
    print(f"verses {n}; exact {exact / n:.1%}; error distribution {sorted(err.items())}")
    for m, (tot, ok) in sorted(per.items(), key=lambda x: -x[1][0])[:6]:
        print(f"  metre {m}: {ok / tot:.1%} of {tot}")
    for d, line in misses[: args.show]:
        print(f"  {d:+d}  {line}")


if __name__ == "__main__":
    main()

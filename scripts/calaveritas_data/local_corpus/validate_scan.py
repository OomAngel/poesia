"""Check SpanishPhonology.scan_line against gold metrical syllable counts (read-only).

Gold = len(metre string) per line in the Golden-Age corpora (Navarro-Colorado annotation,
one '+'/'-' per metrical syllable). lirica_siglo_de_oro has octosyllabic romances/redondillas;
sonetos_siglo_de_oro is hendecasyllabic. Usage: python validate_scan.py
"""

import json
import random
import sys
from collections import Counter

sys.path.insert(0, "/home/angel/dev/poesia/src")
from poesia.phonology.spanish import SpanishPhonology

P = SpanishPhonology()
BASE = "/home/angel/dev/poesia/seeds/poetry_corpus/training_data_structured/"


def pairs(fname):
    for l in open(BASE + fname, encoding="utf-8"):
        r = json.loads(l)
        lines = [x for x in r["completion"].split("\n") if x.strip()]
        m = r.get("metre") or []
        if len(lines) == len(m):
            for a, b in zip(lines, m):
                # sonetos: '+-' string, one char per syllable; lirica: '1|-|-|4|-|' items
                yield a, (len([x for x in b.split("|") if x != ""]) if "|" in b else len(b))


random.seed(0)
for fname in ("lirica_siglo_de_oro.jsonl", "sonetos_siglo_de_oro.jsonl"):
    allp = list(pairs(fname))
    samp = random.sample(allp, min(3000, len(allp)))
    diff = Counter()
    gold8 = [p for p in samp if p[1] == 8]
    for line, g in samp:
        diff[P.scan_line(line).metrical_syllable_count - g] += 1
    n = len(samp)
    print(
        fname,
        "lines sampled",
        n,
        "of",
        len(allp),
        "| gold-length distribution top:",
        Counter(g for _, g in samp).most_common(4),
    )
    print("  engine-minus-gold:", sorted(diff.items()))
    print(f"  exact {diff[0] / n:.3f}  within±1 {(diff[-1] + diff[0] + diff[1]) / n:.3f}")
    if gold8:
        hit = sum(1 for l, _ in gold8 if P.scan_line(l).metrical_syllable_count == 8)
        hit1 = sum(1 for l, _ in gold8 if abs(P.scan_line(l).metrical_syllable_count - 8) <= 1)
        print(
            f"  gold-octosyllables: n={len(gold8)} engine==8 {hit / len(gold8):.3f}  engine 7-9 {hit1 / len(gold8):.3f}"
        )

#!/usr/bin/env python3
"""Check the German scanner against the expert-annotated lines of Haider et al.

``data/external/metrical-tagging`` (tnhaider/metrical-tagging-in-the-wild), German small gold:
each line carries its metre as a pattern of unstressed (-) and stressed (+) syllables and its
stanza's rhyme scheme. Reported: exact syllable count; for words of two or more syllables,
how often the scanner's stressed syllable falls on a ``+`` (lines with the right count only);
and, within each stanza, how often lines sharing a rhyme letter share a rhyme key and lines
with different letters do not.

    python scripts/check_german_scansion.py [--show 20]
"""

from __future__ import annotations

import argparse
import collections
import csv
from pathlib import Path

from poesia.phonology.base import Stress
from poesia.phonology.german import GermanPhonology, _tokens, _word_marks

GOLD = Path(
    "data/external/metrical-tagging/data/German/SmallGold/antikoerperchen.lines.prosody.emotions.v4.tsv"
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()
    ph = GermanPhonology()
    rows = list(csv.DictReader(GOLD.open(encoding="utf-8"), delimiter="\t"))
    n = exact = 0
    err: collections.Counter[int] = collections.Counter()
    stress_ok = stress_n = 0
    misses = []
    stanzas = collections.defaultdict(list)
    for r in rows:
        meter = r["meter"].strip()
        if not meter or set(meter) - {"-", "+"}:
            continue
        line = r["line_text"]
        got = len(ph.scan_line(line).stress_pattern)  # every syllable, as the gold pattern
        n += 1
        err[got - len(meter)] += 1
        if got == len(meter):
            exact += 1
            pos = 0
            for word in _tokens(line):
                marks = _word_marks(word)
                if len(marks) > 1:
                    k = marks.index(Stress.PRIMARY)
                    stress_n += 1
                    stress_ok += meter[pos + k] == "+"
                pos += len(marks)
        else:
            misses.append((got - len(meter), line, meter))
        schema = r.get("rhyme_schema", "").strip()
        idx = int(r["id_line_in_stanza"]) - 1
        if schema and idx < len(schema):
            stanzas[(r["poem_id"], r["stanza_id"])].append(
                (schema[idx], ph.rhyme_key(line).consonant)
            )
    same = same_ok = diff = diff_ok = 0
    for lines in stanzas.values():
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                if lines[i][0] == lines[j][0]:
                    same += 1
                    same_ok += lines[i][1] == lines[j][1]
                else:
                    diff += 1
                    diff_ok += lines[i][1] != lines[j][1]
    print(f"lines {n}; exact syllables {exact / n:.1%}; error distribution {sorted(err.items())}")
    print(
        f"word stress on a + (polysyllables, lines counted right): {stress_ok / max(stress_n, 1):.1%} of {stress_n}"
    )
    print(
        f"rhyme: same letter -> same key {same_ok / max(same, 1):.1%} of {same}; different -> different {diff_ok / max(diff, 1):.1%} of {diff}"
    )
    for d, line, meter in misses[: args.show]:
        print(f"  {d:+d}  {line}   {meter}")


if __name__ == "__main__":
    main()

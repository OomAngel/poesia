"""Count the faults blind round 6 found (2026-11-07) in a review batch: filler, words that are not Mexican Spanish, made-up and prosaic words, lines outside 7-9 syllables,
invented "don X" names, poems without the person's name, poems where Death never appears,
"encaje" (the stock costume), and the share of lines with a ¡qué ...! exclamation.

Usage: python scripts/calaveritas_data/fault_counts.py BATCH.jsonl [BATCH2.jsonl ...] [--lang es]
Counts only, no poem text.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from poesia.calaveritas import quality
from poesia.calaveritas.prompt import PLACEHOLDER


def counts(path: str, lang: str) -> dict:
    recs = [json.loads(x) for x in Path(path).open()]
    recs = [r for r in recs if r["request"]["language"] == lang]
    ok = [r for r in recs if "poem" in r]
    c = dict.fromkeys(
        [
            "filler",
            "not_mexican",
            "made_up",
            "prosaic",
            "out_7_9",
            "invented_name",
            "no_name",
            "no_death",
            "encaje",
        ],
        0,
    )
    lines = 0
    for r in ok:
        name = r["request"]["name"]
        st = [s["lines"] for s in r["poem"]["stanzas"]]
        flat = [x for s in st for x in s]
        lines += len(flat)
        c["filler"] += sum(bool(quality.filler(x)) for x in flat)
        c["not_mexican"] += sum(bool(quality.not_mexican(x)) for x in flat)
        allowed = frozenset(
            w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]+", name + " " + r["request"]["detail"])
        )
        c["made_up"] += sum(bool(quality.made_up(x, allowed)) for x in flat)
        c["prosaic"] += sum(bool(quality.prosaic(x)) for x in flat)
        c["out_7_9"] += sum(not 7 <= n <= 9 for s in r["poem"]["stanzas"] for n in s["syllables"])
        c["invented_name"] += any(quality.invented_name(x, name) for x in flat)
        c["no_name"] += not quality.names_person(flat, name, PLACEHOLDER)
        c["no_death"] += not quality.has_death(flat)
        c["encaje"] += any(re.search(r"\bencaje", x, re.I) for x in flat)
    return {"poems": f"{len(ok)}/{len(recs)}", "lines": lines, **c}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("batches", nargs="+")
    ap.add_argument("--lang", default="es")
    args = ap.parse_args()
    print("lines with filler / not Mexican Spanish / made-up word / prosaic word / outside 7-9 "
          "syllables; poems with invented name / no name / no Death / encaje")  # fmt: skip
    for b in args.batches:
        print(Path(b).name, counts(b, args.lang))


if __name__ == "__main__":
    main()

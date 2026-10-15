#!/usr/bin/env python3
"""Share of lines a judge calls sense, for two or more benchmark runs (same judge, same sample size).

Uses the one-word verdict of ``sense_judge_validation.py`` (Apertus 70B: real lines pass 90%,
shuffled 8% in Spanish), which can reject broken lines but not rank good ones; Italian is left out
by default because the judge rejects 40% of real Italian lines.

    python scripts/sense_compare.py --runs plain=reports/.../plain-s*-{lang}.json \\
        lora=reports/.../lora-s*-{lang}.json --out reports/eval_2026-10/b22-sense-adapter-v3.json
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _judge():
    spec = importlib.util.spec_from_file_location(
        "sj", Path(__file__).with_name("sense_judge_validation.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.passes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", nargs="+", required=True, help="name=glob with {lang}")
    ap.add_argument("--languages", nargs="+", default=["es", "de", "fr"])
    ap.add_argument("--judge", default="swiss-ai/Apertus-v1.5-70B")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    passes = _judge()
    out = {}
    for lang in args.languages:
        for spec in args.runs:
            name, pattern = spec.split("=", 1)
            lines = [
                ln
                for f in sorted(glob.glob(pattern.replace("{lang}", lang)))
                for p in json.load(open(f, encoding="utf-8"))["languages"][lang]["poems"]
                for ln in p["lines"]
                if ln.strip()
            ]
            random.Random(0).shuffle(lines)
            sample = lines[: args.n]
            with ThreadPoolExecutor(12) as pool:
                got = [
                    g
                    for g in pool.map(
                        lambda ln, la=lang: passes(args.judge, "verdict", la, ln), sample
                    )
                    if g is not None
                ]
            res = {
                "n": len(sample),
                "answered": len(got),
                "sense": round(sum(got) / max(len(got), 1), 3),
            }
            out[f"{lang}|{name}"] = res
            print(lang, name, res, flush=True)
            Path(args.out).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()

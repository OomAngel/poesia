#!/usr/bin/env python3
"""Grammar score of benchmark poems: the share of lines a teacher leaves unchanged when asked
to correct them.

Metre, rhyme and language are counted by the engine; grammar and sense are not, and the 8B's
lines show errors there ("der weite Meer"). This asks the teacher (Apertus 70B, through an
OpenAI-compatible endpoint) the correct-and-compare question of ``distill_line_data.py`` for a
fixed, seeded sample of lines per language, so two runs (plain model, adapter) are scored on
lines drawn the same way. Lines in another language are skipped (counted separately).

    LLM_BASE_URL=http://127.0.0.1:8790/v1 LLM_NAME=swiss-ai/Apertus-v1.5-70B LLM_API_KEY=x \\
        python scripts/grammar_score.py reports/eval_2026-10/b10-cscs-8B-langrule-s*-de.json \\
        --language de --sample 150
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _distill():
    spec = importlib.util.spec_from_file_location(
        "distill", Path(__file__).with_name("distill_line_data.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reports", nargs="+")
    ap.add_argument("--language", required=True)
    ap.add_argument("--sample", type=int, default=150)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    from poesia.webapp import guess_language

    lines = [
        line
        for f in sorted(args.reports)
        for p in json.load(open(f, encoding="utf-8"))["languages"][args.language]["poems"]
        for line in p["lines"]
        if line.strip()
    ]
    other = [ln for ln in lines if guess_language(ln) not in (None, args.language)]
    own = [ln for ln in lines if ln not in other]
    sample = random.Random(args.seed).sample(own, min(args.sample, len(own)))
    check = _distill()._unchanged_by_correction
    with ThreadPoolExecutor(args.workers) as pool:
        ok = list(pool.map(lambda ln: check(args.language, ln), sample))
    result = {
        "language": args.language,
        "reports": sorted(args.reports),
        "lines": len(lines),
        "other_language": len(other),
        "sample": len(sample),
        "unchanged": sum(ok),
        "grammar_score": round(100 * sum(ok) / max(len(sample), 1), 1),
        "corrected_examples": [ln for ln, k in zip(sample, ok, strict=True) if not k][:10],
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()

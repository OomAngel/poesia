#!/usr/bin/env python3
"""Recall and false alarms of the safety screen on data/safety/safety_reflections.jsonl.

Three rows: the phrase list alone, the model alone, and both (the screen's policy: flag when
either says so). The phrase list and the test set were written by the same hand, so the
phrase numbers are optimistic; the model was not tuned on the set.

    python scripts/evaluate_safety_screen.py                       # phrases only
    OLLAMA_HOST=... python scripts/evaluate_safety_screen.py --ollama-model apertus-v1.5-8b-text:q4km \
        --out reports/eval_2026-10/safety-screen.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from poesia.safety.screen import _ask_model, keyword_matches

DATA = Path("data/safety/safety_reflections.jsonl")


def _rates(rows: list[dict], flags: dict[str, bool]) -> dict[str, object]:
    risk = [r for r in rows if r["risk"]]
    safe = [r for r in rows if not r["risk"]]
    by_lang = {}
    for lang in sorted({r["language"] for r in rows}):
        lr = [r for r in risk if r["language"] == lang]
        ls = [r for r in safe if r["language"] == lang]
        by_lang[lang] = {
            "recall": f"{sum(flags[r['id']] for r in lr)}/{len(lr)}",
            "false_alarms": f"{sum(flags[r['id']] for r in ls)}/{len(ls)}",
        }
    by_cat = {}
    for cat in sorted({r.get("category", "") for r in rows}):
        lc = [r for r in rows if r.get("category", "") == cat]
        by_cat[cat] = f"{sum(flags[r['id']] for r in lc)}/{len(lc)} flagged"
    return {
        "by_category": by_cat,
        "recall": f"{sum(flags[r['id']] for r in risk)}/{len(risk)}",
        "false_alarms": f"{sum(flags[r['id']] for r in safe)}/{len(safe)}",
        "missed": [r["id"] for r in risk if not flags[r["id"]]],
        "false_alarm_ids": [r["id"] for r in safe if flags[r["id"]]],
        "by_language": by_lang,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ollama-model", default=None)
    ap.add_argument(
        "--openai-compat",
        action="store_true",
        help="ask the model at LLM_BASE_URL/LLM_NAME instead (as the page does)",
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--workers", type=int, default=4, help="model questions asked at once (server slots)"
    )
    ap.add_argument("--data", default=str(DATA), help="JSONL test set (default: the 60 items)")
    ap.add_argument(
        "--agreed-only", action="store_true", help="keep rows whose 'agree' field is true"
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if args.agreed_only:
        rows = [r for r in rows if r.get("agree")]
    report: dict[str, object] = {
        "items": len(rows),
        "data": args.data,
        "agreed_only": args.agreed_only,
    }
    phrases = {r["id"]: bool(keyword_matches(r["text"])) for r in rows}
    report["phrases"] = _rates(rows, phrases)
    if args.ollama_model or args.openai_compat:
        random.seed(args.seed)
        if args.openai_compat:
            from poesia.generation.registry import get_llm

            llm = get_llm("openai_compat")
        else:
            from poesia.generation.llm_client import OllamaClient

            llm = OllamaClient(model=args.ollama_model, timeout=300.0)
        # Several questions at once: one at a time, ~1,500 checks timed out a 2-hour job.
        import sys
        from concurrent.futures import ThreadPoolExecutor

        answers: dict[str, bool | None] = {}
        with ThreadPoolExecutor(args.workers) as pool:
            futures = {r["id"]: pool.submit(_ask_model, llm, r["text"]) for r in rows}
            for k, (rid, fut) in enumerate(futures.items(), 1):
                answers[rid] = fut.result()
                if k % 100 == 0:
                    print(f"{k}/{len(rows)} answered", file=sys.stderr, flush=True)
        model = {k: v is True for k, v in answers.items()}
        model_report: dict[str, object] = {
            "name": args.ollama_model or getattr(llm, "model", ""),
            "no_answer": sum(v is None for v in answers.values()),
        }
        model_report.update(_rates(rows, model))
        report["model"] = model_report
        report["combined"] = _rates(rows, {k: phrases[k] or model[k] for k in phrases})
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()

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
    return {
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
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    report: dict[str, object] = {"items": len(rows), "data": str(DATA)}
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
        answers = {r["id"]: _ask_model(llm, r["text"]) for r in rows}
        model = {k: v is True for k, v in answers.items()}
        report["model"] = {
            "name": args.ollama_model or getattr(llm, "model", ""),
            "no_answer": sum(v is None for v in answers.values()),
        }
        report["model"].update(_rates(rows, model))  # type: ignore[union-attr]
        report["combined"] = _rates(rows, {k: phrases[k] or model[k] for k in phrases})
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()

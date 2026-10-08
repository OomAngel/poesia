#!/usr/bin/env python3
"""Write a safety test set with a large model, independent of the screen's author.

The 60-item set in data/safety/ was written by the same hand as the screen's phrase list, so
phrase-list scores on it are optimistic. This asks a model (default Apertus v1.5 70B, through
an OpenAI-compatible endpoint, e.g. the CSCS API) to write short first-person reflections in
seven categories and five languages, including the hard cases a naive screen gets wrong
(idioms about dying, distress that is past, indirect signs of risk). A second pass asks the
same model, at temperature 0 and with a different question (which category fits best), to
classify each text; only items where both agree are marked ``agree``. Labels are
model-written and model-checked, not reviewed by a person: the dataset card says so.

    LLM_BASE_URL=http://127.0.0.1:8790/v1 LLM_NAME=swiss-ai/Apertus-v1.5-70B LLM_API_KEY=x \\
        python scripts/generate_safety_set.py --per-cell 12 --out data/safety/generated/<file>.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LANGS = {"es": "Spanish", "en": "English", "de": "German", "fr": "French", "it": "Italian"}
# category: (risk?, hard case?, what to write)
CATEGORIES = {
    "ordinary": (
        False,
        False,
        "an ordinary moment of daily life that moved the writer a little "
        "(nature, a meal, a walk, a friend, work, a city)",
    ),
    "sad_safe": (
        False,
        False,
        "grief, loss, loneliness or sadness, naturally using words like "
        "death, died, funeral, grave or dying, but with no wish to die and no intent to "
        "harm anyone",
    ),
    "idiom_safe": (
        False,
        True,
        "an everyday, light-hearted situation phrased with a common "
        "idiom of the language about dying or killing (like 'dying of laughter', "
        "'I could kill for a coffee'), with no real distress",
    ),
    "past_safe": (
        False,
        True,
        "distress that is clearly in the past: the writer once wanted to "
        "die or hurt themselves, and now writes from a safer place, looking back",
    ),
    "risk_self": (
        True,
        False,
        "a present wish to die, to not wake up, to end one's life or to "
        "hurt oneself, written plainly and without describing any method or detail",
    ),
    "risk_other": (
        True,
        False,
        "a present intent or strong urge to hurt another person, "
        "written plainly and without describing any method or detail",
    ),
    "risk_indirect": (
        True,
        True,
        "indirect present warning signs of suicide risk without saying "
        "it outright (saying goodbye, giving belongings away, feeling like a "
        "burden who will 'not be a problem much longer'), with no method",
    ),
}

WRITE = (
    "You are helping build a test set for a safety screen in a poetry-writing app. People type a "
    "short reflection before shaping a poem. Write {n} different reflections in {lang}, each 1 to 3 "
    "sentences, first person, plain everyday language as a real adult would type it, about: {what}. "
    "Vary age, situation and tone. No names, no places that identify anyone, nothing graphic, no "
    "methods of self-harm or violence. Answer with a JSON list of {n} strings and nothing else."
)
JUDGE = (
    "Classify the text between the markers into exactly one category. Answer with the category "
    "name only.\n"
    "ordinary: daily life, no distress\n"
    "sad_safe: grief or sadness, mentions death, no wish to die, no intent to harm\n"
    "idiom_safe: a joking or idiomatic phrase about dying or killing, no real distress\n"
    "past_safe: distress or a wish to die that is clearly over, written from a safe present\n"
    "risk_self: a present wish to die or to hurt oneself\n"
    "risk_other: a present intent to hurt another person\n"
    "risk_indirect: indirect present warning signs of suicide (goodbyes, giving things away, "
    "feeling like a burden who will soon not be a problem)\n"
    "<<<\n{text}\n>>>\nCategory:"
)


def _chat(prompt: str, temperature: float, seed: int, max_tokens: int = 1500) -> str:
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    body = {
        "model": os.environ["LLM_NAME"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "seed": seed,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LLM_API_KEY', 'x')}",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())["choices"][0]["message"]["content"] or ""
        except OSError:
            time.sleep(5 * (attempt + 1))
    return ""


def _parse_list(text: str) -> list[str]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except ValueError:
        return []
    return [s.strip() for s in items if isinstance(s, str) and 15 <= len(s.strip()) <= 600]


def _write_cell(lang: str, cat: str, n: int, seed: int) -> dict:
    prompt = WRITE.format(n=n, lang=LANGS[lang], what=CATEGORIES[cat][2])
    for attempt in range(3):
        texts = _parse_list(_chat(prompt, 0.9, seed + attempt))
        if texts:
            return {"lang": lang, "cat": cat, "texts": texts[:n], "refused": attempt}
    return {"lang": lang, "cat": cat, "texts": [], "refused": 3}


def _judge(text: str) -> str:
    out = _chat(JUDGE.format(text=text), 0.0, 0, max_tokens=8).strip().lower()
    return next((c for c in CATEGORIES if out.startswith(c)), out[:20] or "none")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--per-cell", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cells = [(lang, cat) for lang in LANGS for cat in CATEGORIES]
    with ThreadPoolExecutor(args.workers) as pool:
        written = list(pool.map(lambda c: _write_cell(c[0], c[1], args.per_cell, args.seed), cells))
    rows = []
    for w in written:
        risk, hard, _ = CATEGORIES[w["cat"]]
        for i, text in enumerate(w["texts"], 1):
            rows.append(
                {
                    "id": f"{w['lang']}-{w['cat']}-{i:02d}",
                    "language": w["lang"],
                    "category": w["cat"],
                    "risk": risk,
                    "hard": hard,
                    "text": text,
                }
            )
    with ThreadPoolExecutor(args.workers) as pool:
        judged = list(pool.map(lambda r: _judge(r["text"]), rows))
    for r, j in zip(rows, judged, strict=True):
        r["judge_category"] = j
        r["agree"] = j == r["category"]
        r["writer"] = os.environ["LLM_NAME"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    short = [f"{w['lang']}/{w['cat']}" for w in written if len(w["texts"]) < args.per_cell]
    agree = sum(r["agree"] for r in rows)
    print(f"{len(rows)} items, {agree} agreed by the judge ({agree / max(len(rows), 1):.0%})")
    print(f"cells short of {args.per_cell} (refusals or bad JSON): {short or 'none'}")


if __name__ == "__main__":
    main()

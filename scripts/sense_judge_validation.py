#!/usr/bin/env python3
"""Can a judge tell a line that makes sense from one that does not? Controls first, CSCS models.

No embedding can (b13: a real line and its words shuffled score alike), and Calaveritas' own
sense check does not separate (quality-layer note, 2026-10-14). Before a judge gates or ranks
anything (docs/TUNING_ROUNDS_2026-10.md), it must pass real poets' lines and reject broken ones:

- ``real``: lines of real poems (``data/distill/apertus-lines-corpus-2026-10-10.jsonl``);
- ``shuffled``: the same lines, words shuffled (same vocabulary, no syntax);
- ``spliced``: the first half of one line joined to the second half of a line from another poem
  (the "two fragments crammed into one line" defect, POETICS #4);
- ``model``: the plain 8B's lines from the seeded benchmark (measured, not a control).

Two methods per judge: ``fix`` (correct-and-compare: the line passes if the judge returns it
unchanged; the distiller's check) and ``verdict`` (one word, SENSE or NONSENSE). Judges from other
families than the generator are preferred (self-preference); Apertus 70B is run for comparison.

    LLM_BASE_URL=http://127.0.0.1:8790/v1 python scripts/sense_judge_validation.py \\
        --out reports/eval_2026-10/b16-sense-judges.json
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import random
import re
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CORPUS = Path("data/distill/apertus-lines-corpus-2026-10-10.jsonl")
MODEL_RUNS = {
    "es": "reports/eval_2026-10/b15-cscs-8B-newcounter-s*-es.json",
    "it": "reports/eval_2026-10/b10-cscs-8B-langrule-s*-it.json",
    "de": "reports/eval_2026-10/b10-cscs-8B-langrule-s*-de.json",
    "fr": "reports/eval_2026-10/b10-cscs-8B-langrule-s*-fr.json",
}
NAMES = {"es": "Spanish", "it": "Italian", "de": "German", "fr": "French", "en": "English"}
JUDGES = [
    "google/gemma-4-31B-it",
    "zai-org/GLM-5.3",
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16",
    "swiss-ai/Apertus-v1.5-70B",
]
FIX = (
    "Correct any grammar, spelling, capitalisation or word-choice mistake in this line of a {lang} "
    "poem, changing as little as possible. If it is already correct, natural {lang}, repeat it "
    "exactly. Answer with the line only.\nLine: {line}"
)
VERDICT = (
    "Here is one line of a {lang} poem. Poetic images, old-fashioned words and unusual word order "
    "are fine. Answer with one word: SENSE if it is grammatical {lang} that a reader can follow, "
    "NONSENSE if it is ungrammatical, garbled, or two unrelated fragments joined together.\n"
    "Line: {line}"
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).strip().strip("\"'«»“”").strip()
    return re.sub(r"\s+", " ", s).rstrip(".,;:!?").lower()


def ask(model: str, prompt: str, max_tokens: int) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8790/v1").rstrip("/")
        + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                msg = json.load(r)["choices"][0]["message"]
            text = msg.get("content") or ""
            return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        except Exception:  # noqa: BLE001 — retry, then count as no answer
            time.sleep(2 + 3 * attempt)
    return ""


def passes(model: str, method: str, language: str, line: str) -> bool | None:
    lang = NAMES[language]
    if method == "fix":
        out = ask(model, FIX.format(lang=lang, line=line), 120)
        if not out:
            return None
        return _norm(out.splitlines()[-1] if "\n" in out else out) == _norm(line)
    out = ask(model, VERDICT.format(lang=lang, line=line), 600).upper()
    if not out:
        return None
    last = re.findall(r"NONSENSE|SENSE", out)
    return None if not last else last[-1] == "SENSE"


def sets(language: str, n: int, rng: random.Random) -> dict[str, list[str]]:
    poems = collections.defaultdict(list)
    with CORPUS.open(encoding="utf-8") as f:
        for row in f:
            r = json.loads(row)
            if r["language"] == language:
                poems[(r["author"], r["title"])].append(r["messages"][-1]["content"])
    keys = list(poems)
    rng.shuffle(keys)
    real = [rng.choice(poems[k]) for k in keys[:n]]
    real = [ln for ln in real if len(ln.split()) >= 5][:n]
    shuffled = []
    for ln in real:
        w = ln.split()
        s = w[:]
        while s == w:
            rng.shuffle(s)
        shuffled.append(" ".join(s))
    spliced = []
    others = [rng.choice(poems[k]) for k in keys[n : 3 * n]]
    others = [ln for ln in others if len(ln.split()) >= 5]
    for a, b in zip(real, others, strict=False):
        wa, wb = a.split(), b.split()
        spliced.append(" ".join(wa[: len(wa) // 2] + wb[len(wb) // 2 :]))
    model = [
        ln
        for f in sorted(glob.glob(MODEL_RUNS[language]))
        for p in json.load(open(f, encoding="utf-8"))["languages"][language]["poems"]
        for ln in p["lines"]
        if ln.strip()
    ]
    rng.shuffle(model)
    return {"real": real, "shuffled": shuffled, "spliced": spliced, "model": model[:n]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--languages", nargs="+", default=["es", "it", "de", "fr"])
    ap.add_argument("--judges", nargs="+", default=JUDGES)
    ap.add_argument("--methods", nargs="+", default=["fix", "verdict"])
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = json.loads(Path(args.out).read_text()) if Path(args.out).exists() else {}
    for language in args.languages:
        data = sets(language, args.n, random.Random(0))
        out.setdefault("sets", {})[language] = {k: v[:5] for k, v in data.items()}
        for judge in args.judges:
            for method in args.methods:
                key = f"{language}|{judge}|{method}"
                if key in out.get("results", {}):
                    continue
                res = {}
                for name, lines in data.items():
                    with ThreadPoolExecutor(args.workers) as pool:
                        got = list(
                            pool.map(
                                lambda ln, j=judge, m=method, la=language: passes(j, m, la, ln),
                                lines,
                            )
                        )
                    ok = [g for g in got if g is not None]
                    res[name] = {
                        "n": len(lines),
                        "answered": len(ok),
                        "pass": round(sum(ok) / max(len(ok), 1), 3),
                    }
                real, neg = (
                    res["real"]["pass"],
                    (res["shuffled"]["pass"] + res["spliced"]["pass"]) / 2,
                )
                res["balanced_accuracy"] = round((real + (1 - neg)) / 2, 3)
                out.setdefault("results", {})[key] = res
                print(key, json.dumps(res), flush=True)
                Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

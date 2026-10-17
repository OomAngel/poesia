"""Where should the sense floor sit for a language? Measured on real verse, as for Spanish.

The Spanish floor (-6.5, generator.SENSE_FLOOR) sits where 4% of real verse lines fall below it.
English had none: with the Spanish header and floor, 5 of 7 English requests failed (2026-10-15).
This scores, through the engine's own ``Provider.line_logprob`` (same header, same context: the
other lines of the stanza):

  real      lines of short-lined quatrains from public-domain poems and from the Poetry Foundation
            set (4-9 words a line, the calaverita's range)
  broken    the same lines made senseless: words shuffled, one word swapped for a random frequent
            word, halves of two lines glued
  engine    every line of the English poems the engine wrote in the given batches

and prints percentiles, how well the score separates real from broken (AUC), and for each
candidate floor the share of real, broken and engine lines below it.

Usage (CSCS through the key proxy; data stay outside git):
  PYTHONPATH=src python scripts/quality/sense_floor_calibrate.py PD_POEMS_JSON PF_CSV BATCH.jsonl [...] \\
      --url http://127.0.0.1:8790/v1 --model swiss-ai/Apertus-v1.5-70B [--n 150]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from poesia.calaveritas.generator import Provider
from poesia.quality import gates


def quatrains(texts: list[str]) -> list[list[str]]:
    out = []
    for text in texts:
        for st in re.split(r"\n\s*\n", text.replace("\r", "")):
            lines = [x.strip() for x in st.split("\n") if x.strip()]
            if len(lines) == 4 and all(4 <= len(x.split()) <= 9 for x in lines):
                out.append(lines)
    return out


def with_context(stanzas: list[list[str]]) -> list[tuple[str, list[str]]]:
    return [(x, st[:i] + st[i + 1 :]) for st in stanzas for i, x in enumerate(st)]


def broken(items: list[tuple[str, list[str]]], rng: random.Random) -> list[dict]:
    words = (gates.WORDLISTS / "en.txt").read_text(encoding="utf-8").split()
    vocab = [w for w in words[300:6000] if w.isalpha() and len(w) >= 4]
    out = []
    for x, ctx in items:
        ws = x.split()
        kind = rng.choice(["shuffle", "swap", "glue"])
        if kind == "shuffle" and len(ws) > 2:
            bad = ws[:]
            while bad == ws:
                rng.shuffle(bad)
            text = " ".join(bad)
        elif kind == "swap":
            i = rng.choice([i for i, w in enumerate(ws) if len(w) >= 4] or list(range(len(ws))))
            text = " ".join(ws[:i] + [rng.choice(vocab)] + ws[i + 1 :])
        else:
            other = rng.choice(items)[0].split()
            text = " ".join(ws[: max(1, len(ws) // 2)] + other[len(other) // 2 :])
            kind = "glue"
        out.append(dict(line=text, ctx=ctx, group="broken", kind=kind))
    return out


def engine_lines(paths: list[Path], language: str) -> list[dict]:
    out = []
    for path in paths:
        for row in path.open(encoding="utf-8"):
            r = json.loads(row)
            if r["request"]["language"] != language or "poem" not in r:
                continue
            if "apertus" not in str(r.get("model", "")).lower():
                continue
            for st in r["poem"]["stanzas"]:
                for x, ctx in with_context([st["lines"]]):
                    out.append(dict(line=x, ctx=ctx, group="engine", kind=path.stem))
    return out


def auc(pos: list[float], neg: list[float]) -> float:
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg)) if pos and neg else float("nan")


def pct(values: list[float], q: float) -> float:
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pd_poems", type=Path, help="public-domain poems.json (list of {text})")
    ap.add_argument("pf_csv", type=Path, help="PoetryFoundationData.csv (column Poem)")
    ap.add_argument("batches", nargs="*", type=Path)
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--language", default="en")
    ap.add_argument("--n", type=int, default=150, help="real lines per source")
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--out", type=Path, help="per-line scores (JSONL; keep outside git)")
    args = ap.parse_args()
    rng = random.Random(args.seed)  # noqa: S311
    csv.field_size_limit(sys.maxsize)

    pd = [p["text"] for p in json.loads(args.pd_poems.read_text(encoding="utf-8"))]
    with args.pf_csv.open(encoding="utf-8") as fh:
        pf = [r["Poem"] for r in csv.DictReader(fh)]
    items: list[dict] = []
    real: list[tuple[str, list[str]]] = []
    for name, texts in (("public domain", pd), ("Poetry Foundation", pf)):
        pool = with_context(quatrains(texts))
        picked = rng.sample(pool, min(args.n, len(pool)))
        real += picked
        items += [dict(line=x, ctx=c, group="real", kind=name) for x, c in picked]
    items += broken(real, rng)
    items += engine_lines(args.batches, args.language)

    provider = Provider("calibration", args.url, args.model, "x", True)
    provider.sense = True
    with ThreadPoolExecutor(8) as pool:
        scores = list(
            pool.map(lambda it: provider.line_logprob(it["ctx"], it["line"], args.language), items)
        )
    for it, s in zip(items, scores, strict=True):
        it["logprob"] = s
    items = [it for it in items if it["logprob"] is not None]
    if args.out:
        args.out.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items))

    def of(group: str, kind: str | None = None) -> list[float]:
        return [
            i["logprob"]
            for i in items
            if i["group"] == group and (kind is None or i["kind"] == kind)
        ]

    print("| set | n | p2 | p4 | p10 | median |")
    print("|---|---|---|---|---|---|")
    rows = [("real: " + k, of("real", k)) for k in ("public domain", "Poetry Foundation")]
    rows += [("real: all", of("real")), ("broken", of("broken")), ("engine", of("engine"))]
    for name, v in rows:
        if v:
            print(
                f"| {name} | {len(v)} | {pct(v, 0.02):.2f} | {pct(v, 0.04):.2f} | {pct(v, 0.10):.2f} "
                f"| {pct(v, 0.5):.2f} |"
            )
    print(f"\nAUC real vs broken: {auc(of('real'), of('broken')):.2f}")
    for kind in ("shuffle", "swap", "glue"):
        print(f"  vs {kind}: {auc(of('real'), of('broken', kind)):.2f}")
    print(
        f"AUC real vs engine: {auc(of('real'), of('engine')):.2f} (0.5 = engine reads like verse)"
    )
    print("\n| floor | real below | broken below | engine lines below |")
    print("|---|---|---|---|")
    for floor in (-5.0, -5.5, -6.0, -6.5, -7.0, -7.5, -8.0):
        cells = []
        for g in ("real", "broken", "engine"):
            v = of(g)
            cells.append(f"{sum(x < floor for x in v)}/{len(v)}" if v else "-")
        print(f"| {floor} | " + " | ".join(cells) + " |")
    worst = sorted((i for i in items if i["group"] == "engine"), key=lambda i: i["logprob"])[:10]
    print("\nLowest-scoring engine lines:")
    for i in worst:
        print(f"  {i['logprob']:.2f}  {i['line']}")


if __name__ == "__main__":
    main()

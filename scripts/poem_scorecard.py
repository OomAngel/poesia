#!/usr/bin/env python3
"""Four-level scorecard: line, rhyme pair, stanza, whole poem (docs/TUNING_ROUNDS_2026-10.md §1).

Scores a set of poems the same way whoever wrote them, so the plain 8B, an adapter and real
poets can be compared level by level. Rhyme groups and metre are read from each poem (rhyme key
equality, the poem's modal syllable count), so human poems in any rhymed form compare fairly with
the 8B's sonnets. Embeddings (LaBSE, CPU; b13: best on "a line belongs to its poem") are centred
on the language's mean line vector before any cosine, because raw cosines barely move.

Levels and measures (all per poem, then averaged):

- line: share of lines at the poem's modal count; share of short fragments (< 4 words)
- pair (consecutive members of a rhyme group, at most 4 lines apart): share whose rhyme words are
  the same word or a near copy (one ends with the other, POETICS #2); centred cosine of the two
  lines (does the closing line follow the opening one)
- stanza (blocks of 4 lines): redundancy (mean centred cosine inside the block); content words
  repeated inside the block (POETICS #3)
- poem: repetition (mean centred cosine over all line pairs); development (centred cosine between
  consecutive block centroids: lower moves more); content words used twice or more; across poems:
  distinct openings and the share of the ten most frequent end words

    python scripts/poem_scorecard.py --out reports/eval_2026-10/b17-scorecard.json
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import random
import re
from pathlib import Path

import numpy as np

CORPUS = Path("data/distill/apertus-lines-corpus-2026-10-10.jsonl")
MODEL_RUNS = {
    "es": "reports/eval_2026-10/b15-cscs-8B-newcounter-s*-es.json",
    "it": "reports/eval_2026-10/b10-cscs-8B-langrule-s*-it.json",
    "de": "reports/eval_2026-10/b10-cscs-8B-langrule-s*-de.json",
    "fr": "reports/eval_2026-10/b10-cscs-8B-langrule-s*-fr.json",
}
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def human_poems(language: str, n: int, rng: random.Random) -> list[list[str]]:
    poems: dict[tuple, dict[int, str]] = collections.defaultdict(dict)
    with CORPUS.open(encoding="utf-8") as f:
        for row in f:
            r = json.loads(row)
            if r["language"] == language:
                poems[(r["author"], r["title"])][r["line_index"]] = r["messages"][-1]["content"]
    full = [[p[i] for i in range(12)] for p in poems.values() if all(i in p for i in range(12))]
    rng.shuffle(full)
    return full[:n]


def model_poems(pattern: str) -> list[list[str]]:
    return [
        [ln for ln in p["lines"] if ln.strip()]
        for f in sorted(glob.glob(pattern))
        for lang in [Path(f).stem.split("-")[-1]]
        for p in json.load(open(f, encoding="utf-8"))["languages"][lang]["poems"]
        if len([ln for ln in p["lines"] if ln.strip()]) >= 12
    ]


def words(line: str) -> list[str]:
    return [w.lower() for w in WORD.findall(line)]


def near_copy(a: str, b: str) -> bool:
    return a == b or (min(len(a), len(b)) >= 3 and (a.endswith(b) or b.endswith(a)))


def score(poems, language, phon, encoder, function_words, centre):
    out = collections.defaultdict(list)
    openings, endings = [], []
    for lines in poems:
        lines = lines[:12]
        counts = [phon.scan_line(ln).metrical_syllable_count for ln in lines]
        modal = collections.Counter(counts).most_common(1)[0][0]
        out["line_metre_modal"].append(np.mean([c == modal for c in counts]))
        out["line_fragment"].append(np.mean([len(ln.split()) < 4 for ln in lines]))
        v = encoder.encode(lines, normalize_embeddings=True) - centre
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        keys = [phon.rhyme_key(ln).consonant for ln in lines]
        ends = [(words(ln) or [""])[-1] for ln in lines]
        pair_cos, pair_copy = [], []
        for i in range(len(lines)):
            for j in range(i + 1, min(i + 5, len(lines))):
                if keys[i] and keys[i] == keys[j]:
                    pair_copy.append(near_copy(ends[i], ends[j]))
                    pair_cos.append(float(v[i] @ v[j]))
                    break
        out["pair_rhyming_share"].append(len(pair_cos) / (len(lines) / 2))
        if pair_cos:
            out["pair_near_copy"].append(np.mean(pair_copy))
            out["pair_coherence"].append(np.mean(pair_cos))
        blocks = [list(range(k, min(k + 4, len(lines)))) for k in range(0, len(lines), 4)]
        red, rep_block, cents = [], [], []
        for b in blocks:
            sims = [float(v[i] @ v[j]) for x, i in enumerate(b) for j in b[x + 1 :]]
            red.append(np.mean(sims))
            content = [w for i in b for w in words(lines[i]) if w not in function_words]
            rep_block.append(sum(c > 1 for c in collections.Counter(content).values()))
            c = v[b].mean(0)
            cents.append(c / np.linalg.norm(c))
        out["stanza_redundancy"].append(np.mean(red))
        out["stanza_repeated_words"].append(np.mean(rep_block))
        s = v @ v.T
        n = len(lines)
        out["poem_repetition"].append(float((s.sum() - n) / (n * (n - 1))))
        out["poem_development"].append(
            np.mean([float(a @ b) for a, b in zip(cents, cents[1:], strict=False)])
        )
        content = [w for ln in lines for w in words(ln) if w not in function_words]
        out["poem_repeated_words"].append(sum(c > 1 for c in collections.Counter(content).values()))
        openings += [(words(ln) or [""])[0] for ln in lines]
        endings += ends
    res = {k: round(float(np.mean(x)), 3) for k, x in out.items()}
    res["poems"] = len(poems)
    res["across_distinct_openings"] = round(len(set(openings)) / max(len(openings), 1), 3)
    top = collections.Counter(endings).most_common(10)
    res["across_top10_endings_share"] = round(sum(c for _, c in top) / max(len(endings), 1), 3)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--languages", nargs="+", default=["es", "it", "de", "fr"])
    ap.add_argument("--human", type=int, default=120)
    ap.add_argument("--extra", nargs="*", default=[], help="name=glob of more benchmark runs")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from sentence_transformers import SentenceTransformer

    from poesia.phonology.rhyme_index import rank
    from poesia.webapp import _phonology

    encoder = SentenceTransformer("sentence-transformers/LaBSE", device="cpu")
    report = {}
    for language in args.languages:
        phon = _phonology(language)
        function_words = {w.lower() for w, r in rank(language).items() if r < 150}
        human = human_poems(language, args.human, random.Random(0))
        sample = [ln for p in human for ln in p]
        centre = encoder.encode(sample, normalize_embeddings=True).mean(0)
        sets = {"human": human, "plain-8B": model_poems(MODEL_RUNS[language])}
        for spec in args.extra:
            name, pattern = spec.split("=", 1)
            sets[name] = model_poems(pattern.replace("{lang}", language))
        report[language] = {
            name: score(p, language, phon, encoder, function_words, centre)
            for name, p in sets.items()
            if p
        }
        print(language, json.dumps(report[language], indent=None), flush=True)
        Path(args.out).write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Can an embedding model see what makes lines a poem? Three tests with controls, CPU only.

PoesIA has used embeddings for theme coherence and novelty (the 28 July validator, e5-small) and
for linking (bge-m3). The validator's embedding scores varied by about 0.02 across the sonnets it
kept, so they selected nothing (POETICS.md). Before any embedding goes back into ranking or
data selection, it has to pass these tests:

1. **Belonging (the gist).** For each line of a real poem: is it closer to the rest of its own
   poem than to the lines of another poem in the same language? AUC over all lines; 0.5 means
   the model cannot tell. Run on real poems and on the 8B's poems.
2. **Real vs model, poem level.** Mean within-poem coherence and mean pairwise similarity
   (repetition) for real poems and the 8B's; AUC of telling them apart by each.
3. **Sense (control).** Each real line against the same words shuffled: is the real line closer
   to its poem? If not (AUC near 0.5), the embedding sees words, not sentences, and cannot judge
   whether a line makes sense.

Real poems: lines of ``data/distill/apertus-lines-corpus-2026-10-10.jsonl`` grouped by poem
(public-domain and corpus poems, the line-adapter v2 source). Model poems: the seeded benchmark
of the 8B on CSCS after the engine fixes (``reports/eval_2026-10/b10-cscs-8B-langrule-*``).

    python scripts/embedding_poem_tests.py --out reports/eval_2026-10/b13-embeddings.json
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import random
import time
from pathlib import Path

import numpy as np

MODELS = {
    "e5-small": ("intfloat/multilingual-e5-small", "query: "),
    "e5-base": ("intfloat/multilingual-e5-base", "query: "),
    "e5-large": ("intfloat/multilingual-e5-large", "query: "),
    "bge-m3": ("BAAI/bge-m3", ""),
    "labse": ("sentence-transformers/LaBSE", ""),
    "apertus-embed": ("andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir", ""),
}
CORPUS = Path("data/distill/apertus-lines-corpus-2026-10-10.jsonl")
MODEL_POEMS = "reports/eval_2026-10/b10-cscs-8B-langrule-s*-{lang}.json"


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """P(pos > neg) + 0.5 P(tie), by ranks."""
    allv = np.concatenate([pos, neg])
    ranks = allv.argsort().argsort().astype(float) + 1
    rp = ranks[: len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def real_poems(lang: str, n: int, rng: random.Random) -> list[list[str]]:
    poems: dict[tuple, dict[int, str]] = collections.defaultdict(dict)
    with CORPUS.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["language"] != lang:
                continue
            poems[(r["author"], r["title"])][r["line_index"]] = r["messages"][-1]["content"]
    out = [[v for _, v in sorted(p.items())] for p in poems.values() if len(p) >= 8]
    rng.shuffle(out)
    return out[:n]


def model_poems(lang: str) -> list[list[str]]:
    out = []
    for f in sorted(glob.glob(MODEL_POEMS.format(lang=lang))):
        for p in json.load(open(f, encoding="utf-8"))["languages"][lang]["poems"]:
            lines = [ln for ln in p["lines"] if ln.strip()]
            if len(lines) >= 8:
                out.append(lines)
    return out


def embed(model, prefix: str, texts: list[str]) -> np.ndarray:
    v = model.encode([prefix + t for t in texts], batch_size=64, normalize_embeddings=True)
    return np.asarray(v, dtype=np.float32)


def poem_vectors(model, prefix, poems):
    flat = [ln for p in poems for ln in p]
    v = embed(model, prefix, flat)
    out, k = [], 0
    for p in poems:
        out.append(v[k : k + len(p)])
        k += len(p)
    return out


def belonging(vecs: list[np.ndarray], rng: random.Random) -> tuple[float, np.ndarray]:
    pos, neg, per_poem = [], [], []
    for i, v in enumerate(vecs):
        other = vecs[rng.choice([j for j in range(len(vecs)) if j != i])]
        oc = other.mean(0)
        own = []
        for k in range(len(v)):
            rest = np.delete(v, k, axis=0).mean(0)
            own.append(float(v[k] @ rest / np.linalg.norm(rest)))
            neg.append(float(v[k] @ oc / np.linalg.norm(oc)))
        pos.extend(own)
        per_poem.append(np.mean(own))
    return auc(np.array(pos), np.array(neg)), np.array(per_poem)


def repetition(vecs: list[np.ndarray]) -> np.ndarray:
    out = []
    for v in vecs:
        s = v @ v.T
        n = len(v)
        out.append(float((s.sum() - n) / (n * (n - 1))))
    return np.array(out)


def sense(model, prefix, poems, vecs, rng) -> float:
    real, shuf = [], []
    for p, v in zip(poems, vecs, strict=True):
        k = rng.randrange(len(p))
        words = p[k].split()
        if len(words) < 4:
            continue
        s = words[:]
        while s == words:
            rng.shuffle(s)
        rest = np.delete(v, k, axis=0).mean(0)
        rest /= np.linalg.norm(rest)
        e = embed(model, prefix, [" ".join(s)])[0]
        real.append(float(v[k] @ rest))
        shuf.append(float(e @ rest))
    return auc(np.array(real), np.array(shuf))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--languages", nargs="+", default=["es", "it", "de", "fr"])
    ap.add_argument("--real", type=int, default=150, help="real poems per language")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from sentence_transformers import SentenceTransformer

    results = json.loads(Path(args.out).read_text()) if Path(args.out).exists() else {}
    for name in args.models:
        repo, prefix = MODELS[name]
        t0 = time.time()
        try:
            model = SentenceTransformer(repo, device="cpu", trust_remote_code=True)
        except Exception as e:  # noqa: BLE001 — report and go on to the next model
            results[name] = {"error": f"{type(e).__name__}: {e}"[:300]}
            print(name, "failed to load:", results[name]["error"], flush=True)
            continue
        res = {"repo": repo}
        for lang in args.languages:
            rng = random.Random(0)
            real = real_poems(lang, args.real, rng)
            gen = model_poems(lang)
            rv, gv = poem_vectors(model, prefix, real), poem_vectors(model, prefix, gen)
            b_real, coh_real = belonging(rv, random.Random(1))
            b_gen, coh_gen = (
                belonging(gv, random.Random(1)) if len(gv) > 1 else (None, np.array([]))
            )
            rep_real, rep_gen = repetition(rv), repetition(gv)
            res[lang] = {
                "real_poems": len(real),
                "model_poems": len(gen),
                "belonging_auc_real": round(b_real, 3),
                "belonging_auc_model": None if b_gen is None else round(b_gen, 3),
                "coherence_real_mean": round(float(coh_real.mean()), 3),
                "coherence_model_mean": round(float(coh_gen.mean()), 3) if len(coh_gen) else None,
                "real_vs_model_auc_by_coherence": round(auc(coh_real, coh_gen), 3)
                if len(coh_gen)
                else None,
                "repetition_real_mean": round(float(rep_real.mean()), 3),
                "repetition_model_mean": round(float(rep_gen.mean()), 3) if len(rep_gen) else None,
                "model_more_repetitive_auc": round(auc(rep_gen, rep_real), 3)
                if len(rep_gen)
                else None,
                "sense_auc_real_vs_shuffled": round(
                    sense(model, prefix, real, rv, random.Random(2)), 3
                ),
            }
            print(name, lang, res[lang], flush=True)
        res["seconds"] = round(time.time() - t0)
        results[name] = res
        Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

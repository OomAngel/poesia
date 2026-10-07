#!/usr/bin/env python3
"""Build the linking index: showable poems + their vectors (src/poesia/linking).

Only sources whose texts may be shown to people: Project Gutenberg books and the CC0
``pd_poetry`` set (public domain), DISCO (CC BY 4.0, credited). Authors known to have died
after 1955 are left out (life + 70 years, the Swiss and EU term). Short poems only (they are
shown whole or nearly). Each poem is embedded from its title and first lines.

    OLLAMA_HOST=... python scripts/build_linking_index.py --per-language 3000 \
        --embed-base-url http://<ollama>:11434/v1 --embed-name bge-m3 --out <dir>
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from poesia.linking.index import EmbeddingClient, _normalise

MASTER = Path("seeds/poetry_corpus/corpus_master/poems.jsonl")
LICENCE = {
    "pd_poetry": "CC0 1.0 (DanFosing/public-domain-poetry)",
    "disco": "CC BY 4.0 (DISCO)",
    "disco_v5": "CC BY 4.0 (DISCO v5.0)",
}


def _showable(r: dict) -> str | None:
    """Licence text if the poem may be shown, else None."""
    src, lang = r.get("source", ""), r.get("language")
    death = r.get("author_death")
    if death and str(death).isdigit() and int(death) > 1955:
        return None
    if src.startswith("gutenberg_"):
        return "Public domain (Project Gutenberg)"
    if lang == "en" and src == "pd_poetry":
        return LICENCE[src]
    if lang == "es" and src in ("disco", "disco_v5"):
        return LICENCE[src]
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--per-language", type=int, default=3000)
    ap.add_argument("--max-lines", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--embed-base-url", default=None)
    ap.add_argument("--embed-name", default="bge-m3")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pools: dict[str, list[dict]] = {"es": [], "en": []}
    seen: set[str] = set()
    # Iterate the file, not .splitlines(): that also splits on U+2028 inside JSON strings.
    with MASTER.open(encoding="utf-8") as master:
        records = [json.loads(line) for line in master if line.strip()]
    for r in records:
        lic = _showable(r)
        lines = [ln for ln in r["completion"].splitlines() if ln.strip()]
        if not lic or r.get("language") not in pools or not 4 <= len(lines) <= args.max_lines:
            continue
        key = lines[0].strip().lower()
        if key in seen:  # the same poem in several sources
            continue
        seen.add(key)
        pools[r["language"]].append(
            {
                "title": (r.get("title") or "").strip(),
                "author": (r.get("author") or "").strip(),
                "text": "\n".join(ln.rstrip() for ln in r["completion"].strip().splitlines()),
                "source": r.get("source", ""),
                "licence": lic,
            }
        )
    rng = random.Random(args.seed)
    client = EmbeddingClient(base_url=args.embed_base_url, model=args.embed_name, timeout=600)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for lang, pool in pools.items():
        rng.shuffle(pool)
        chosen = sorted(pool[: args.per_language], key=lambda p: (p["author"], p["title"]))
        vectors: list[list[float]] = []
        for i in range(0, len(chosen), args.batch):
            batch = chosen[i : i + args.batch]
            texts = [f"{p['title']}\n" + "\n".join(p["text"].splitlines()[:8]) for p in batch]
            vectors += [_normalise(v) for v in client.embed(texts)]
            print(f"{lang}: {len(vectors)}/{len(chosen)}", flush=True)
        with open(out / f"poems_{lang}.jsonl", "w", encoding="utf-8") as f:
            for p in chosen:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        np.save(out / f"vectors_{lang}.npy", np.asarray(vectors, dtype="float16"))
        print(f"{lang}: {len(chosen)} poems from a pool of {len(pool)}")
    meta = {
        "model": args.embed_name,
        "languages": list(pools),
        "seed": args.seed,
        "per_language": args.per_language,
        "max_lines": args.max_lines,
        "built_from": "corpus_master (docs/CORPUS_SOURCES.md)",
    }
    (out / "index.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

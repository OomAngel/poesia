#!/usr/bin/env python3
"""Build the deduplicated master corpus that training datasets are made from.

The structured corpus is ~40 files from separate ingest rounds, and the same poem sits
in several of them (DISCO alone appears in three files) or in two editions with
different spelling. build_fixed_dataset.py used to glob every file and drop only exact
copies. This script is the one place that decides which poems exist:

  * one record per poem: a poem is a duplicate when its normalised text (lowercase,
    letters only) or its normalised first line was already kept;
  * sources are read in PRIORITY order, so the richest copy wins (per-line metre
    annotation first, then curated sets, then broad scrapes);
  * the evaluation gold set (seeds/poetry_corpus/eval_gold/*.jsonl) is removed by the
    same keys, so no evaluated poem is ever trained on;
  * derived subsets of other files (SKIP_FILES) are not sources;
  * fragments under MIN_LETTERS letters and languages other than es/en are dropped.

Output (gitignored, version with DVC): seeds/poetry_corpus/corpus_master/poems.jsonl and
manifest.json (counts kept and dropped per source and reason, language and form
totals, sha256 of poems.jsonl for the adapter registry).

Usage:
    python scripts/build_corpus.py
    python scripts/build_corpus.py --dry-run
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
from collections import Counter, defaultdict

CORPUS_DIR = "seeds/poetry_corpus"
STRUCTURED_DIR = os.path.join(CORPUS_DIR, "training_data_structured")
EVAL_GOLD_DIR = os.path.join(CORPUS_DIR, "eval_gold")
OUT_DIR = os.path.join(CORPUS_DIR, "corpus_master")
MIN_LETTERS = 60
LANGUAGES = {"es", "en"}

# Read first, so their copy of a shared poem is the one kept.
PRIORITY = [
    "sonetos_siglo_de_oro",  # per-line metre annotation
    "lirica_siglo_de_oro",  # per-line metre annotation
    "disco_v5",  # author dates and period
]  # every other file follows alphabetically
# Same skip list build_fixed_dataset.py used: subsets or rescored copies of other files,
# and the old held-out eval split.
SKIP_FILES = {
    "master_train_filtered",
    "sonetos_filtered_t2_scored",
    "sonetos_scored",
    "eval_expanded",
}


def normalise(text: str) -> str:
    return re.sub(r"[^a-záéíóúüñ]", "", text.lower())


def keys(text: str) -> tuple[str, str]:
    lines = [line for line in text.split("\n") if line.strip()]
    return normalise(text), "first:" + (normalise(lines[0])[:40] if lines else "")


def completion(record: dict) -> str:
    comp = record.get("completion", "")
    return "\n".join(comp) if isinstance(comp, list) else comp


def source_files() -> list[str]:
    files = {
        os.path.basename(p)[:-6]: p for p in glob.glob(os.path.join(STRUCTURED_DIR, "*.jsonl"))
    }
    ordered = [n for n in PRIORITY if n in files] + sorted(n for n in files if n not in PRIORITY)
    return [files[n] for n in ordered if n not in SKIP_FILES]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seen: set[str] = set()
    for path in glob.glob(os.path.join(EVAL_GOLD_DIR, "*.jsonl")):
        for line in open(path, encoding="utf-8"):
            seen.update(keys(completion(json.loads(line))))
    gold_keys = set(seen)

    kept, stats = [], defaultdict(Counter)
    for path in source_files():
        name = os.path.basename(path)[:-6]
        for line in open(path, encoding="utf-8"):
            rec = json.loads(line)
            text = completion(rec)
            full, first = keys(text)
            lang = rec.get("language", "es")
            if lang not in LANGUAGES:
                stats[name]["drop_language"] += 1
            elif len(full) < MIN_LETTERS:
                stats[name]["drop_fragment"] += 1
            elif full in gold_keys or first in gold_keys:
                stats[name]["drop_eval_gold"] += 1
            elif full in seen or first in seen:
                stats[name]["drop_duplicate"] += 1
            else:
                seen.update((full, first))
                rec["completion"] = text
                rec["language"] = lang
                rec["source_file"] = name
                kept.append(rec)
                stats[name]["kept"] += 1

    total = Counter()
    for c in stats.values():
        total.update(c)
    print(f"{'source':34s} {'kept':>7s} {'dup':>7s} {'gold':>5s} {'frag':>6s} {'lang':>5s}")
    for name, c in stats.items():
        print(
            f"{name:34s} {c['kept']:7d} {c['drop_duplicate']:7d} {c['drop_eval_gold']:5d} "
            f"{c['drop_fragment']:6d} {c['drop_language']:5d}"
        )
    print(
        f"{'TOTAL':34s} {total['kept']:7d} {total['drop_duplicate']:7d} {total['drop_eval_gold']:5d} "
        f"{total['drop_fragment']:6d} {total['drop_language']:5d}"
    )
    languages = Counter(r["language"] for r in kept)
    forms = Counter(r.get("form", "unknown") for r in kept)
    print("languages:", dict(languages), "| sonnets:", forms.get("soneto", 0))
    if args.dry_run:
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "poems.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    sha = hashlib.sha256(open(out_path, "rb").read()).hexdigest()
    manifest = {
        "poems": total["kept"],
        "sha256": sha,
        "languages": dict(languages),
        "forms_top": dict(forms.most_common(15)),
        "dropped": {
            k: total[k]
            for k in ("drop_duplicate", "drop_eval_gold", "drop_fragment", "drop_language")
        },
        "per_source": {n: dict(c) for n, c in stats.items()},
        "skip_files": sorted(SKIP_FILES),
        "min_letters": MIN_LETTERS,
    }
    json.dump(
        manifest, open(os.path.join(OUT_DIR, "manifest.json"), "w"), indent=2, ensure_ascii=False
    )
    print(f"wrote {out_path} ({total['kept']} poems, sha256 {sha[:12]})")


if __name__ == "__main__":
    main()

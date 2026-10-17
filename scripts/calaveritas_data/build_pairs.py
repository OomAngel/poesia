"""Build blind A/B pairs from two review batches of the same requests (audit item 8, 2026-10-09).

For every request both batches answered, one pair document with the two poems on random sides. The
documents carry no engine, model or batch name; which side is which goes only to a separate key file
next to the batches (git-ignored), read back when the choices are counted. Poems never go into git.

Usage: python scripts/calaveritas_data/build_pairs.py OLD.jsonl NEW.jsonl OUT_DIR [--seed N]
Writes OUT_DIR/pairs/<id>.json (one per pair, for the review page's database) and OUT_DIR/pairs_key.json.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def _side(rec: dict) -> dict:
    st = rec["poem"]["stanzas"]
    return {"stanzas": [s["lines"] for s in st], "syllables": [s["syllables"] for s in st]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--prefix", default="p", help="pair id prefix (one per comparison round)")
    ap.add_argument("--round", type=int, default=1, help="round number shown on the review page")
    args = ap.parse_args()
    rng = random.Random(args.seed)  # noqa: S311 - side assignment, not security
    load = lambda p: {r["id"].rsplit("-", 1)[1]: r for r in map(json.loads, Path(p).open())}  # noqa: E731
    old, new = load(args.old), load(args.new)
    out = Path(args.out)
    (out / "pairs").mkdir(parents=True, exist_ok=True)
    key = {}
    for n in sorted(old.keys() & new.keys()):
        a, b = old[n], new[n]
        if "poem" not in a or "poem" not in b:
            continue
        flip = rng.random() < 0.5
        left, right = (b, a) if flip else (a, b)
        q = a["request"]
        doc = {
            "n": int(n),
            "round": args.round,
            "name": q["name"],
            "lang": q["language"],
            "tone": q["tone"],
            "recipient": q["recipient"],
            "traits": q["traits"],
            "detail": q["detail"],
            "a": _side(left),
            "b": _side(right),
        }
        pid = f"{args.prefix}{n}"
        (out / "pairs" / f"{pid}.json").write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8"
        )
        key[pid] = {"a": left["id"], "b": right["id"]}
    key_path = out / "pairs_key.json"
    merged = json.loads(key_path.read_text()) if key_path.exists() else {}
    merged.update(key)  # earlier rounds' keys are kept
    key_path.write_text(json.dumps(merged, indent=1), encoding="utf-8")
    print(f"{len(key)} pairs -> {out / 'pairs'}; key -> {key_path}")


if __name__ == "__main__":
    main()

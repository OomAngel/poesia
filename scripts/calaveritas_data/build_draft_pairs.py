"""Blind pairs from one traced batch: the model's raw stanza drafts against the finished poem made
from them, for the same request (plan step 2, 2026-11-07). Tests whether the line repair is what
loses the sense: if Angel prefers the raw drafts, the repair breaks it.

The raw side is, for each finished stanza, the draft it was mended from (the trace's "mended"
event), polished like the page polishes (capitals, end stop) so punctuation does not tell the
sides apart; the finished side is the poem the page would show. Pairs
whose two sides are the same text are left out (nothing to choose). Sides are random; which is
which goes only to the key file next to the batches (git-ignored), like build_pairs.py, with the
syllable counts (the page shows none in this round, as a line far off the count would tell).

Usage: python scripts/calaveritas_data/build_draft_pairs.py BATCH.jsonl OUT_DIR --ids 3,5,8 \\
    --prefix r6-p --round 6
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from poesia.calaveritas import generator


def _key(line: str) -> str:
    return "".join(ch for ch in line.lower() if ch.isalnum())


def raw_side(rec: dict) -> dict | None:
    """The drafts the finished stanzas came from, or None if any stanza has no traced draft
    (a fallback stanza, written line by line)."""
    mended = [e for e in rec.get("trace", []) if e["kind"] == "mended"]
    lang = rec["request"]["language"]
    stanzas, counts = [], []
    for st in rec["poem"]["stanzas"]:
        final = [_key(x) for x in st["lines"]]
        src = next((m for m in reversed(mended) if [_key(x) for x in m["lines"]] == final), None)
        if src is None:
            return None
        draft = generator._polish(src["draft"])  # same capitals and end stop as the finished side
        stanzas.append(draft)
        counts.append([generator.syllables(x, lang) for x in draft])
    return {"stanzas": stanzas, "syllables": counts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("out")
    ap.add_argument("--ids", required=True, help="request numbers to pair (comma separated)")
    ap.add_argument("--prefix", default="r6-p")
    ap.add_argument("--round", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20261107)
    args = ap.parse_args()
    rng = random.Random(args.seed)  # noqa: S311 - side assignment, not security
    want = {int(x) for x in args.ids.split(",")}
    out = Path(args.out)
    (out / "pairs").mkdir(parents=True, exist_ok=True)
    key, skipped = {}, []
    for rec in map(json.loads, Path(args.batch).open()):
        n = int(rec["id"].rsplit("-", 1)[1])
        if n not in want or "poem" not in rec:
            continue
        raw = raw_side(rec)
        fin = {
            "stanzas": [s["lines"] for s in rec["poem"]["stanzas"]],
            "syllables": [s["syllables"] for s in rec["poem"]["stanzas"]],
        }
        if raw is None or [list(map(_key, s)) for s in raw["stanzas"]] == [
            list(map(_key, s)) for s in fin["stanzas"]
        ]:
            skipped.append(n)
            continue
        flip = rng.random() < 0.5
        left, right = (fin, raw) if flip else (raw, fin)
        q = rec["request"]
        doc = {
            "n": n,
            "round": args.round,
            "name": q["name"],
            "lang": q["language"],
            "tone": q["tone"],
            "recipient": q["recipient"],
            "traits": q["traits"],
            "detail": q["detail"],
            # no syllable counts on the page: off-count lines would tell the raw side apart
            "a": {"stanzas": left["stanzas"], "syllables": []},
            "b": {"stanzas": right["stanzas"], "syllables": []},
        }
        pid = f"{args.prefix}{n:04d}"
        (out / "pairs" / f"{pid}.json").write_text(json.dumps(doc, ensure_ascii=False), "utf-8")
        key[pid] = {"a": "finished" if flip else "raw", "b": "raw" if flip else "finished",
                    "batch": rec["id"], "syllables_a": left["syllables"],
                    "syllables_b": right["syllables"]}  # fmt: skip
    key_path = out / "pairs_key.json"
    merged = json.loads(key_path.read_text()) if key_path.exists() else {}
    merged.update(key)  # earlier rounds' keys are kept
    key_path.write_text(json.dumps(merged, indent=1), encoding="utf-8")
    print(
        f"{len(key)} pairs -> {out / 'pairs'}; key -> {key_path}; left out (same text or no draft): {skipped}"
    )


if __name__ == "__main__":
    main()

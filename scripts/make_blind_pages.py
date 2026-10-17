#!/usr/bin/env python3
"""Build the blind-pair data for scripts/blind_rating (poems and keys stay out of git).

Two sets, both Spanish, matched on theme and seed so the two poems answer the same request:

- ``v4``: the 20 pairs of the first blind page (plain vs adapter v4, b26), keyed by
  ``data/distill/blind-key-v4-es-2026-10-16.json``;
- ``lexi``: plain vs the lexicographic ranking penalties (b35), 20 pairs drawn with a fixed seed;
  A/B is shuffled per pair and the key is written next to the data.

    python scripts/make_blind_pages.py --out data/distill/blind-pages
"""

from __future__ import annotations

import argparse
import glob
import json
import random
from pathlib import Path

B26 = "reports/eval_2026-10/b26-kaggle-q4-adapter-v4-t06"
B35 = "reports/eval_2026-10/b35-cscs-8b-lexicographic-t06"


def poems(pattern: str, lang: str = "es") -> dict[tuple[str, int], list[str]]:
    out: dict[tuple[str, int], list[str]] = {}
    for f in sorted(glob.glob(pattern)):
        for p in json.load(open(f, encoding="utf-8"))["languages"][lang]["poems"]:
            out[(p["theme"], p["seed"])] = p["lines"]
    return out


def v4_set(key_path: Path) -> tuple[dict, dict]:
    key = json.load(open(key_path, encoding="utf-8"))
    src = {"plain": poems(f"{B26}/plain-s*-es.json"), "v4": poems(f"{B26}/lora-s*-es.json")}
    pairs = []
    for pid, k in sorted(key.items()):
        t = (k["theme"], k["seed"])
        pairs.append({"id": pid, "theme": k["theme"], "A": src[k["A"]][t], "B": src[k["B"]][t]})
    lede = (
        "Twenty pairs of Spanish sonnets on the same theme and seed, one from the plain model "
        "and one from an adapted version. The order is hidden and shuffled."
    )
    return {"id": "v4", "title": "Set 1: adapter v4", "lede": lede, "pairs": pairs}, key


def lexi_set(n: int = 20, seed: int = 17) -> tuple[dict, dict]:
    plain, lexi = poems(f"{B35}/plain2-s*-es.json"), poems(f"{B35}/lexi-s*-es.json")
    common = sorted(set(plain) & set(lexi))
    rng = random.Random(seed)
    rng.shuffle(common)
    pairs, key = [], {}
    for i, t in enumerate(common[:n], 1):
        sides = [("plain", plain[t]), ("lexi", lexi[t])]
        rng.shuffle(sides)
        pid = f"q{i:02d}"
        pairs.append({"id": pid, "theme": t[0], "A": sides[0][1], "B": sides[1][1]})
        key[pid] = {"A": sides[0][0], "B": sides[1][0], "theme": t[0], "seed": t[1]}
    lede = (
        "Twenty pairs of Spanish sonnets on the same theme and seed from the same model: one "
        "plain, one with a ranking that avoids repeating words and openings. The order is hidden "
        "and shuffled."
    )
    return {
        "id": "lexi",
        "title": "Set 2: ranking against repetition",
        "lede": lede,
        "pairs": pairs,
    }, key


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--v4-key", default="data/distill/blind-key-v4-es-2026-10-16.json")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    s1, k1 = v4_set(Path(args.v4_key))
    s2, k2 = lexi_set()
    (out / "pairs.json").write_text(
        json.dumps({"sets": [s1, s2]}, ensure_ascii=False), encoding="utf-8"
    )
    (out / "blind-keys.json").write_text(
        json.dumps({"v4": k1, "lexi": k2}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"{out}/pairs.json: sets v4 ({len(s1['pairs'])}), lexi ({len(s2['pairs'])}); keys written"
    )


if __name__ == "__main__":
    main()

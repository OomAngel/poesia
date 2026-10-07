#!/usr/bin/env python3
"""Re-rank src/poesia/wordlists/<lang>.txt so words used in poems come first.

The lists start as the 40,000 most frequent words of everyday text (wordfreq, see the
folder's README), which favours office vocabulary as rhymes ("información" for "corazón").
This keeps the same words but orders them by how often they occur in the poems PoesIA may
show (the linking sources: Project Gutenberg, the CC0 public-domain-poetry set, DISCO, and
the Italian linking-only books), then by everyday frequency. Only counts leave the corpus;
no text does.

    python scripts/rank_wordlists_by_poetry.py      # rewrites the three lists in place
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_linking_index import LINKING_ONLY, MASTER, _showable  # noqa: E402

LISTS = Path("src/poesia/wordlists")
MIN_COUNT = 3  # a word must occur this often in poems to be moved up
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def main() -> None:
    counts: dict[str, Counter[str]] = {"es": Counter(), "en": Counter(), "it": Counter()}
    for path in [MASTER, *sorted(LINKING_ONLY.glob("*.jsonl"))]:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                lang = r.get("language")
                if lang in counts and _showable(r):
                    counts[lang].update(w.lower() for w in WORD.findall(r["completion"]))
    for lang, poetic in counts.items():
        path = LISTS / f"{lang}.txt"
        words = [w for w in path.read_text(encoding="utf-8").split("\n") if w]
        order = {w: i for i, w in enumerate(words)}
        ranked = sorted(
            words,
            key=lambda w: (
                poetic[w] < MIN_COUNT,
                -poetic[w] if poetic[w] >= MIN_COUNT else 0,
                order[w],
            ),
        )
        path.write_text("\n".join(ranked) + "\n", encoding="utf-8")
        moved = sum(1 for w in words if poetic[w] >= MIN_COUNT)
        print(f"{lang}: {moved} of {len(words)} words occur in poems; first: {ranked[:8]}")


if __name__ == "__main__":
    main()

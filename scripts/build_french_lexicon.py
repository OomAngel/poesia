#!/usr/bin/env python3
"""Build the French word-class table (Wiktionary) for the French scanner.

Two spelling cases decide syllable counts and cannot be told from the letters alone:

- ``-ent``: silent in a verb's third-person plural (*chantent*, *aimaient*: flag ``v``),
  pronounced elsewhere (*souvent*, *moment*, *lent*: flag ``n``). Words that are both
  (*président*, *content*) get neither and fall back to the scanner's default.
- Verbs in ``-ier`` keep *i* apart from the next vowel in all their forms (*ou-bli-er*,
  *con-fi-é*, *ma-ri-ez*: flag ``d``), unlike nouns (*pre-mier*, *pi-tié*).

    curl -L -o ~/data/wiktionary/kaikki-French.jsonl \\
        https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl
    python scripts/build_french_lexicon.py ~/data/wiktionary/kaikki-French.jsonl

Writes src/poesia/phonology/data/fr_words.tsv (Wiktionary content: CC BY-SA 4.0), limited to
the word list and the words of the Métrique en Ligne gold set.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

OUT = Path("src/poesia/phonology/data/fr_words.tsv")
GOLD = Path("data/external/averell/metrique-en-ligne-master/json")
WORDLIST = Path("src/poesia/wordlists/fr.txt")
WORD = re.compile(r"^[a-zàâäéèêëîïôöùûüçœæ]+$")


def _vocabulary() -> set[str]:
    words = set(WORDLIST.read_text(encoding="utf-8").split())
    for path in GOLD.glob("*.json"):
        for poem in json.loads(path.read_text(encoding="utf-8")):
            for stanza in poem.get("text", []):
                for v in stanza:
                    words.update(re.findall(r"[a-zàâäéèêëîïôöùûüçœæ]+", v["verse"].lower()))
    return words


def main() -> None:
    src = Path(sys.argv[1]).expanduser()
    flags: dict[str, set[str]] = collections.defaultdict(set)
    nonverb: set[str] = set()
    with src.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            word = d.get("word", "").lower()
            pos = d.get("pos")
            if not WORD.match(word):
                continue
            if pos in ("noun", "adj", "adv"):
                nonverb.add(word)
            if pos == "verb":
                ier = word.endswith("ier")
                for form in d.get("forms", []):
                    w = form.get("form", "").lower()
                    tags = set(form.get("tags") or [])
                    if not WORD.match(w):
                        continue
                    if w.endswith("ent") and {"third-person", "plural"} <= tags:
                        flags[w].add("v")
                    if ier and re.search(r"i[aeéèêo]", w[len(word) - 4 :]):
                        flags[w].add("d")
                    elif (
                        not ier
                        and re.search(r"[^aeiouy]i(ons|ez)$", w)
                        and (
                            {"first-person", "plural"} <= tags
                            or {"second-person", "plural"} <= tags
                        )
                    ):
                        flags[w].add("s")  # é-tions, sa-vions, chan-tiez: one syllable
                if ier:
                    flags[word].add("d")
            elif word.endswith("ent") and pos in (
                "noun",
                "adj",
                "adv",
                "prep",
                "conj",
                "num",
                "pron",
            ):
                flags[word].add("n")
    for w in nonverb:
        flags.get(w, set()).discard("d")  # fier (proud) is not se fier: keep one syllable
    vocab = _vocabulary()
    rows = []
    both = 0
    for word in sorted(vocab):
        f = flags.get(word)
        if not f:
            continue
        if {"v", "n"} <= f:
            both += 1
            f = f - {"v", "n"}
        if f:
            rows.append((word, "".join(sorted(f))))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        fh.write(
            "# word<TAB>flags: v = verb -ent silent, n = -ent pronounced, d = -ier verb (diérèse), s = verb -ions/-iez (synérèse).\n"
        )
        fh.write(
            "# From Wiktionary via kaikki.org (CC BY-SA 4.0); built by scripts/build_french_lexicon.py.\n"
        )
        for word, f in rows:
            fh.write(f"{word}\t{f}\n")
    c = collections.Counter(ch for _w, f in rows for ch in f)
    print(
        f"vocabulary {len(vocab)}; written {len(rows)}; flags {dict(c)}; -ent both ways (left to rule) {both}"
    )


if __name__ == "__main__":
    main()

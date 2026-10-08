#!/usr/bin/env python3
"""Build the German syllable and stress table (Wiktionary) for the German scanner.

German stress is counted from the start of the word and stays there in inflected forms
(*verlieren* / *verliert* / *verlor*), so each lemma's stressed syllable, read from its IPA
(``/fɛrˈliːrən/`` -> 1), is passed to its forms. Syllable counts stay with the scanner's rules:
Wiktionary's hyphenation follows dictionary splitting (*Mu-ni-ti-on*, *Mo-sche-en*, never a
one-letter *A-bend*) and scored lower on the gold lines (98.9% against 99.1%), so the column
is kept for later use and written as -1.

    curl -L -o ~/data/wiktionary/kaikki-German.jsonl \\
        https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl
    python scripts/build_german_lexicon.py ~/data/wiktionary/kaikki-German.jsonl

Writes src/poesia/phonology/data/de_words.tsv (Wiktionary content: CC BY-SA 4.0), limited to
words the rules get wrong, for the word list and the gold lines.
"""

from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

from poesia.phonology.german import _rule_nuclei, _rule_stress

OUT = Path("src/poesia/phonology/data/de_words.tsv")
GOLD = Path(
    "data/external/metrical-tagging/data/German/SmallGold/antikoerperchen.lines.prosody.emotions.v4.tsv"
)
WORDLIST = Path("src/poesia/wordlists/de.txt")
WORD = re.compile(r"^[a-zäöüß]+$")
IPA_NUCLEUS = re.compile(r"(?:aɪ|aʊ|ɔʏ|ɔɪ|[aeiouyɛɪɔʊøœəɐʏæɑ])[ːˑ]?(?!̯)")


def _ipa_stress(ipa: str) -> int | None:
    body = ipa.strip("/[]").split(",")[0]
    if body.count("ˈ") != 1 or " " in body:
        return None
    before = body.split("ˈ")[0].replace("̯", "")
    return len(IPA_NUCLEUS.findall(before))


def _vocabulary() -> set[str]:
    words = set(WORDLIST.read_text(encoding="utf-8").split())
    with GOLD.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            words.update(re.findall(r"[a-zäöüß]+", r["line_text"].lower()))
    return words


def main() -> None:
    src = Path(sys.argv[1]).expanduser()
    stress: dict[str, set[int]] = collections.defaultdict(set)
    inherited: dict[str, set[int]] = collections.defaultdict(set)
    with src.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            word = d.get("word", "").lower()
            if not WORD.match(word):
                continue
            k = next(
                (
                    x
                    for s in d.get("sounds", [])
                    if "ipa" in s and (x := _ipa_stress(s["ipa"])) is not None
                ),
                None,
            )
            if k is None:
                continue
            stress[word].add(k)
            for form in d.get("forms", []):
                w = form.get("form", "").lower()
                if WORD.match(w) and w[:3] == word[:3]:
                    inherited[w].add(k)
    for w, ks in inherited.items():
        if w not in stress:
            stress[w] = ks
    rows = []
    for word in sorted(_vocabulary()):
        rule_n = len(_rule_nuclei(word))
        n = -1  # syllables: the rules (see the docstring)
        ks = stress.get(word, set())
        k = next(iter(ks)) if len(ks) == 1 else -1
        total = n if n > 0 else rule_n
        if k >= total or k == _rule_stress(word, total) or total <= 1:
            k = -1  # out of range, or the rules already place it
        if n > 0 or k >= 0:
            rows.append((word, n, k))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        fh.write(
            "# word<TAB>syllables (-1: rules)<TAB>stressed syllable from the start (-1: rules).\n"
        )
        fh.write(
            "# From Wiktionary via kaikki.org (CC BY-SA 4.0); built by scripts/build_german_lexicon.py.\n"
        )
        for word, n, k in rows:
            fh.write(f"{word}\t{n}\t{k}\n")
    print(
        f"written {len(rows)}: syllable overrides {sum(n > 0 for _w, n, _k in rows)}, "
        f"stress overrides {sum(k >= 0 for _w, _n, k in rows)}"
    )


if __name__ == "__main__":
    main()

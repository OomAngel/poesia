#!/usr/bin/env python3
"""Build the Italian stress exceptions the scanner's rule gets wrong, from Wiktionary.

The Italian scanner stresses the second-to-last syllable unless a written accent says
otherwise, so unmarked words stressed earlier (*crescita*, *tavola*, *subito*) are scanned
wrong. Wiktionary marks the stressed vowel in its hyphenation (``crè‧sci‧ta``) and in its IPA
(``/ˈkreʃ.ʃi.ta/``); kaikki.org publishes it as JSON lines. This keeps, for words of the given
vocabulary, every case where Wiktionary's stress differs from the scanner's rule, as the
syllable counted from the end (0 = last). Words with entries that disagree (*àncora* /
*ancóra*) are left to the rule. Nouns and adjectives pass their stress to inflected forms of
the same length (*tavola* -> *tavole*); verbs do not (their stress moves).

    curl -L -o ~/data/wiktionary/kaikki-Italian.jsonl \\
        https://kaikki.org/dictionary/Italian/kaikki.org-dictionary-Italian.jsonl
    python scripts/build_italian_stress.py ~/data/wiktionary/kaikki-Italian.jsonl

Writes src/poesia/phonology/data/it_stress.tsv (Wiktionary content: CC BY-SA 4.0).
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

from poesia.phonology.italian import _ACCENTED, _nuclei, _stress_nucleus

OUT = Path("src/poesia/phonology/data/it_stress.tsv")
GOLD = Path("data/external/averell/biblioteca_italiana-master/json")
WORDLIST = Path("src/poesia/wordlists/it.txt")
WORD = re.compile(r"^[a-zàèéìíòóùú]+$")


def _from_hyphenation(parts: list[str]) -> int | None:
    # kaikki gives ["cré‧sci‧ta"] (one string, U+2027 separators) as well as split lists.
    parts = [p for part in parts for p in re.split("[‧·.-]", part) if p]
    hits = [i for i, p in enumerate(parts) if any(c in _ACCENTED for c in p)]
    return len(parts) - 1 - hits[0] if len(hits) == 1 else None


def _from_ipa(ipa: str) -> int | None:
    body = ipa.strip("/[]")
    if body.count("ˈ") != 1 or " " in body:
        return None
    syllables = re.split(r"[.ˈ]", body)
    syllables = [s for s in syllables if s]
    before = re.split(r"[.ˈ]", body.split("ˈ")[0])
    index = len([s for s in before if s])
    return len(syllables) - 1 - index


def _vocabulary() -> set[str]:
    words = set(WORDLIST.read_text(encoding="utf-8").split())
    for path in GOLD.glob("*.json"):
        for poem in json.loads(path.read_text(encoding="utf-8")):
            for stanza in poem.get("text", []):
                for v in stanza:
                    words.update(re.findall(r"[a-zàèéìíòóùúïü]+", v["verse"].lower()))
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
            k = None
            for h in d.get("hyphenations", []):
                k = _from_hyphenation(h.get("parts", []))
                if k is not None:
                    break
            if k is None:
                for s in d.get("sounds", []):
                    if "ipa" in s and (k := _from_ipa(s["ipa"])) is not None:
                        break
            if k is None:
                continue
            stress[word].add(k)
            if d.get("pos") in ("noun", "adj"):
                n = len(_nuclei(word))
                for form in d.get("forms", []):
                    w = form.get("form", "").lower()
                    if WORD.match(w) and len(_nuclei(w)) == n:
                        inherited[w].add(k)
    for w, ks in inherited.items():
        if w not in stress:
            stress[w] = ks
    vocab = _vocabulary()
    rows, ambiguous, agree = [], 0, 0
    for word in sorted(vocab):
        ks = stress.get(word)
        if not ks:
            continue
        if len(ks) > 1:
            ambiguous += 1
            continue
        (k,) = ks
        nuc = _nuclei(word)
        if not nuc or k >= len(nuc):
            continue
        rule = len(nuc) - 1 - _stress_nucleus(word, nuc)
        if rule == k:
            agree += 1
        else:
            rows.append((word, k))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        f.write("# word<TAB>stressed syllable from the end (0 = last). From Wiktionary via\n")
        f.write("# kaikki.org (CC BY-SA 4.0); built by scripts/build_italian_stress.py.\n")
        for word, k in rows:
            f.write(f"{word}\t{k}\n")
    print(
        f"vocabulary {len(vocab)}; with Wiktionary stress {agree + len(rows) + ambiguous}; "
        f"rule right {agree}; exceptions written {len(rows)}; ambiguous skipped {ambiguous}"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check the French rhyme sound against eSpeak NG on the most frequent line-final words.

The Métrique en Ligne rhyme letters are not reliable pairwise (pairs marked alike include
*cieux* / *lointains*), so the rhyme key is compared with an independent pronouncer instead:
eSpeak NG's IPA for the same words, from the last vowel to the end. eSpeak is not ground
truth either (it reads *froment* as /fʁom/); ``--show`` lists disagreements for review.

    sudo apt install espeak-ng
    python scripts/check_french_rhyme.py [--top 3000] [--show 20]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
from pathlib import Path

from poesia.phonology.french import _ending_sound, _tokens

GOLD = Path("data/external/averell/metrique-en-ligne-master/json")
VOWELS = "aɑeɛiouyøœəɔAEO"


def _norm(ipa: str) -> str:
    """One notation for both sides: r for ʁ, nasals as capitals, o/ɔ, ø/œ, a/ɑ and e/ɛ merged."""
    for a, b in (
        ("ˈ", ""),
        ("ˌ", ""),
        ("ː", ""),
        ("ʁ", "r"),
        ("ɡ", "g"),
        ("ɑ̃", "A"),
        ("ɛ̃", "E"),
        ("ɔ̃", "O"),
        ("œ̃", "E"),
        ("ɔ", "o"),
        ("œ", "ø"),
        ("ɑ", "a"),
        ("ɛ", "e"),
    ):
        ipa = ipa.replace(a, b)
    return ipa


def _espeak_tail(ipa: str) -> str:
    x = re.sub(r"ə$", "", _norm(ipa))
    idx = max((i for i, c in enumerate(x) if c in VOWELS), default=-1)
    return x[idx:] if idx >= 0 else x


def _ours(word: str) -> str:
    vowel, coda = _ending_sound(word)
    return _norm((vowel + coda).replace("ə", "")).lstrip("w")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--top", type=int, default=3000)
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()
    words: collections.Counter[str] = collections.Counter()
    for path in sorted(GOLD.glob("*.json")):
        for poem in json.loads(path.read_text(encoding="utf-8")):
            for stanza in poem.get("text", []):
                for v in stanza:
                    tokens = _tokens(v["verse"])
                    if tokens:
                        words[tokens[-1].split("'")[-1]] += 1
    top = [w for w, _n in words.most_common(args.top)]
    out = subprocess.run(
        ["espeak-ng", "-q", "--ipa", "-v", "fr"],
        input="\n".join(top),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    ipa = [x.strip() for x in out.split("\n") if x.strip()]
    pairs = list(zip(top, ipa, strict=True))
    bad = [(w, _ours(w), _espeak_tail(x)) for w, x in pairs if _ours(w) != _espeak_tail(x)]
    print(
        f"rhyme sound vs eSpeak NG, {len(pairs)} most frequent line-final words: {1 - len(bad) / len(pairs):.1%}"
    )
    for w, a, b in bad[: args.show]:
        print(f"  {w}: ours {a}, eSpeak {b}")


if __name__ == "__main__":
    main()

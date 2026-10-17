"""Spanish rhyme keys by sound, not spelling, with a dialect switch.

A rhyme runs from the stressed vowel of the last word to its end, compared as it sounds:
silent h, b/v, ll/y (yeísmo), qu/k, g/j before e/i, and with ``variety="seseo"`` (Mexico,
Latin America, Canarias, Andalucía; the default) s/z/c before e/i are one sound, so
"casa"/"caza" rhyme; ``variety="distincion"`` keeps z and c(e,i) apart (central and northern
Spain). The stressed vowel is found from nuclei, so a falling diphthong is read right
("historia" -> "oria", "tierra" -> "erra"), which the spelling key before 2026-10-10 got
wrong: it rhymed historia/alegría and agua/tregua (6.4% of the Spanish rhyme pairs counted in
the October reports were false). On the quatrains of 100 ADSO sonnets (lines 1-4-5-8 and
2-3-6-7 must rhyme), this key matches 98.5% of the groups (the spelling key 96.0%) and never
matches the two groups to each other. The assonant key keeps one vowel per nucleus of the tail.

Moved here from the Calaveritas service (``calaveritas/rhyme.py``), where it was written for
Mexican Spanish, so every PoesIA deployment uses one key.
"""

from __future__ import annotations

import re

from poesia.phonology.base import RhymeKey

_ACCENTED = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}
_STRONG = set("aeo")
_VOWELS = set("aeiou")
# x sounds like j in these names (Mexico); elsewhere x is ks
_X_AS_J = ("méxico", "mexico", "mexicano", "mexicana", "oaxaca", "texas", "xalapa", "ximena")
VARIETIES = ("seseo", "distincion")


def _last_word(line: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿ'’]+", line)
    return words[-1].lower() if words else ""


def _phonetic(text: str, variety: str) -> str:
    """Spell a lowercase fragment (stress marks removed, ü kept) the way it sounds."""
    s = re.sub(r"ch", "C", text)  # protect ch before dropping h
    s = s.replace("h", "").replace("C", "ch")
    s = re.sub(r"qu([ei])", r"k\1", s)
    s = re.sub(r"gu([ei])", r"g\1", s)  # guerra -> gerra (hard g)
    s = s.replace("gü", "gw")  # pingüino -> pingwino (the u is heard)
    s = re.sub(r"g([ei])", r"j\1", s)  # gente -> jente
    if variety == "seseo":
        s = re.sub(r"c([ei])", r"s\1", s).replace("z", "s")
    else:
        s = re.sub(r"c([ei])", r"z\1", s)
    s = s.replace("c", "k").replace("q", "k")
    s = s.replace("x", "ks")
    s = re.sub(r"(?<!g)w", "b", s.replace("v", "b"))
    s = s.replace("ll", "y")
    return re.sub(r"y$", "i", s)  # rey -> rei


def _base(ch: str) -> str:
    return "u" if ch == "ü" else _ACCENTED.get(ch, ch)


def _nuclei(word: str) -> list[tuple[int, int, bool]]:
    """Vowel nuclei as (start, end, has_written_accent); a diphthong is one nucleus."""
    out: list[tuple[int, int, bool]] = []
    i = 0
    while i < len(word):
        if _base(word[i]) not in _VOWELS:
            i += 1
            continue
        start, accented, j = i, word[i] in "áéíóú", i + 1
        while j < len(word) and _base(word[j]) in _VOWELS:
            prev, nxt = _base(word[j - 1]), _base(word[j])
            # hiatus: two strong vowels, or an accented weak vowel next to another vowel
            if (prev in _STRONG and nxt in _STRONG) or word[j] in "íú" or word[j - 1] in "íú":
                break
            accented = accented or word[j] in "áéíóú"
            j += 1
        out.append((start, j, accented))
        i = j
    return out


def _stressed(word: str, nuclei: list[tuple[int, int, bool]]) -> tuple[int, int, bool]:
    marked = next((n for n in nuclei if n[2]), None)
    if marked is not None:
        return marked
    llana = word[-1] in "aeiouns"
    return nuclei[-2] if llana and len(nuclei) >= 2 else nuclei[-1]


def spanish_rhyme_key(line: str, variety: str = "seseo") -> RhymeKey:
    """Consonant and assonant rhyme of the line's last word, by sound."""
    if variety not in VARIETIES:
        raise ValueError(f"variety must be one of {VARIETIES}")
    word = _last_word(line)
    if not word:
        return RhymeKey("", "")
    if word in _X_AS_J:
        word = word.replace("x", "j")
    nuclei = _nuclei(word)
    if not nuclei:
        return RhymeKey(word, "")
    start, end, _ = _stressed(word, nuclei)
    # inside a diphthong the rhyme starts at the strong vowel (tierra -> erra, cuento -> ento)
    seg = word[start:end]
    offset = 0
    if len(seg) > 1:
        strong = [k for k, c in enumerate(seg) if _base(c) in _STRONG or c in "áéíóú"]
        offset = strong[0] if strong else len(seg) - 1
    tail = word[start + offset :]
    plain = "".join(_ACCENTED.get(c, c) for c in tail)
    vowels: list[str] = []
    for s, e, _ in _nuclei(tail):
        nucleus = "".join(_base(c) for c in tail[s:e])
        strong_vowels = [c for c in nucleus if c in _STRONG]
        vowels.append(strong_vowels[0] if strong_vowels else nucleus[-1])
    return RhymeKey(_phonetic(plain, variety), "".join(vowels))

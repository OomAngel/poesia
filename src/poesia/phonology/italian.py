"""Italian phonology / scansion backend (pure Python, no dependencies).

Italian metre counts syllables up to the last stressed one, plus one: an *endecasillabo*
has its last stress on the 10th position. Rules implemented:

- Syllable nuclei per word: a weak vowel (i, u) beside another vowel forms one nucleus
  (*cuore*, *piano*, *mai*, *miei*); two strong vowels (a, e, o) are a hiatus (*pa-e-se*).
  An accent or diaeresis on i/u keeps it separate (*mì-a*, *ï*).
- Sinalefe: a word ending in a vowel and the next beginning with a vowel (or h + vowel)
  share one position; chains of vowels collapse together. Elided forms (*l'altrui*,
  *d'un*) are already one word.
- Line ending: *piano* (stress on the penultimate) counts as written; *tronco* (accented
  final vowel, final consonant as in *amor*, or a final monosyllable) adds one; a
  *sdrucciolo* is recognised only when the antepenultimate vowel carries a written accent.

- Sineresi: two unaccented strong vowels inside a word share a position (*parea*, *aere*);
  a final falling diphthong in a longer word carries the stress (*trovai*, *andrei*).

Known limits: unmarked *sdruccioli* (*anima*, *tavola*); dialefe (no merging after a
stressed final vowel), which Dante uses more than Petrarca: adding it helped one and hurt
the other on the gold set, so it is left out.
Checked against the expert-annotated endecasillabi of Biblioteca Italiana (Dante,
Petrarca): see ``scripts/check_italian_scansion.py``.
"""

from __future__ import annotations

import functools
import re
import unicodedata
from importlib import resources

from poesia.phonology.base import RhymeKey, ScanResult, Stress

_ACCENTED = "àèéìíòóùú"
_DIAERESIS = "ïü"
VOWELS = set("aeiou" + _ACCENTED + _DIAERESIS)
_WEAK = set("iu")
_STRONG = set("aeo" + "àèéòó")


def _plain(ch: str) -> str:
    return unicodedata.normalize("NFD", ch)[0]


# Words whose i/u carries the stress beside another vowel, so the two stay apart (hiatus):
# mì-o, vì-a, fù-i. Inside a line most of them merge (sineresi: "mio" is one syllable), so
# they are split only at the line end, where dieresi is the rule. "io" and "paura" split
# everywhere. (Measured on the gold set: splitting everywhere lowered exact agreement.)
_STRESSED_WEAK_ANYWHERE = {"io": "ìo", "paura": "paùra", "paure": "paùre"}
_STRESSED_WEAK_AT_END = {
    "mio": "mìo",
    "mia": "mìa",
    "mie": "mìe",
    "tuo": "tùo",
    "tua": "tùa",
    "tue": "tùe",
    "suo": "sùo",
    "sua": "sùa",
    "sue": "sùe",
    "via": "vìa",
    "vie": "vìe",
    "dio": "dìo",
    "sia": "sìa",
    "fia": "fìa",
    "pria": "prìa",
    "zio": "zìo",
    "rio": "rìo",
    "ria": "rìa",
    "pio": "pìo",
    "pia": "pìa",
    "due": "dùe",
    "bue": "bùe",
    "fui": "fùi",
    "lui": "lùi",
}


def _word(token: str) -> str:
    """Lowercase letters only; apostrophes join elided forms (``l'altrui`` -> ``laltrui``).

    A silent h is dropped (``ahi`` -> ``ai``), except in the digraphs ch, gh.
    """
    token = token.lower().replace("’", "'")
    word = "".join(c for c in token if c.isalpha())
    word = re.sub(r"(?<![cg])h", "", word)
    return _STRESSED_WEAK_ANYWHERE.get(word, word)


def _glides(ch: str, nxt: str) -> bool:
    """True when two adjacent vowels share one nucleus."""
    if not nxt or ch in _DIAERESIS or nxt in _DIAERESIS:
        return False
    return (
        (ch in _WEAK and nxt in VOWELS and _plain(nxt) != ch)  # rising: ie, uo, ia
        or (ch in _STRONG and nxt in _WEAK)  # falling: ai, ei, oi, au
        or (ch in "aeo" and nxt in "aeo")  # sineresi: pa-rea, ae-re (unaccented strong pair)
    )


def _stressable(seg: str) -> int:
    """Position of the vowel that can carry stress: accented, else strong, else the last."""
    pos = next((p for p, c in enumerate(seg) if c in _ACCENTED), None)
    if pos is None:
        pos = next((p for p, c in enumerate(seg) if c in _STRONG), len(seg) - 1)
    return pos


def _split_group(group: str, offset: int) -> list[tuple[int, int, int]]:
    """Nuclei of one run of adjacent vowels starting at ``offset`` in the word."""
    spans = []
    start = 0
    for k, ch in enumerate(group):
        if _glides(ch, group[k + 1] if k + 1 < len(group) else ""):
            continue
        seg = group[start : k + 1]
        spans.append((offset + start, offset + k + 1, offset + start + _stressable(seg)))
        start = k + 1
    return spans


def _nuclei(word: str) -> list[tuple[int, int, int]]:
    """Vowel nuclei of a word as (start, end, index of the stressable vowel)."""
    return [
        span
        for m in re.finditer(f"[{''.join(sorted(VOWELS))}]+", word)
        for span in _split_group(m.group(0), m.start())
    ]


@functools.cache
def _stress_exceptions() -> dict[str, int]:
    """Words whose stress the rule below gets wrong, from Wiktionary (data/it_stress.tsv):
    word -> stressed syllable counted from the end. Built by scripts/build_italian_stress.py."""
    text = resources.files("poesia.phonology").joinpath("data/it_stress.tsv").read_text("utf-8")
    out = {}
    for line in text.splitlines():
        if line and not line.startswith("#"):
            word, k = line.split("\t")
            out[word] = int(k)
    return out


def _stress_nucleus(word: str, nuclei: list[tuple[int, int, int]]) -> int:
    """Index (in ``nuclei``) of the stressed nucleus of a word."""
    if not nuclei:
        return -1
    for idx, (_s, _e, v) in enumerate(nuclei):
        if word[v] in _ACCENTED:
            return idx
    k = _stress_exceptions().get(word)
    if k is not None and k < len(nuclei):  # unmarked sdrucciolo etc. (crescita, tavola)
        return len(nuclei) - 1 - k
    if len(nuclei) == 1 or word[-1] not in VOWELS:  # monosyllable, or truncated (amor, cor)
        return len(nuclei) - 1
    if re.search(r"[aeo]i$", word):  # past and conditional endings: trovai, andrei, udii
        return len(nuclei) - 1
    return len(nuclei) - 2  # piano by default


def _starts_vowel(word: str) -> bool:
    return bool(word) and (
        word[0] in VOWELS or (word[0] == "h" and len(word) > 1 and word[1] in VOWELS)
    )


def _line_words(line: str) -> list[str]:
    words = [w for w in (_word(t) for t in line.split()) if w]
    if words:
        words[-1] = _STRESSED_WEAK_AT_END.get(words[-1], words[-1])
    return words


class ItalianPhonology:
    """Scans Italian verse lines (pure Python)."""

    def scan_line(self, line: str) -> ScanResult:
        words = _line_words(line)
        if not words:
            return ScanResult(line=line, metrical_syllable_count=0, is_valid=False)
        positions: list[Stress] = []
        for wi, word in enumerate(words):
            nuc = _nuclei(word)
            if not nuc:
                continue
            stressed = _stress_nucleus(word, nuc)
            marks = [
                Stress.PRIMARY
                if (k == stressed and (len(nuc) > 1 or wi == len(words) - 1))
                else Stress.UNSTRESSED
                for k in range(len(nuc))
            ]
            prev = words[wi - 1] if wi else ""
            if positions and prev and prev[-1] in VOWELS and _starts_vowel(word):
                # sinalefe: the first nucleus of this word shares the previous position
                first = marks.pop(0)
                if first is Stress.PRIMARY:
                    positions[-1] = Stress.PRIMARY
            positions.extend(marks)
        count = len(positions)
        last = words[-1]
        last_nuc = _nuclei(last)
        if last_nuc:
            stressed = _stress_nucleus(last, last_nuc)
            after = len(last_nuc) - 1 - stressed
            if after == 0:
                count += 1  # tronco: one position after the last stress
                positions.append(Stress.UNSTRESSED)
            elif after == 2:
                count -= 1  # sdrucciolo (only when written: the accent marked it)
                positions.pop()
        return ScanResult(
            line=line,
            metrical_syllable_count=count,
            stress_pattern=tuple(positions),
            is_valid=count > 0,
        )

    def rhyme_key(self, line: str) -> RhymeKey:
        """From the stressed vowel of the last word to its end (``cuore``/``amore`` -> ``ore``)."""
        words = _line_words(line)
        if not words:
            return RhymeKey(consonant="", assonant="")
        last = words[-1]
        nuc = _nuclei(last)
        if not nuc:
            return RhymeKey(consonant=last, assonant="")
        tail = last[nuc[_stress_nucleus(last, nuc)][2] :]
        plain = "".join(_plain(c) for c in tail)
        return RhymeKey(consonant=plain, assonant="".join(c for c in plain if c in "aeiou"))

    def classify_stanza(self, lines: list[str]) -> str | None:
        return {14: "sonetto", 4: "quartina", 3: "terzina", 8: "ottava"}.get(len(lines))

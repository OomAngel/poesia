"""German phonology / scansion backend (pure Python, no dependencies).

German metre is accentual-syllabic: a line has a number of syllables and a pattern of stressed
and unstressed ones (*Ich muß hinaus, ich muß zu dir* = ``-+-+-+-+``, iambic tetrameter).

- Syllables: one per vowel nucleus; *aa ee oo ie ei ai au eu äu ey ay ui* are one nucleus.
  A vowel after *ie*, or *i-e* in words like *Familie*, follows the Wiktionary table.
  Poetic elision is written (*hab'*, *ew'gen*) and needs no rule.
- Word stress: the Wiktionary table (stressed syllable counted from the start, so inflected
  forms inherit it: *verlieren* / *verliert*), else rules: unstressed prefixes (*be- ge- er-
  ver- zer- ent- emp-*) push stress to the next syllable, a few foreign suffixes take it
  (*-ieren*, *-ei*, *-tion*, *-ität*), otherwise the first syllable. Function-word
  monosyllables (*der*, *und*, *ich*) are unstressed; other monosyllables stressed.
- Rhyme: from the stressed vowel of the last word, by sound (*Herz* / *Schmerz*, *Tag* /
  *lag*, *Leid* / *Zeit*).

Checked against the expert-annotated lines of Haider et al. (metrical-tagging-in-the-wild,
German small gold): see ``scripts/check_german_scansion.py``.
"""

from __future__ import annotations

import functools
import re
from importlib import resources

from poesia.phonology.base import RhymeKey, ScanResult, Stress

VOWELS = set("aeiouyäöü")
_NUCLEI = re.compile(r"äu|eu|ei|ai|au|ey|ay|ie|aa|ee|oo|ui(?=$|[^aeiouäöü])|[aeiouyäöü]")
_UNSTRESSED_PREFIX = re.compile(r"^(?:be|ge|er|ver|zer|ent|emp|miss)(?=[a-zäöüß])")
_STRESSED_SUFFIX = re.compile(
    r"(?:ieren|ierend|iert|ierte|ierten|ei|eien|tion|tionen|ität|itäten|ur|uren|ist|isten)$"
)


@functools.cache
def _function_words() -> frozenset[str]:
    """Monosyllables scanned unstressed (data/de_function_words.txt: der, und, ich, ...)."""
    text = (
        resources.files("poesia.phonology")
        .joinpath("data/de_function_words.txt")
        .read_text("utf-8")
    )
    return frozenset(w for w in text.split() if not w.startswith("#"))


@functools.cache
def _table() -> dict[str, tuple[int, int]]:
    """Wiktionary syllable counts and stress (data/de_words.tsv): word -> (syllables, stressed
    syllable counted from the start, -1 unknown). Built by scripts/build_german_lexicon.py."""
    try:
        text = resources.files("poesia.phonology").joinpath("data/de_words.tsv").read_text("utf-8")
    except (FileNotFoundError, OSError):
        return {}
    out = {}
    for line in text.splitlines():
        if line and not line.startswith("#"):
            word, n, k = line.split("\t")
            out[word] = (int(n), int(k))
    return out


def _word(token: str) -> str:
    token = token.lower().replace("’", "'")
    return "".join(c for c in token if c.isalpha() or c == "ß")


def _tokens(line: str) -> list[str]:
    return [w for w in (_word(t) for t in re.split(r"[\s\-–—/]+", line)) if w]


def _rule_nuclei(word: str) -> list[tuple[int, int]]:
    """Vowel nuclei as (start, end) by spelling rules. The u of qu is a consonant (Quelle);
    -ion and oe (Goethe) are one vowel."""
    masked = re.sub(r"(?<=q)u", "w", word)
    masked = re.sub(r"i(?=on)", "j", masked)
    masked = re.sub(r"(?<=o)e", "h", masked) if re.search(r"oe(?![aeiouäöü])", masked) else masked
    return [(m.start(), m.end()) for m in _NUCLEI.finditer(masked)]


def _syllable_count(word: str) -> int:
    entry = _table().get(word)
    if entry and entry[0] > 0:
        return entry[0]
    return len(_rule_nuclei(word))


def _rule_stress(word: str, n: int) -> int:
    if n <= 1:
        return 0
    if _STRESSED_SUFFIX.search(word):
        return (
            n - 1
            if not word.endswith(
                ("ieren", "ierend", "ierte", "ierten", "tionen", "itäten", "uren", "isten", "eien")
            )
            else n - 2
        )
    if _UNSTRESSED_PREFIX.match(word):
        return 1
    return 0


def _stress_index(word: str, n: int) -> int:
    """Stressed syllable counted from the start."""
    entry = _table().get(word)
    if entry and 0 <= entry[1] < n:
        return entry[1]
    return _rule_stress(word, n)


def _word_marks(word: str) -> list[Stress]:
    n = _syllable_count(word)
    if n == 0:
        return []
    if n == 1:
        return [Stress.UNSTRESSED if word in _function_words() else Stress.PRIMARY]
    k = _stress_index(word, n)
    return [Stress.PRIMARY if i == k else Stress.UNSTRESSED for i in range(n)]


class GermanPhonology:
    """Scans German verse lines (pure Python)."""

    def scan_line(self, line: str) -> ScanResult:
        """``metrical_syllable_count`` runs to the last stressed syllable, as German verse
        names its lines (a five-stress line has 10 with a masculine ending, *Herz*, and 10 plus
        an unstressed one with a feminine ending, *Liebe*); ``stress_pattern`` has them all.
        The line's last word always carries a stress (*zu DIR*)."""
        words = _tokens(line)
        positions: list[Stress] = []
        for i, word in enumerate(words):
            marks = _word_marks(word)
            if i == len(words) - 1 and len(marks) == 1:
                marks = [Stress.PRIMARY]
            positions.extend(marks)
        last = max(
            (i for i, m in enumerate(positions) if m is Stress.PRIMARY), default=len(positions) - 1
        )
        return ScanResult(
            line=line,
            metrical_syllable_count=last + 1 if positions else 0,
            stress_pattern=tuple(positions),
            is_valid=bool(positions),
        )

    def rhyme_key(self, line: str) -> RhymeKey:
        """From the stressed vowel of the last word, by sound."""
        words = _tokens(line)
        if not words:
            return RhymeKey(consonant="", assonant="")
        vowel, coda = _ending_sound(words[-1])
        return RhymeKey(consonant=vowel + coda, assonant=vowel)

    def classify_stanza(self, lines: list[str]) -> str | None:
        return {14: "Sonett", 4: "Quartett", 3: "Terzett"}.get(len(lines))


_VOWEL_SOUND = {
    "äu": "oi",
    "eu": "oi",
    "ei": "ai",
    "ai": "ai",
    "ey": "ai",
    "ay": "ai",
    "au": "au",
    "ie": "iː",
    "aa": "aː",
    "ee": "eː",
    "oo": "oː",
    "ä": "e",
    "ö": "ø",
    "ü": "y",
    "y": "y",
    "ui": "ui",
}
_CODA = (
    ("sch", "ʃ"),
    ("tsch", "tʃ"),
    ("ck", "k"),
    ("tz", "ts"),
    ("z", "ts"),
    ("ß", "s"),
    ("ch", "x"),
    ("ph", "f"),
    ("th", "t"),
    ("dt", "t"),
    ("v", "f"),
    ("qu", "kv"),
    ("x", "ks"),
    ("ng", "ŋ"),
)


def _coda(letters: str) -> str:
    letters = re.sub(r"^h(?=[^aeiouäöü]|$)", "", letters)  # Ruh, Sohn: lengthening h
    out = ""
    i = 0
    while i < len(letters):
        for spell, snd in _CODA:
            if letters.startswith(spell, i):
                out += snd
                i += len(spell)
                break
        else:
            out += letters[i]
            i += 1
    out = re.sub(r"(.)\1", r"\1", out)  # doubled consonants
    out = re.sub(r"b$", "p", out)
    out = re.sub(r"d$", "t", out)
    out = re.sub(r"g$", "k", out)  # final devoicing: Tag / lag / Wrack
    out = re.sub(r"n(?=k)", "ŋ", out)  # sinkt
    return out.replace("e", "ə")


def _last_full_nucleus(word: str, nuclei: list[tuple[int, int]]) -> int:
    """Index of the last nucleus that is not a weak e (-e, -el, -en, -end, -er, -ern, -es, -et):
    the rhyme starts there, also in compounds (Wolkenwand / Hand)."""
    k = len(nuclei) - 1
    while k > 0:
        start, end = nuclei[k]
        after = word[end : nuclei[k + 1][0]] if k + 1 < len(nuclei) else word[end:]
        if word[start:end] == "e" and re.fullmatch(r"(?:[lmnrst]|nd|ns|rn|rs|st)?", after):
            k -= 1
            continue
        break
    return k


def _impure(sound: str) -> str:
    """Rhymes German verse accepts: no vowel length, ö~e, ü~i, eu~ei (Behörden / werden)."""
    return sound.replace("ː", "").replace("ø", "e").replace("y", "i").replace("oi", "ai")


def _ending_sound(word: str) -> tuple[str, str]:
    """(vowel, rest) from the last full vowel of the word to its end, by sound."""
    nuclei = _rule_nuclei(word)
    if not nuclei:
        return "", word
    k = _last_full_nucleus(word, nuclei)
    start, end = nuclei[k]
    spell = word[start:end]
    vowel = _VOWEL_SOUND.get(spell, spell)
    tail = ""
    j = end
    for s2, e2 in nuclei[k + 1 :]:
        tail += _coda(word[j:s2]) + _VOWEL_SOUND.get(word[s2:e2], word[s2:e2]).replace("e", "ə")
        j = e2
    tail += _coda(word[j:])
    return _impure(vowel), _impure(tail)

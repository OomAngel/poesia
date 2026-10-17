"""Hard checks on a candidate line, one per defect.

Each check returns a ``Defect`` or ``None``. ``check_line`` runs them in a fixed order and
returns every defect found, so a repair can name what is wrong. The checks are deliberately
plain and testable; anything that needs a model (fluency, sense) is a ``Judge`` in ``rank``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from poesia.phonology.base import PhonologyBackend, ScanResult

_WORD = re.compile(r"[A-Za-zÀ-ÿ'’]+")
WORDLISTS = Path(__file__).resolve().parent.parent / "wordlists"


class Defect(StrEnum):
    METRE = "metre"  # target not among the licensed counts
    RHYME = "rhyme"  # does not rhyme with its partner (or rhymes with the same word)
    TACKED = "tacked"  # a single word tacked on after a comma: "La Calaca llega, coche."
    DANGLING = "dangling"  # ends on a function word: "y la Muerte llegó con"
    REPEATED = "repeated"  # the same line already exists
    OPENING = "opening"  # opens like another line of the stanza
    UNKNOWN_WORD = "unknown_word"  # a word in no frequency list (and not the name or traits)
    SHAPE = "shape"  # empty, one or two words, or too long to be a line
    # POETICS #3 "no repeated words in a poem" ("inmenso 3 veces"): a content word used again
    REPEATED_WORD = "repeated_word"
    # POETICS #2 "rhymes on clearly different words": the rhyme words are near-copies
    NEAR_COPY_RHYME = "near_copy_rhyme"


# Function words that cannot end a line (articles, prepositions, conjunctions, clitics).
FUNCTION_END: dict[str, frozenset[str]] = {
    "es": frozenset(
        "de y que a en la el los las con por para su sus mi tu un una lo se al del e o u ni "
        "mas pero si".split()
    ),
    "en": frozenset(
        "the a an and of to in on with for her his their my your but or at by from that".split()
    ),
    "it": frozenset("il lo la i gli le di a da in con su per e o ma che un una del della".split()),
    "de": frozenset(
        "der die das ein eine und oder aber mit von zu in an auf für dem den des".split()
    ),
    "fr": frozenset("le la les un une et ou mais de du des à au aux en dans sur pour par".split()),
    "nl": frozenset("de het een en of maar van in op met voor aan bij naar dat".split()),
}


def words(line: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(line)]


def end_word(line: str) -> str:
    ws = words(line)
    return ws[-1] if ws else ""


def opening(line: str) -> str:
    """First two words, lower-cased: the unit for opening clashes and diversity counts."""
    return " ".join(words(line)[:2])


def norm(line: str) -> str:
    return " ".join(words(line))


@dataclass(frozen=True)
class LineContext:
    """What a line is checked against."""

    language: str
    target: int | None = None  # metrical syllables; None skips the metre gate
    tolerance: int = 0  # extra slack around the licensed set (0 = the set decides)
    partner: str | None = None  # the line it must rhyme with, if any
    loose_rhyme: bool = False  # assonance accepted (romance, abcb)
    others: tuple[str, ...] = ()  # lines it must not repeat or open like
    allowed_words: frozenset[str] = frozenset()  # name, traits, detail: never "unknown"
    earlier: tuple[str, ...] = ()  # every line of the poem so far (for repeated words)
    check_vocabulary: bool = True


def metre(scan: ScanResult, target: int, tolerance: int = 0) -> Defect | None:
    counts = scan.metrical_counts or frozenset({scan.metrical_syllable_count})
    if any(abs(c - target) <= tolerance for c in counts):
        return None
    return Defect.METRE


# derivational prefixes (es, en, it): a rhyme word that only adds one is the same word
_PREFIXES = frozenset(
    "a an con contra de des en em entre ex in im pre re sobre sub tras ante dis mis un be".split()
)


def near_copies(a: str, b: str) -> bool:
    """Rhyme words too similar to count as two words (Angel: "no me gusta que rimen en palabras
    tan similares"): one ends the other (canta/encanta), a long shared start (cantaba/cantara),
    or both are -mente adverbs."""
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if len(short) > 2 and long_.endswith(short) and long_[: -len(short)] in _PREFIXES:
        return True  # the same word with a prefix (canta/encanta), not día/respondía
    if a.endswith("mente") and b.endswith("mente"):
        return True
    shared = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        shared += 1
    return shared >= 4 and shared >= min(len(a), len(b)) - 2


def rhyme(
    line: str, partner: str, phonology: PhonologyBackend, loose: bool = False
) -> Defect | None:
    if end_word(line) == end_word(partner):
        return Defect.RHYME  # the same word is not a rhyme
    if near_copies(end_word(line), end_word(partner)):
        return Defect.NEAR_COPY_RHYME
    a, b = phonology.rhyme_key(line), phonology.rhyme_key(partner)
    if a.consonant and a.consonant == b.consonant:
        return None
    if loose and a.assonant and a.assonant == b.assonant:
        return None
    return Defect.RHYME


_TACKED = re.compile(r",\s*[¡!¿]?\s*[A-Za-zÀ-ÿ'’]+\s*[.!?…]*\s*$")


def tacked_on(line: str) -> Defect | None:
    return Defect.TACKED if _TACKED.search(line) and len(words(line)) > 2 else None


def dangling(line: str, language: str) -> Defect | None:
    return Defect.DANGLING if end_word(line) in FUNCTION_END.get(language, frozenset()) else None


def repeated(line: str, others: tuple[str, ...]) -> Defect | None:
    return Defect.REPEATED if norm(line) in {norm(o) for o in others} else None


def opening_clash(line: str, others: tuple[str, ...], language: str) -> Defect | None:
    """Same two opening words as another line, or the same opening content word."""
    if opening(line) in {opening(o) for o in others}:
        return Defect.OPENING
    first = (words(line) or [""])[0]
    if not first or first in FUNCTION_END.get(language, frozenset()):
        return None
    return Defect.OPENING if any((words(o) or [""])[0] == first for o in others) else None


@lru_cache(maxsize=8)
def vocabulary(language: str) -> frozenset[str]:
    path = WORDLISTS / f"{language}.txt"
    if not path.exists():
        return frozenset()
    return frozenset(w.lower() for w in path.read_text(encoding="utf-8").split())


_ROMAN = re.compile(r"m*(c[md]|d?c{0,3})(x[cl]|l?x{0,3})(i[xv]|v?i{0,3})")


def unknown_words(line: str, language: str, allowed: frozenset[str]) -> list[str]:
    """Words in no frequency list (and Roman numerals, which the lists contain)."""
    vocab = vocabulary(language)
    if not vocab:
        return []
    out = []
    for w in words(line):
        w = w.strip("'’").removesuffix("'s").removesuffix("’s")
        if w and w not in allowed and (w not in vocab or (len(w) >= 3 and _ROMAN.fullmatch(w))):
            out.append(w)
    return out


STOPWORDS_TOP = 150  # the most frequent words of a language's list are its function words


@lru_cache(maxsize=8)
def stopwords(language: str) -> frozenset[str]:
    path = WORDLISTS / f"{language}.txt"
    if not path.exists():
        return FUNCTION_END.get(language, frozenset())
    top = path.read_text(encoding="utf-8").split()[:STOPWORDS_TOP]
    return frozenset(w.lower() for w in top) | FUNCTION_END.get(language, frozenset())


def content_words(line: str, language: str) -> list[str]:
    stop = stopwords(language)
    return [w for w in words(line) if len(w) >= 3 and w not in stop]


def repeated_words(
    line: str, earlier: tuple[str, ...], language: str, allowed: frozenset[str] = frozenset()
) -> list[str]:
    """Content words of ``line`` already used in ``earlier`` lines of the poem (or twice in it)."""
    seen = [w for e in earlier for w in content_words(e, language)]
    out, own = [], []
    for w in content_words(line, language):
        if w not in allowed and (w in seen or w in own):
            out.append(w)
        own.append(w)
    return out


def shape(line: str, max_words: int = 14) -> Defect | None:
    return Defect.SHAPE if not 3 <= len(words(line)) <= max_words else None


def check_line(
    line: str, ctx: LineContext, phonology: PhonologyBackend
) -> tuple[list[Defect], ScanResult]:
    """Every defect of ``line`` in ``ctx`` (empty list = it passes), with its scan."""
    defects: list[Defect] = []
    for d in (
        shape(line),
        repeated(line, ctx.others),
        opening_clash(line, ctx.others, ctx.language),
        dangling(line, ctx.language),
        tacked_on(line),
    ):
        if d:
            defects.append(d)
    if ctx.check_vocabulary and unknown_words(line, ctx.language, ctx.allowed_words):
        defects.append(Defect.UNKNOWN_WORD)
    if repeated_words(line, ctx.earlier, ctx.language, ctx.allowed_words):
        defects.append(Defect.REPEATED_WORD)
    if ctx.partner is not None:
        d = rhyme(line, ctx.partner, phonology, ctx.loose_rhyme)
        if d:
            defects.append(d)
    scan = phonology.scan_line(line)
    if ctx.target is not None and metre(scan, ctx.target, ctx.tolerance):
        defects.append(Defect.METRE)
    return defects, scan

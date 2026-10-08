"""Syllables of a line as the page shows them (docs/hack_apertus/PACKAGING_UX_PLAN.md, U4).

``syllable_view(line, language)`` splits each word into written syllables, marks the
stressed one, and marks where a word's last vowel merges with the next word's first
(Spanish *sinalefa*, Italian *sinalefe*). The page draws it as ``la·LU·na‿i·lu·MI·na`` so
a person sees what the counter counted without learning the terms first.

It is a display aid, not the metrical count: ``scan_line`` stays the authority. Spanish
uses ``silabeador`` (syllables and stress), Italian the vowel nuclei of
``poesia.phonology.italian``, English CMUdict stress with ``pyphen`` hyphenation where the
two agree on the number of syllables (otherwise the word is shown whole, with its stress),
German the nuclei and stress of ``poesia.phonology.german``, French a spelling split kept only
where it matches the French scanner's count for that word in that line.
"""

from __future__ import annotations

import re
from typing import Any

_PUNCT = ".,;:!?¡¿«»\"'()[]—–-…“”‘’"
_ES_VOWELS = set("aeiouáéíóúü")
_IT_ONSET_2 = {"ch", "gh", "gn", "gl", "sc", "qu"}


def _clean(word: str) -> str:
    return word.strip(_PUNCT)


def _syl(text: str, stressed: bool) -> dict[str, Any]:
    return {"t": text, "s": stressed}


# ── Spanish ──────────────────────────────────────────────────────────────


def _es_word(word: str) -> list[dict[str, Any]]:
    import silabeador  # type: ignore[import-untyped]

    clean = _clean(word)
    if not clean or not any(c.isalpha() for c in clean):
        return [_syl(word, False)]
    try:
        parts = silabeador.syllabify(clean)
        stress = silabeador.tonica(clean)
    except Exception:
        return [_syl(clean, False)]
    if not parts:
        return [_syl(clean, False)]
    idx = len(parts) + stress if stress < 0 else stress
    return [_syl(p, i == idx and len(parts) > 1) for i, p in enumerate(parts)]


def _es_merges(words: list[str]) -> list[bool]:
    """merge[i]: word i's last vowel joins word i+1's first (sinalefa)."""
    out = []
    for a, b in zip(words, words[1:], strict=False):
        a, b = _clean(a).lower(), _clean(b).lower()
        ends = bool(a) and a[-1] in _ES_VOWELS
        starts = bool(b) and (
            b[0] in _ES_VOWELS
            or b[0] == "y"
            and len(b) == 1
            or (b[0] == "h" and len(b) > 1 and b[1] in _ES_VOWELS)
        )
        out.append(ends and starts)
    return out


# ── Italian ──────────────────────────────────────────────────────────────


def _it_word(word: str) -> list[dict[str, Any]]:
    from poesia.phonology.italian import _nuclei, _stress_nucleus

    clean = _clean(word).replace("’", "'")
    letters = "".join(c for c in clean.lower() if c.isalpha())
    nuc = _nuclei(letters)
    if len(nuc) < 2:
        return [_syl(clean, False)]
    cuts = []
    for (_s1, e1, _v1), (s2, _e2, _v2) in zip(nuc, nuc[1:], strict=False):
        cluster = letters[e1:s2]
        if len(cluster) <= 1:
            cuts.append(e1)  # hiatus or a single consonant: it opens the next syllable
        elif cluster[0] == cluster[1]:
            cuts.append(e1 + 1)  # double consonant splits: ter-ra
        elif (
            cluster[0] == "s"
            or cluster[:2] in _IT_ONSET_2
            or (len(cluster) == 2 and cluster[1] in "lr")
        ):
            cuts.append(e1)  # s+C, digraphs and muta cum liquida stay together: pa-sta, pa-dre
        else:
            cuts.append(e1 + 1)  # otherwise split after the first: can-to, mon-tagna
    stressed = _stress_nucleus(letters, nuc)
    # Map cuts in `letters` back onto the written word (apostrophes and accents kept).
    pieces, pos, letter_i, start = [], 0, 0, 0
    bounds = set(cuts)
    for pos, ch in enumerate(clean):
        if ch.isalpha():
            if letter_i in bounds and pos > start:
                pieces.append(clean[start:pos])
                start = pos
            letter_i += 1
    pieces.append(clean[start:])
    return [_syl(p, i == stressed) for i, p in enumerate(pieces)]


def _it_merges(words: list[str]) -> list[bool]:
    from poesia.phonology.italian import VOWELS, _starts_vowel, _word

    out = []
    for a, b in zip(words, words[1:], strict=False):
        wa, wb = _word(a), _word(b)
        out.append(bool(wa) and wa[-1] in VOWELS and _starts_vowel(wb))
    return out


# ── German and French ────────────────────────────────────────────────────

_ONSET_2 = {
    "bl",
    "br",
    "cl",
    "cr",
    "dr",
    "fl",
    "fr",
    "gl",
    "gr",
    "pl",
    "pr",
    "tr",
    "vr",
    "ch",
    "ph",
    "th",
    "gn",
    "kl",
    "kr",
}


def _cuts(letters: str, spans: list[tuple[int, int]], onsets: set[str]) -> list[int]:
    """Syllable boundaries between vowel spans: one consonant opens the next syllable; of a
    cluster, an onset pair (pr, bl, ch) stays together, otherwise the last consonant moves."""
    cuts = []
    for (_s1, e1), (s2, _e2) in zip(spans, spans[1:], strict=False):
        cluster = letters[e1:s2]
        if len(cluster) <= 1:
            cuts.append(e1)
        elif cluster[-3:] in ("sch",) and len(cluster) > 3:
            cuts.append(s2 - 3)
        elif cluster[-2:] in onsets:
            cuts.append(s2 - 2)
        else:
            cuts.append(s2 - 1)
    return cuts


def _split_written(clean: str, cuts: list[int]) -> list[str]:
    """Cut positions counted in letters, applied to the written word (apostrophes kept)."""
    pieces, start, letter_i = [], 0, 0
    bounds = set(cuts)
    for pos, ch in enumerate(clean):
        if ch.isalpha():
            if letter_i in bounds and pos > start:
                pieces.append(clean[start:pos])
                start = pos
            letter_i += 1
    pieces.append(clean[start:])
    return pieces


def _de_word(word: str) -> list[dict[str, Any]]:
    from poesia.phonology.base import Stress
    from poesia.phonology.german import _rule_nuclei, _word_marks

    clean = _clean(word).replace("’", "'")
    letters = "".join(c for c in clean.lower() if c.isalpha())
    spans = _rule_nuclei(letters)
    marks = _word_marks(letters)
    if len(spans) < 2 or len(marks) != len(spans):
        return [_syl(clean, False)]
    pieces = _split_written(clean, _cuts(letters, spans, _ONSET_2 | {"ck", "ng"} - {"gn"}))
    return [_syl(p, len(pieces) > 1 and marks[i] is Stress.PRIMARY) for i, p in enumerate(pieces)]


_FR_VOWEL_RUN = re.compile(r"[aeiouyàâäéèêëîïôöùûüœæ]+")


def _fr_pieces(clean: str, count: int) -> list[str]:
    """Spelling split of one French word, kept only when it matches the scanner's count; a
    mute e the line does not count joins the syllable before it."""
    letters = "".join(c for c in clean.lower() if c.isalpha())
    masked = re.sub(r"(?<=[qg])u", "w", letters)
    spans = [(m.start(), m.end()) for m in _FR_VOWEL_RUN.finditer(masked)]
    pieces = _split_written(clean, _cuts(letters, spans, _ONSET_2)) if len(spans) > 1 else [clean]
    if len(pieces) == count + 1 and re.search(r"(e|es|ent)$", pieces[-1].lower()):
        pieces = pieces[:-2] + [pieces[-2] + pieces[-1]]
    return pieces if len(pieces) == count and count else [clean]


def _fr_stress(pieces: list[str]) -> int:
    """The last syllable, or the one before a counted mute e (SPEC·tre)."""
    if len(pieces) < 2:
        return -1
    last = pieces[-1].lower()
    return len(pieces) - 2 if re.fullmatch(r"[^aeiouy]*(e|es|ent)", last) else len(pieces) - 1


def _fr_words(words: list[str]) -> tuple[list[list[dict[str, Any]]], list[bool]]:
    """French syllables per word as counted in the line, and where a mute e is elided before
    the next word's vowel."""
    from poesia.phonology.french import _starts_vowel, _syllables, _word

    keys = [_word(w) for w in words]
    out, merges = [], []
    for i, word in enumerate(words):
        key = keys[i]
        if not key:  # punctuation on its own (« :) is shown as written
            out.append([_syl(word, False)])
            merges.append(False)
            continue
        nxt = next((k for k in keys[i + 1 :] if k), "")
        before_vowel = bool(nxt) and _starts_vowel(nxt)
        count, _stressed = _syllables(key, line_end=not nxt, before_vowel=before_vowel)
        pieces = _fr_pieces(_clean(word).replace("’", "'"), count)
        stress = _fr_stress(pieces)
        out.append([_syl(p, j == stress) for j, p in enumerate(pieces)])
        merges.append(before_vowel and bool(re.search(r"[^aeiouy]e$", key)))
    return out, merges[:-1] if merges else []


# ── English ──────────────────────────────────────────────────────────────


def _en_word(word: str) -> list[dict[str, Any]]:
    clean = _clean(word)
    letters = re.sub(r"[^A-Za-z']", "", clean)
    if not letters:
        return [_syl(clean or word, False)]
    try:
        import pronouncing  # type: ignore[import-untyped]

        phones = pronouncing.phones_for_word(letters.lower())
    except Exception:
        phones = []
    if not phones:
        return [_syl(clean, False)]
    stresses = pronouncing.stresses(phones[0])
    primary = stresses.find("1")
    if len(stresses) <= 1:
        return [_syl(clean, stresses == "1")]
    try:
        import pyphen  # type: ignore[import-untyped]

        parts = pyphen.Pyphen(lang="en_US").inserted(clean).split("-")
    except Exception:
        parts = [clean]
    if len(parts) != len(stresses):
        return [_syl(clean, True)]  # split unknown: show the word whole, stressed
    return [_syl(p, i == primary) for i, p in enumerate(parts)]


def syllable_view(line: str, language: str) -> list[dict[str, Any]]:
    """Words of ``line`` as ``{"syl": [{"t", "s"}...], "join": bool}``; join = merges with next."""
    words = [w for w in line.split() if w.strip()]
    if not words:
        return []
    if language == "es":
        sylls = [_es_word(w) for w in words]
        merges = _es_merges(words)
    elif language == "it":
        sylls = [_it_word(w) for w in words]
        merges = _it_merges(words)
    elif language == "en":
        sylls = [_en_word(w) for w in words]
        merges = [False] * (len(words) - 1)
    elif language == "de":
        sylls = [_de_word(w) for w in words]
        merges = [False] * (len(words) - 1)
    elif language == "fr":
        sylls, merges = _fr_words(words)
    else:
        return [{"syl": [_syl(w, False)], "join": False} for w in words]
    merges.append(False)
    return [{"syl": s, "join": j} for s, j in zip(sylls, merges, strict=True)]

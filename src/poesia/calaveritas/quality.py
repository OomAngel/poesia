"""Ranking of candidate lines by more than metre: sense, novelty, endings, clichés.

The review batch of 2026-10-09 (docs/research/research_notes/calaveritas_quality_audit_2026-10-09.md)
showed what a metre-only ranking produces: 96% of rhyme-closing Spanish lines ended on one of the six
most frequent words of their family, 37% of stanzas opened on a Death epithet, 7.7% of lines ended on
a word tacked on after a comma, and trait labels were pasted in verbatim. The checks here follow
PoesIA's line scorer (``evaluation/metrics.py``: novelty, end-word, cliché, theme) without its
embedding model, so they run inside the small container: theme is word overlap with the stanza's
scene, novelty is character-trigram overlap with earlier lines.
"""

from __future__ import annotations

import re
import threading
from collections import Counter
from typing import Any

from poesia.quality import gates
from poesia.quality.diversity import RecentEndings as _SharedRecent

CLICHES = {
    "es": (
        "llega la flaca",
        "llegó la flaca",
        "llega la catrina",
        "llegó la catrina",
        "la muerte llega",
        "llegó la muerte",
        "llega la muerte",
        "con su guadaña",
        "sin prisa",
        "en vano",
        "a su puerta",
        "a tu puerta",
        "toca la puerta",
        "tocó la puerta",
        "tocó a la puerta",
        "le llegó la hora",
        "su hora llegó",
        "llegó su hora",
        "no hay escape",
        "no hay escapatoria",
        "se lo llevó",
        "se la llevó",
    ),
    "en": (
        "death came knocking",
        "came knocking",
        "at the door",
        "at your door",
        "with her scythe",
        "your time has come",
        "time to go",
        "no escape",
        "came for",
    ),
}

_EPITHETS = r"(?:catrina|calaca|flaca|muerte|huesuda|huesudita|parca|pelona|calavera|dientona)"
DEATH_OPENING = {
    "es": re.compile(rf"^[¡¿\"«]*\s*(?:y |pero |mas |ya )?(?:la |el )?{_EPITHETS}\b", re.I),
    "en": re.compile(
        r"^[\"“]*\s*(?:and |but |now )?(?:la catrina|catrina|lady death|death|the reaper)\b", re.I
    ),
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zà-ÿ'’]+", text.lower())


def tacked_on(line: str) -> bool:
    """True for a line whose last word stands alone after a comma (shared gate)."""
    return gates.tacked_on(line) is not None


def death_opening(line: str, language: str) -> bool:
    return bool(DEATH_OPENING[language].search(line.strip()))


def cliches(line: str, language: str) -> int:
    low = " ".join(_words(line))
    return sum(1 for c in CLICHES[language] if c in low)


def _trigrams(text: str) -> set[str]:
    s = " ".join(_words(text))
    return {s[i : i + 3] for i in range(max(0, len(s) - 2))}


def similarity(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def _stems(text: str) -> set[str]:
    return {w[:5] for w in _words(text) if len(w) >= 4}


def copied(line: str, material: str) -> bool:
    """True if the line pastes three or more consecutive words of a trait or detail."""
    m = _words(material)
    low = " ".join(_words(line))
    return any(" ".join(m[i : i + 3]) in low for i in range(len(m) - 2))


class RecentEndings(_SharedRecent):
    """End words of recent lines across poems (shared ``poesia.quality.diversity``)."""

    def add(self, words: list[str]) -> None:  # type: ignore[override] - takes end words
        super().add(words)


RECENT = RecentEndings()


def score_line(
    line: str,
    language: str,
    *,
    syllables: int,
    target: int,
    end_word: str,
    common_ends: set[str],
    scene: str,
    material: str,
    prior: list[str],
    opening: bool,
    recent: Counter[str] | None = None,
) -> float:
    """Higher is better. ``opening``: the line opens a stanza after the first one."""
    score = -1.0 * abs(syllables - target)
    overlap = len(_stems(line) & _stems(scene + " " + material))
    score += min(overlap, 3) * 0.4
    score -= 1.0 * cliches(line, language)
    if end_word in common_ends:
        score -= 0.6
    if recent:
        score -= min(recent.get(end_word, 0), 6) * 0.25
    if prior:
        sim = max(similarity(line, p) for p in prior)
        if sim > 0.4:
            score -= 2.0 * (sim - 0.4) / 0.6 + 0.5
    if material and copied(line, material):
        score -= 0.8
    if opening and death_opening(line, language):
        score -= 1.5
    return score


# Step 3 of the 2026-11-06 plan (poesia-private research note calaveritas-live-sample, §9): faults
# both engines showed in blind round 6. None of these phrases occurs in the 2,192 broadside lines
# (transcriptions + local_octosyllabic); "¡qué X!" does (26 lines) and stays allowed.
FILLER = re.compile(
    r"\b(?:afán|fervor|sin cesar|sin fin|sin igual|sin parar|sin dudar|con primor|con esmero|"
    r"sin pudor)\b",
    re.I,
)
# The verse is written in Mexican Spanish, by rule (POETICS #6; Angel, 2026-11-07: "by rule in
# Mexican Spanish"). Words whose everyday Mexican form is another one, with that form; the repair is
# told the Mexican word. "mando" only as a noun (after an article), "yo mando" is Mexican too.
MEXICAN = {
    "móvil": "celular",
    "móviles": "celulares",
    "serial": "serie",
    "seriales": "series",
    "mando": "control",
    "verle": "verlo o verla",
    "vosotros": "ustedes",
    "ordenador": "computadora",
    "gafas": "lentes",
    "zumo": "jugo",
    "patata": "papa",
    "patatas": "papas",
    "nevera": "refrigerador",
    "melocotón": "durazno",
    "aparcar": "estacionar",
    "chaval": "chavo",
    "guay": "padre",
}
_NOT_MEXICAN = re.compile(
    r"\b(?:(?:el|su|un|del|al) (mando)|(" + "|".join(w for w in MEXICAN if w != "mando") + r"))\b",
    re.I,
)
# Prosaic or technical words (POETICS #5: "mencionar *derecho* lo hace menos lírico"), seen in the
# live sample of 2026-11-06 ("bytes", "datos", "aparato", "abono"); none occurs in the broadsides.
PROSAIC = re.compile(
    r"\b(?:bytes?|datos?|aparatos?|abono|jardinería|algoritmos?|software|dispositivos?|"
    r"archivos?|información|sistemas?|procesos?|gestión|análisis|función|eficiencia|"
    r"productividad|optimizar|estrategia|plataforma|usuarios?|contenido|digital|tecnología)\b",
    re.I,
)
_TITLED = re.compile(r"\b(?:don|doña)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)")
DEATH_WORD = re.compile(rf"\b(?:{_EPITHETS[3:-1]}|panteón|tumba|más allá|ultratumba)\b", re.I)


def filler(line: str) -> str | None:
    m = FILLER.search(line)
    return m.group(0) if m else None


def prosaic(line: str) -> str | None:
    m = PROSAIC.search(line)
    return m.group(0) if m else None


def not_mexican(line: str) -> tuple[str, str] | None:
    """(the word, its Mexican form) for the first word that Mexican Spanish says otherwise."""
    m = _NOT_MEXICAN.search(line)
    if not m:
        return None
    word = m.group(1) or m.group(2)
    return word, MEXICAN[word.lower()]


def invented_name(line: str, name: str) -> str | None:
    """A "don X" / "doña X" whose X is not in the requested name (e.g. "don Remigio" for "el
    alcalde")."""
    own = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]+", name)}
    for m in _TITLED.finditer(line):
        if m.group(1).lower() not in own:
            return m.group(0)
    return None


def names_person(lines: list[str], name: str, placeholder: str) -> bool:
    """The stanza names the person (any word of the name of 3+ letters other than an article)."""
    text = " ".join(lines).lower()
    keys = [
        w.lower()
        for w in re.findall(r"[A-Za-zÀ-ÿ]+", name)
        if len(w) > 2 and w.lower() not in {"los", "las", "del", "the"}
    ]
    return (
        not keys or placeholder.lower() in text or any(re.search(rf"\b{k}\b", text) for k in keys)
    )


def has_death(lines: list[str]) -> bool:
    return bool(DEATH_WORD.search(" ".join(lines)))


# Made-up words (Angel, 2026-11-08: "We need to catch them"): a word in neither the es_MX Hunspell
# dictionary (wordlists/hunspell, MPL 1.1) nor the 40,000-word list, e.g. "la Catrí" cut short to
# rhyme. Diminutives are looked up by their base word (Hunspell lacks most of them); a capitalised
# word inside the line is a name unless it is a cut-short genre word. Without spylls or the files
# the check is off (fails open).
_HUNSPELL_LOCK = threading.Lock()
_HUNSPELL: list = []
# Everyday Mexican words the es_MX dictionary lacks (checked 2026-11-08; the broadside lines it
# flagged include chamaca, tejocotes, petateó, tepetate).
EVERYDAY_MX = frozenset(
    """mija mijo mijita mijito chavo chava chavos chavas chamaca chamaco chamacas chamacos
    petate petatear petatearse petateó petatea petatean petatearon petateado petateada tejocote
    tejocotes tepetate cuatacho chambear chilango chilanga popote popotes padrísimo padrísima
    cuico cuicos carnala jefecita jefecito pachanga pachangas lambiscón metiche metiches
    argüendero argüendera argüende copal jacal ofertón deveras bonsáis""".split()
)
_DIMINUTIVE = re.compile(r"(?:c?it)(o|a)(s?)$")
_AUGMENTATIVE = ("ón", "ona", "ones", "onas", "ote", "ota", "otes", "otas", "tón", "tona", "tones")


def _hunspell() -> Any:
    with _HUNSPELL_LOCK:
        if not _HUNSPELL:
            try:
                from importlib.resources import files

                from spylls.hunspell import Dictionary

                base = files("poesia.wordlists") / "hunspell" / "es_MX"
                _HUNSPELL.append(Dictionary.from_files(str(base)))
            except (ImportError, OSError, ValueError):
                _HUNSPELL.append(None)
        return _HUNSPELL[0]


def _known(word: str, vocab: frozenset[str], dic: Any) -> bool:
    if len(word) == 1 or word in vocab or word in EVERYDAY_MX or dic.lookup(word):
        return True  # one letter: y, o, a, e, u and the old "á"
    bases = []
    m = _DIMINUTIVE.search(word)
    if m and len(word) > 5:  # lomitos -> lomos, cafecito -> cafe
        stem = word[: m.start()]
        bases += [stem + m.group(1) + m.group(2), stem + "e" + m.group(2), stem + m.group(2)]
    for suffix in _AUGMENTATIVE:  # bigotón -> bigote, panzón -> panza, lametón -> lame(r)
        if word.endswith(suffix) and len(word) > 5:
            stem = word[: -len(suffix)]
            bases += [stem + "e", stem + "o", stem + "a", stem, stem + "r"]
    return any(b in vocab or dic.lookup(b) for b in bases)


_DEATH_NAMES = frozenset({"catrina", "calaca", "huesuda", "pelona", "flaca", "parca", "calavera"})


def _bare(word: str) -> str:
    return word.translate(str.maketrans("áéíóúü", "aeiouu"))


def made_up(line: str, allowed: frozenset[str], genre: frozenset[str] = frozenset()) -> str | None:
    """The first word of ``line`` that does not exist in Spanish (None if all do)."""
    dic = _hunspell()
    if dic is None:
        return None
    vocab = gates.vocabulary("es")
    for i, m in enumerate(re.finditer(r"[A-Za-zÀ-ÿ]+", line)):
        raw = m.group(0)
        word = raw.lower()
        if word in allowed or _known(word, vocab, dic) or (raw[0].isupper() and dic.lookup(raw)):
            continue
        if i > 0 and raw[0].isupper():
            bare = _bare(word)
            cut = len(word) >= 3 and any(
                _bare(g).startswith(bare) and _bare(g) != bare for g in genre | _DEATH_NAMES
            )
            if not cut:
                continue  # a name
        return raw
    return None

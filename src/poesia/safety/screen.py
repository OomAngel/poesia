"""Phrase list + one model question; see ``poesia.safety`` for the policy."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Protocol

# Phrases, not single words: "morir", "death", "Tod" alone appear in grief and autumn
# poems and would flag the people the page is for. Matched on lowercased, accent-folded
# text, so "suicidio", "Suizid" and "suicide" all hit "suicid".
_PATTERNS: dict[str, list[str]] = {
    "en": [
        r"suicid",
        r"kill(ing)? myself",
        r"end (it all|my life|it now)",
        r"(don'?t|do not) want to (live|be alive|wake up|be here)",
        r"want(ed)? to die",
        r"better off without me",
        r"no (reason|point) (to|in) (live|living|go on|going on)",
        r"(hurt|harm|cut)(ting)? myself",
        r"self[- ]harm",
        r"(kill|hurt) (him|her|them)\b",
        r"can'?t go on( living)?",
    ],
    "es": [
        r"suicid",
        r"quitarme la vida",
        r"matarme",
        r"no quiero (vivir|seguir viviendo|despertar|estar aqui|seguir)",
        r"quiero morir",
        r"mejor sin mi\b",
        r"acabar con todo",
        r"(hacerme|me hago|me estoy haciendo) dano",
        r"(cortarme|lastimarme)",
        r"no tiene sentido (vivir|seguir)",
        r"(matarlo|matarla|matarlos|hacerle dano)",
        r"(ponerle|hacerle) fin a mi vida",
    ],
    "de": [
        r"suizid",
        r"selbstmord",
        r"mich umbringen",
        r"(mir|mich) das leben (zu )?nehmen",
        r"nicht mehr (leben|aufwachen|da sein)",
        r"sterben (will|mochte)",
        r"besser ohne mich",
        r"allem ein ende",
        r"mir (etwas|was) antun",
        r"mich (selbst )?(verletzen|ritzen)",
        r"(verletze|ritze) (ich )?mich",
        r"(ihn|sie) umbringen",
        r"(ihm|ihr) weh(zu)?tun",
    ],
    "fr": [
        r"suicid",
        r"me tuer",
        r"en finir",
        r"plus envie de vivre",
        r"ne plus me reveiller",
        r"veux mourir",
        r"mieux sans moi",
        r"me (faire|fais|suis fait) du mal",
        r"(lui|leur) faire du mal",
        r"me (couper|blesser)",
        r"(le|la|les) tuer",
    ],
    "it": [
        r"suicid",
        r"uccidermi",
        r"farla finita",
        r"non voglio piu (vivere|svegliarmi)",
        r"voglio morire",
        r"meglio senza di me",
        r"(farmi|mi faccio) del male",
        r"(fargli|farle) del male",
        r"tagliarmi",
        r"(ucciderlo|ucciderla|ucciderli)",
    ],
}
_COMPILED = {lang: [re.compile(p) for p in pats] for lang, pats in _PATTERNS.items()}

# Checked on the services' own sites, 2026-10-07 (www.143.ch, www.147.ch).
RESOURCES: list[dict[str, str]] = [
    {
        "number": "143",
        "name": "Die Dargebotene Hand / La Main Tendue",
        "note": "Always available, anonymous; chat and email on 143.ch. "
        "In English: 0800 143 000, 6–11 pm.",
        "url": "https://www.143.ch",
    },
    {
        "number": "147",
        "name": "Pro Juventute, for children and young people",
        "note": "Free and confidential, around the clock; WhatsApp and chat on 147.ch.",
        "url": "https://www.147.ch",
    },
    {
        "number": "144 / 112",
        "name": "Emergency",
        "note": "If someone is in immediate danger.",
        "url": "",
    },
]

CLASSIFY_PROMPT = (
    "You are a safety screen. Read the text between the markers. Answer with exactly one "
    "word, YES or NO: does the writer express a wish to die, intent or plans to harm "
    "themselves, or intent to harm another person? Sadness, grief, loneliness and poems "
    "about death or autumn are NO unless such intent is expressed.\n"
    "<<<\n{text}\n>>>\nAnswer (YES or NO):"
)


class _Generates(Protocol):
    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]: ...


@dataclass
class ScreenResult:
    """Outcome of screening one text."""

    flagged: bool
    matched: list[str] = field(default_factory=list)  # phrase patterns that hit
    model_says: bool | None = None  # None: no model asked, or no clear answer
    resources: list[dict[str, str]] = field(default_factory=list)


def _fold(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in norm if not unicodedata.combining(ch)).replace("’", "'")


def keyword_matches(text: str, languages: list[str] | None = None) -> list[str]:
    """Patterns that match, across the given languages (default: all five).

    All languages by default: people mix languages, and a German phrase in a Spanish poem
    still counts.
    """
    folded = _fold(text)
    hits = []
    for lang in languages or list(_COMPILED):
        hits += [f"{lang}:{rx.pattern}" for rx in _COMPILED[lang] if rx.search(folded)]
    return hits


def _ask_model(llm: _Generates, text: str) -> bool | None:
    try:
        out = llm.generate(CLASSIFY_PROMPT.format(text=text[:4000]), n=1, temperature=0.0)
    except Exception:  # screen must not fail closed on a model outage: keywords still ran
        return None
    answer = _fold(out[0] if out else "").strip().lstrip("*\"' ")
    if answer.startswith("yes") or answer.startswith("si"):
        return True
    if answer.startswith("no"):
        return False
    return None


def screen(text: str, llm: Any | None = None) -> ScreenResult:
    """Flag when any phrase matches or the model answers YES."""
    if not text.strip():
        return ScreenResult(flagged=False)
    matched = keyword_matches(text)
    model_says = _ask_model(llm, text) if llm is not None else None
    flagged = bool(matched) or model_says is True
    return ScreenResult(
        flagged=flagged,
        matched=matched,
        model_says=model_says,
        resources=RESOURCES if flagged else [],
    )

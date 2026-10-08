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
        # Passive wishes, burden, giving things away (added 2026-10-08, tuning set).
        r"(never|not) (to )?wake up( again)?",
        r"(stop|cease to) exist",
        r"(not|no longer) (be )?here anymore",
        r"(everything|it all) to (end|stop)",
        r"(i'?m|i am|feel like) (just )?a burden",
        r"won'?t be a (problem|burden)",
        r"giv(e|ing) (all )?my (things|stuff|belongings) away",
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
        # Passive wishes, burden, giving things away (added 2026-10-08, tuning set).
        r"no despertar",
        r"que todo (termine|acabe|se acabe)",
        r"dejar de existir",
        r"(soy|ser) una carga",
        r"no (volver a )?abrir los ojos",
        r"desaparecer para siempre",
        r"regalar (todas )?mis cosas",
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
        # Passive wishes, burden, giving things away (added 2026-10-08, tuning set).
        r"nie (wieder|mehr) aufwachen",
        r"nicht mehr existieren",
        r"(alles|es) (soll|moge|solle) (aufhoren|enden)",
        r"(eine|nur eine) last",
        r"meine sachen (weg|ver)schenken",
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
        # Passive wishes, burden, giving things away (added 2026-10-08, tuning set).
        r"ne plus (etre|exister)",
        r"que tout (s'arrete|se termine|finisse)",
        r"un fardeau",
        r"ne (plus|jamais) me reveiller",
        r"donne(r)? (toutes )?mes affaires",
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
        # Passive wishes, burden, giving things away (added 2026-10-08, tuning set).
        r"non (svegliarmi|risvegliarmi) piu",
        r"non esserci piu",
        r"smettere di (vivere|esistere)",
        r"(sono|essere) un peso",
        r"che tutto (finisca|termini)",
        r"regal(are|o) (tutte )?le mie cose",
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

# Checked on the services' own sites, 2026-10-07 (www.143.ch, www.143.ch/it, www.147.ch).
# The same facts in each page language (U9): a pause shown in Spanish must not switch to
# English. The services answer in the Swiss national languages; 143 also has an English line.
RESOURCES_BY_LANGUAGE: dict[str, list[dict[str, str]]] = {
    "en": [
        {
            "number": "143",
            "name": "Die Dargebotene Hand / La Main Tendue / Telefono Amico",
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
    ],
    "es": [
        {
            "number": "143",
            "name": "Die Dargebotene Hand / La Main Tendue / Telefono Amico",
            "note": "Siempre disponible y anónimo; chat y correo en 143.ch. "
            "En inglés: 0800 143 000, de 18 a 23 h.",
            "url": "https://www.143.ch",
        },
        {
            "number": "147",
            "name": "Pro Juventute, para niños, niñas y jóvenes",
            "note": "Gratuito y confidencial, a cualquier hora; WhatsApp y chat en 147.ch.",
            "url": "https://www.147.ch",
        },
        {
            "number": "144 / 112",
            "name": "Emergencias",
            "note": "Si alguien está en peligro inmediato.",
            "url": "",
        },
    ],
    "it": [
        {
            "number": "143",
            "name": "Telefono Amico (Die Dargebotene Hand / La Main Tendue)",
            "note": "Sempre disponibile e anonimo; chat ed e-mail su 143.ch. "
            "In inglese: 0800 143 000, dalle 18 alle 23.",
            "url": "https://www.143.ch/it",
        },
        {
            "number": "147",
            "name": "Pro Juventute, per bambini e giovani",
            "note": "Gratuito e confidenziale, 24 ore su 24; WhatsApp e chat su 147.ch.",
            "url": "https://www.147.ch/it/",
        },
        {
            "number": "144 / 112",
            "name": "Emergenza",
            "note": "Se qualcuno è in pericolo immediato.",
            "url": "",
        },
    ],
}
RESOURCES = RESOURCES_BY_LANGUAGE["en"]


def resources_for(language: str) -> list[dict[str, str]]:
    return RESOURCES_BY_LANGUAGE.get(language, RESOURCES)


# Widened 2026-10-08 after an independent 1,043-item set (data/safety/generated/) showed the
# first wording missed passive death wishes ("better not to wake up") and indirect signs
# (goodbyes, giving things away, feeling a burden): 28% recall. Tuned on that set; measured on
# a held-out set written before the change.
CLASSIFY_PROMPT = (
    "You are a safety screen for a poetry-writing app. Read the text between the markers. "
    "Answer YES if the writer, now or soon: wishes to die, not to wake up, to disappear or "
    "for everything to end; feels others would be better off without them; intends or plans "
    "to hurt themselves; shows warning signs of suicide such as saying goodbye, giving "
    "belongings away or feeling like a burden who will soon not be a problem; or intends to "
    "hurt another person. Answer NO for sadness, grief, loneliness, poems about death or "
    "autumn, distress that is clearly in the past, and joking idioms such as 'dying of "
    "laughter' or 'I could kill for a coffee'. Answer with exactly one word, YES or NO.\n"
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

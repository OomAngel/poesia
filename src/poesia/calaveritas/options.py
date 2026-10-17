"""What a visitor can ask for, and the rules that follow from it (docs/calaveritas/DECISIONS.md).

Recipients split into three risk groups (research report "PoesIA calaveritas site design"):
private people get "friend mode" (first name, chips, a short detail), public figures and the late
famous get satire of the public role or homage, pets and yourself are low risk. Under-18 visitors
get the Escolar tone only and no partner recipient.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Tone(StrEnum):
    CARINOSA = "carinosa"
    PICARA = "picara"
    POLITICA = "politica"
    ESCOLAR = "escolar"
    CLASICA = "clasica"


class Recipient(StrEnum):
    AMISTAD = "amistad"
    FAMILIA = "familia"
    PAREJA = "pareja"
    TRABAJO = "trabajo"
    PUBLICA = "publica"
    MASCOTA = "mascota"
    YO = "yo"
    FALLECIDA = "fallecida"


PRIVATE = {Recipient.AMISTAD, Recipient.FAMILIA, Recipient.PAREJA, Recipient.TRABAJO}
LANGUAGES = ("es", "en")
ADULT_AGE = 18
MAX_NAME = 40
MAX_DETAIL_PRIVATE = 80
MAX_DETAIL_OTHER = 200
STANZAS = (1, 2, 3, 4)

# Trait chips offered in friend mode (and to everyone); ids are stable, labels live in the page.
TRAITS: dict[str, dict[str, str]] = {
    "tarde": {"es": "siempre llega tarde", "en": "always late"},
    "cafe": {"es": "vive de café", "en": "runs on coffee"},
    "plantas": {"es": "colecciona plantas", "en": "collects plants"},
    "celular": {"es": "no suelta el celular", "en": "glued to the phone"},
    "chismes": {"es": "sabe todos los chismes", "en": "knows all the gossip"},
    "cocina": {"es": "cocina de maravilla", "en": "a great cook"},
    "futbol": {"es": "fanático del futbol", "en": "football fanatic"},
    "dormir": {"es": "duerme a todas horas", "en": "sleeps all the time"},
    "baile": {"es": "no para de bailar", "en": "never stops dancing"},
    "series": {"es": "ve series sin parar", "en": "binge-watches series"},
    "deporte": {"es": "vive en el gimnasio", "en": "lives at the gym"},
    "musica": {"es": "canta a todas horas", "en": "always singing"},
    "ahorro": {"es": "no gasta un peso", "en": "never spends a penny"},
    "compras": {"es": "compra de todo", "en": "buys everything"},
    "mascotas": {"es": "ama a sus mascotas", "en": "loves their pets"},
    "viajes": {"es": "siempre de viaje", "en": "always travelling"},
}
MAX_TRAITS = 4


@dataclass(frozen=True)
class Request:
    """A validated request (see safety.validate_request for the checks)."""

    language: str
    name: str
    recipient: Recipient
    tone: Tone
    stanzas: int
    traits: tuple[str, ...]
    detail: str
    birth_year: int

    @property
    def private(self) -> bool:
        return self.recipient in PRIVATE


def allowed_tones(age: int) -> tuple[Tone, ...]:
    return tuple(Tone) if age >= ADULT_AGE else (Tone.ESCOLAR,)


def allowed_recipients(age: int) -> tuple[Recipient, ...]:
    if age >= ADULT_AGE:
        return tuple(Recipient)
    return tuple(r for r in Recipient if r is not Recipient.PAREJA)


def max_detail(recipient: Recipient) -> int:
    return MAX_DETAIL_PRIVATE if recipient in PRIVATE else MAX_DETAIL_OTHER

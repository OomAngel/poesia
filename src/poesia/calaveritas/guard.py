"""Input validation and the content floor for calaveritas (docs/calaveritas/DECISIONS.md).

Topics are open; the floor applies to every tone and recipient: no threats, no personal data
(phone numbers, e-mail, street addresses, links), no sexual content, no hate speech. Private
recipients (friend mode) also exclude health, religion and sexuality details. The Escolar tone adds
a stricter list (swearing, alcohol and drugs, violence) checked on the input and on the poem.

Lists match on accent-folded, lower-cased text with simple leetspeak undone, against word
prefixes, so "pendejos" and "p3ndejo" both hit "pendej"; an entry ending in "$" matches the whole
word only ("arma$" must not block "Armando"). They are a floor, not a classifier: the
report button and the scoped auto-pause cover what slips through.
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata

from .options import (
    LANGUAGES,
    MAX_NAME,
    MAX_TRAITS,
    PRIVATE,
    STANZAS,
    TRAITS,
    Recipient,
    Request,
    Tone,
    allowed_recipients,
    allowed_tones,
    max_detail,
)

# --- word lists (prefixes, accent-folded) ------------------------------------------------------

HATE = (
    "maricon",
    "marica$",
    "maricas$",
    "joto$",
    "jotos$",
    "sudaca",
    "retrasad",
    "mongolic",
    "subnormal",
    "nigger",
    "nigga",
    "faggot",
    "fagot",
    "retard",
    "spic$",
    "spics$",
    "wetback",
    "beaner",
    "chink$",
    "kike",
    "tranny",
    "dyke",
)
SEXUAL = (
    "sexo",
    "sexual",
    "sexy",
    "coger",
    "cogid",
    "verga",
    "pito$",
    "chichi",
    "tetas",
    "nalga",
    "porno",
    "desnud",
    "orgasm",
    "violar",
    "violacion",
    "violad",
    "pedofil",
    "pederast",
    "follar",
    "masturb",
    "erotic",
    "sex$",
    "nude",
    "naked",
    "porn",
    "rape$",
    "raped$",
    "dick$",
    "pussy",
    "boob",
    "blowjob",
    "horny",
    "orgy",
    "orgia",
)
THREAT_PHRASES = (
    r"\bte voy a (matar|golpear|partir)",
    r"\b(lo|la|los|las) voy a (matar|golpear)",
    r"\bvamos a (matar|golpear)",
    r"\bkill (you|him|her|them)\b",
    r"\bshoot (you|him|her|them)\b",
    r"\bbomba\b",
    r"\bbomb\b",
)
SELF_HARM = ("suicid", "ahorcarse", "se ahorco", "kill himself", "kill herself", "kill yourself")
PRIVATE_SENSITIVE = (
    "cancer",
    "diabet",
    "enfermedad",
    "enfermo$",
    "enferma$",
    "depresi",
    "ansiedad",
    "sida$",
    "vih$",
    "discapacid",
    "embaraz",
    "aborto",
    "religi",
    "catolic",
    "cristian",
    "judio",
    "judia",
    "musulm",
    "evangel",
    "testigo de",
    "gay",
    "lesbian",
    "trans$",
    "transgener",
    "transexual",
    "bisexual",
    "homosexual",
    "disease",
    "illness",
    "sick$",
    "pregnan",
    "abortion",
    "catholic",
    "christian",
    "jewish",
    "muslim",
    "disabilit",
    "hiv$",
    "aids$",
)
ESCOLAR_EXTRA = (
    "pendej",
    "cabron",
    "chingad",
    "chingar",
    "chinga",
    "puta",
    "puto",
    "mierda",
    "culo",
    "joder",
    "carajo",
    "pinche",
    "mamon",
    "huevon",
    "estupid",
    "idiota",
    "imbecil",
    "borrach",
    "cerveza",
    "tequila",
    "mezcal",
    "alcohol",
    "droga",
    "mota",
    "marihuana",
    "cigarr",
    "fumar",
    "cruda$",
    "sangre",
    "degoll",
    "apunal",
    "asesin",
    "balazo",
    "disparo",
    "dispara$",
    "disparar",
    "dinamita",
    "cuchill",
    "ahorc",
    "matar$",
    "mato$",
    "a golpes",
    "pistola",
    "arma$",
    "armas$",
    "damn",
    "hell$",
    "shit",
    "fuck",
    "bitch",
    "bastard",
    "ass$",
    "drunk",
    "beer",
    "booze",
    "drug",
    "weed",
    "smok",
    "blood",
    "murder",
    "stab$",
    "stabbed",
    "shoot",
    "gun$",
    "guns$",
    "kill",
    "stupid",
    "idiot",
)
INJECTION = (
    "ignora las",
    "ignora tus",
    "ignora todo",
    "ignore the",
    "ignore all",
    "ignore previous",
    "instruccion",
    "instruction",
    "prompt",
    "system prompt",
    "olvida tus",
    "olvida las",
    "eres un modelo",
    "you are an ai",
    "jailbreak",
)

_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_URL = re.compile(r"(?:https?://|www\.|\b[\w-]+\.(?:com|mx|net|org|io|nl|es)\b)", re.I)
_ADDRESS = re.compile(
    r"\b(calle|avenida|av\.|colonia|col\.|c\.p\.|codigo postal|numero|num\.|street|st\.|avenue|"
    r"road|apt\.?|apartment|zip)\s*\S*\s*\d",
    re.I,
)
_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)


def fold(text: str, leet: bool = True) -> str:
    """Lower-case, strip accents, undo simple leetspeak (unless ``leet`` is False), collapse spaces."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    if leet:
        t = t.translate(_LEET)
    return re.sub(r"\s+", " ", t).strip()


def _hits(text: str, prefixes: tuple[str, ...]) -> list[str]:
    folded = fold(text)
    found = []
    for p in prefixes:
        if " " in p:
            if p in folded:
                found.append(p)
        elif p.endswith("$"):
            if re.search(rf"\b{re.escape(p[:-1])}\b", folded):
                found.append(p)
        elif re.search(rf"\b{re.escape(p)}", folded):
            found.append(p)
    return found


class Rejection(Exception):
    """A request or a generated stanza that the floor refuses; ``code`` keys MESSAGES."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def message(self, language: str) -> str:
        return MESSAGES.get(self.code, MESSAGES["invalid"])[0 if language == "es" else 1]


MESSAGES: dict[str, tuple[str, str]] = {
    "invalid": ("Revisa el formulario.", "Please check the form."),
    "name": (
        "Escribe un nombre de hasta 40 letras, sin números ni símbolos.",
        "Enter a name of up to 40 letters, without numbers or symbols.",
    ),
    "name_private": (
        "Para amistades, familia, pareja y trabajo usa solo el nombre de pila (una o dos palabras).",
        "For friends, family, partners and work, use the first name only (one or two words).",
    ),
    "age": ("Escribe tu año de nacimiento.", "Enter your year of birth."),
    "tone_age": (
        "Para menores de 18 años solo está el tono Escolar.",
        "Under 18, only the School tone is available.",
    ),
    "recipient_age": (
        "Esa opción no está disponible para menores de 18 años.",
        "That option is not available under 18.",
    ),
    "detail_long": ("El detalle es demasiado largo.", "The detail is too long."),
    "personal_data": (
        "No escribas teléfonos, correos, direcciones ni enlaces.",
        "Do not include phone numbers, e-mail, addresses or links.",
    ),
    "hate": (
        "Ese texto incluye palabras de odio. Las calaveritas se burlan sin humillar.",
        "That text includes hateful words. Calaveritas tease without humiliating.",
    ),
    "sexual": (
        "Aquí no se escribe contenido sexual sobre nadie.",
        "No sexual content about anyone is written here.",
    ),
    "threat": ("Aquí no se escriben amenazas.", "No threats are written here."),
    "self_harm": (
        "Ese tema no se trata aquí. Si lo estás pasando mal, busca a alguien de confianza o una línea "
        "de ayuda.",
        "That topic is not covered here. If you are going through a hard time, reach out to someone "
        "you trust or a helpline.",
    ),
    "private_sensitive": (
        "Para personas privadas no se escriben datos de salud, religión ni sexualidad.",
        "For private people, no health, religion or sexuality details are written.",
    ),
    "escolar": (
        "En el tono Escolar no van groserías, alcohol, drogas ni violencia.",
        "The School tone has no swearing, alcohol, drugs or violence.",
    ),
    "injection": (
        "Escribe solo rasgos de la persona, no instrucciones.",
        "Write only traits of the person, not instructions.",
    ),
}


def _check_floor(text: str, *, private: bool, escolar: bool, inputs: bool) -> None:
    if (
        _PHONE.search(text)
        or _EMAIL.search(text)
        or _URL.search(text)
        or _ADDRESS.search(fold(text, leet=False))
    ):
        raise Rejection("personal_data")
    if _hits(text, HATE):
        raise Rejection("hate")
    if _hits(text, SEXUAL):
        raise Rejection("sexual")
    if _hits(text, SELF_HARM):
        raise Rejection("self_harm")
    if inputs and any(re.search(p, fold(text)) for p in THREAT_PHRASES):
        raise Rejection("threat")
    if private and _hits(text, PRIVATE_SENSITIVE):
        raise Rejection("private_sensitive")
    if escolar and _hits(text, ESCOLAR_EXTRA):
        raise Rejection("escolar")


def _valid_name(name: str) -> bool:
    if not name or len(name) > MAX_NAME or not unicodedata.category(name[0]).startswith("L"):
        return False
    return all(unicodedata.category(c).startswith("L") or c in " .'’-" for c in name)


def _parse(raw: dict) -> tuple[str, str, Recipient, Tone, int, int]:
    language = raw.get("language") if raw.get("language") in LANGUAGES else "es"
    name = re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(raw.get("name", "")))).strip()
    try:
        return (
            language,
            name,
            Recipient(raw.get("recipient")),
            Tone(raw.get("tone")),
            int(raw.get("stanzas", 3)),
            int(raw.get("birth_year")),
        )
    except (ValueError, TypeError) as e:
        raise Rejection("invalid") from e


def _check_gates(name: str, recipient: Recipient, tone: Tone, stanzas: int, age: int) -> None:
    """Shape and age rules: stanza count, name, under-18 tone and recipient, friend-mode name."""
    if stanzas not in STANZAS:
        raise Rejection("invalid")
    if not _valid_name(name):
        raise Rejection("name")
    if recipient not in allowed_recipients(age):
        raise Rejection("recipient_age")
    if tone not in allowed_tones(age):
        raise Rejection("tone_age")
    if recipient in PRIVATE and (len(name.split()) > 2 or len(name) > 20):
        raise Rejection("name_private")


def _clean_detail(raw: dict, recipient: Recipient) -> tuple[tuple[str, ...], str]:
    traits = tuple(dict.fromkeys(t for t in raw.get("traits", []) or [] if t in TRAITS))
    detail = re.sub(r"\s+", " ", str(raw.get("detail", "") or "")).strip()
    if len(detail) > max_detail(recipient):
        raise Rejection("detail_long")
    return traits[:MAX_TRAITS], detail


def validate_request(raw: dict, today: _dt.date | None = None) -> Request:
    """Turn the posted form into a Request or raise Rejection(code)."""
    today = today or _dt.date.today()
    language, name, recipient, tone, stanzas, birth_year = _parse(raw)
    if not 1900 <= birth_year <= today.year:
        raise Rejection("age")
    _check_gates(name, recipient, tone, stanzas, today.year - birth_year)
    traits, detail = _clean_detail(raw, recipient)
    if any(_hits(x, INJECTION) or any(c in x for c in "<>{}[]`") for x in (name, detail)):
        raise Rejection("injection")
    # The name gets the floor only (no Escolar or private-topic lists: "Armando", "Gay Talese").
    _check_floor(name, private=False, escolar=False, inputs=True)
    _check_floor(detail, private=recipient in PRIVATE, escolar=tone is Tone.ESCOLAR, inputs=True)
    return Request(language, name, recipient, tone, stanzas, traits, detail, birth_year)


def check_output(lines: list[str], request: Request) -> str | None:
    """Return a rejection code if a generated stanza breaks the floor, else None."""
    text = "\n".join(lines)
    try:
        _check_floor(
            text, private=request.private, escolar=request.tone is Tone.ESCOLAR, inputs=False
        )
    except Rejection as r:
        return r.code
    return None

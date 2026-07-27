"""RhymeFetcher — retrieves rhyme-word candidates from local and online databases.

Sources, in priority order:
  1. `pronouncing` + CMUdict  — English only, offline, fast.
  2. Datamuse API `rel_rhy`   — English + some Spanish, online, free.
  3. Phonological suffix scan — Spanish fallback, offline, small built-in word list.

All network calls have a short timeout (3s) and fail silently.
"""

from __future__ import annotations

import json
import urllib.request

# Small Spanish frequency word list for offline suffix matching (~200 words).
_ES_COMMON_WORDS: list[str] = [
    # -ura
    "altura", "ternura", "dulzura", "escritura", "hermosura", "hechura",
    "locura", "figura", "fractura", "ruptura", "textura", "lectura",
    "apertura", "criatura", "oscura", "dura", "pura", "cura", "mesura",
    "postura", "pintura", "clausura", "natura", "censura", "rotura",
    # -ado / -ada
    "amado", "callado", "olvidado", "sagrado", "cansado", "pasado",
    "soñado", "guardado", "llamado", "marcado", "hallado", "enamorado",
    "morada", "mirada", "alborada", "madrugada", "jornada", "nevada",
    # -or
    "amor", "dolor", "calor", "temblor", "fervor", "clamor", "verdor",
    "fulgor", "esplendor", "resplandor", "interior", "exterior", "rumor",
    "labor", "valor", "ardor", "color", "terror", "error", "honor",
    # -ón / -ión
    "corazón", "canción", "ilusión", "visión", "pasión", "nación",
    "razón", "traición", "emoción", "tensión", "función", "lección",
    "acción", "creación", "misión", "atención", "decisión", "oración",
    # -al
    "eternal", "final", "vital", "mortal", "real", "ideal", "inmortal",
    "natural", "brutal", "total", "igual", "usual", "sutil", "leal",
    "canal", "rival", "coral", "oral", "penal", "plural", "causal",
    # -ento / -iento
    "tormento", "momento", "aliento", "viento", "lamento", "intento",
    "sustento", "fragmento", "fundamento", "pensamiento", "sentimiento",
    # -undo
    "fecundo", "profundo", "segundo", "mundo", "inmundo",
    # -ero / -era
    "sendero", "primero", "entero", "ligero", "compañero", "viajero",
    "primavera", "espera", "ribera", "manera", "quimera", "frontera",
    # -ido / -ida
    "latido", "gemido", "perdido", "querido", "partido", "ruido",
    "herida", "guarida", "despedida", "venida", "acogida", "medida",
    # -eza
    "belleza", "tristeza", "pureza", "nobleza", "sutileza", "firmeza",
    "naturaleza", "grandeza", "riqueza", "certeza", "proeza", "rareza",
    # -encia / -ancia
    "presencia", "ausencia", "vivencia", "experiencia", "paciencia",
    "distancia", "fragancia", "elegancia", "constancia", "importancia",
    # misc
    "tierra", "guerra", "sierra", "luna", "una", "laguna", "fortuna",
    "noche", "coche", "broche", "mar", "lugar", "hablar", "mirar",
    "volar", "soñar", "amar", "cantar", "llegar", "buscar", "callar",
]


def fetch_rhyme_words(
    word: str,
    language: str,
    max_results: int = 12,
    timeout: float = 3.0,
) -> list[str]:
    """Return up to `max_results` words that rhyme with `word`.

    Args:
        word: The anchor word (last word of the committed rhyme-group line).
        language: 'es', 'en', or 'nl'.
        max_results: Maximum candidates to return.
        timeout: Network timeout for Datamuse (seconds).

    Returns:
        List of rhyming words, deduplicated and excluding the anchor word.
        Empty list on any failure.
    """
    candidates: list[str] = []

    if language == "en":
        candidates = _fetch_pronouncing(word)
        if len(candidates) < 4:
            candidates += _fetch_datamuse(word, timeout=timeout)
    else:
        candidates = _fetch_datamuse(word, timeout=timeout)
        if len(candidates) < 4 and language == "es":
            candidates += _fetch_suffix_match_es(word)

    seen: set[str] = {word.lower()}
    unique: list[str] = []
    for w in candidates:
        w = w.strip().lower()
        if w and w not in seen:
            seen.add(w)
            unique.append(w)
        if len(unique) >= max_results:
            break

    return unique


def _fetch_pronouncing(word: str) -> list[str]:
    """English rhymes from CMUdict via the `pronouncing` library."""
    try:
        import pronouncing  # type: ignore[import-untyped]
        return pronouncing.rhymes(word.lower())
    except Exception:
        return []


def _fetch_datamuse(word: str, timeout: float = 3.0) -> list[str]:
    """Rhyming words from Datamuse `rel_rhy` endpoint."""
    try:
        url = f"https://api.datamuse.com/words?rel_rhy={word.lower()}&max=30"
        req = urllib.request.Request(url, headers={"User-Agent": "poesia/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [item["word"] for item in data if "word" in item]
    except Exception:
        return []


def _fetch_suffix_match_es(word: str) -> list[str]:
    """Spanish offline fallback: words sharing the stressed ending."""
    suffix = _spanish_rhyme_suffix(word)
    if not suffix or len(suffix) < 2:
        return []
    return [w for w in _ES_COMMON_WORDS if w != word and w.endswith(suffix)]


def _spanish_rhyme_suffix(word: str) -> str:
    """Extract consonant rhyme suffix (stressed vowel onward), normalised.

    Spanish stress rules (simplified):
    - If word has an explicit accent (á/é/í/ó/ú), that vowel is stressed.
    - Else if word ends in vowel, -n, or -s: penultimate vowel (paroxytone).
    - Else: last vowel (oxytone).
    """
    vowels = "aeiouáéíóú"
    vowel_map = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"}
    w = word.lower().rstrip(".,;:!?¿¡\"'")
    if not w:
        return ""
    positions = [i for i, c in enumerate(w) if c in vowels]
    if not positions:
        return ""

    # Explicit accent → use that position
    accented = [i for i, c in enumerate(w) if c in "áéíóú"]
    if accented:
        stressed = accented[0]
    elif len(positions) >= 2 and (w[-1] in "aeiouáéíóúns"):
        # Paroxytone: stress on penultimate vowel group
        stressed = positions[-2]
    else:
        # Oxytone: stress on last vowel
        stressed = positions[-1]

    suffix = w[stressed:]
    for acc, norm in vowel_map.items():
        suffix = suffix.replace(acc, norm)
    return suffix

"""Teaching voice for PoesIA.

The Teaching movement from `docs/POSITIONING.md`: when a line fails, say
*why* and *how to fix* in human language — not just "invalid". This module
turns the deterministic data in a ``ScanResult`` into a short lesson.

Pure functions over ScanResult — no I/O, no LLM, no network. It may import
rule helpers from the phonology backends, but never instantiates heavy
backends, so every function here is trivially testable offline.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from poesia.phonology.base import ScanResult, Stress
from poesia.phonology.spanish import VOWELS

__all__ = ["ScanLesson", "stress_marks", "sinalefa_pairs", "teach_scan", "format_scan"]


@dataclass
class ScanLesson:
    """A short, human *why + how to fix* lesson for one scanned line."""

    line: str
    metrical_syllable_count: int
    target_syllables: int | None = None
    stress: str = ""
    sinalefas: int = 0
    sinalefa_pairs: list[tuple[str, str]] = field(default_factory=list)
    final_word_note: str | None = None
    status: str = "ok"  # "ok" | "short" | "over"
    messages: list[str] = field(default_factory=list)

    @property
    def on_target(self) -> bool:
        """True when no target is given or the metrical count matches it."""
        return (
            self.target_syllables is None or self.metrical_syllable_count == self.target_syllables
        )


def stress_marks(pattern: Sequence[Stress]) -> str:
    """Render a stress pattern as readable marks (S = primary, s = secondary)."""
    marks = {Stress.PRIMARY: "S", Stress.SECONDARY: "s", Stress.UNSTRESSED: "u"}
    return " ".join(marks.get(s, "?") for s in pattern) or "—"


def _ends_with_vowel_sound(word: str) -> bool:
    """True if the word ends in a vowel sound (vowel, or vowel + n/s)."""
    return word[-1] in VOWELS or (len(word) >= 2 and word[-1] in "ns" and word[-2] in VOWELS)


def _starts_with_vowel_sound(word: str) -> bool:
    """True if the word starts with a vowel sound (vowel, h+vowel, or y)."""
    return (
        word[0] in VOWELS
        or (word[0] == "h" and len(word) > 1 and word[1] in VOWELS)
        or word[0] == "y"
    )


def sinalefa_pairs(line: str) -> list[tuple[str, str]]:
    """Return the adjacent word pairs joined by a sinalefa in a line.

    Mirrors the rule in ``poesia.phonology.spanish._count_sinalefas`` but keeps
    the word pairs themselves so the teaching voice can point at *which* vowels
    merged — the single most useful Spanish scansion lesson for a beginner.
    """
    words = [w for w in line.split() if w.strip()]
    pairs: list[tuple[str, str]] = []
    for i in range(len(words) - 1):
        w1 = words[i].lower().rstrip(".,;:!?\"'")
        w2 = words[i + 1].lower().lstrip(".,;:!?\"'¡¿")
        if not w1 or not w2:
            continue
        if _ends_with_vowel_sound(w1) and _starts_with_vowel_sound(w2):
            pairs.append((words[i].strip(".,;:!?\"'"), words[i + 1].strip(".,;:!?\"'¡¿")))
    return pairs


def _is_llana_end(word: str) -> bool:
    """True for a word ending in a vowel (or -n/-s after a vowel): no adjustment."""
    return word[-1] in "aeiou" or (len(word) >= 2 and word[-1] in "ns" and word[-2] in "aeiou")


def _explicit_accent_class(last: str) -> str | None:
    """Classify an explicit written accent: 'aguda', 'esdrújula', or None."""
    for i, char in enumerate(last):
        if char in "áéíóú":
            if not any(c in VOWELS for c in last[i + 1 :]):
                return "aguda"
            return "esdrujula"
    return None


def _spanish_final_word_note(line: str) -> str | None:
    """Describe how the final word's stress affects Spanish metrical counting."""
    words = [w for w in line.split() if w.strip()]
    if not words:
        return None
    last = words[-1].lower().rstrip(".,;:!?\"'")
    if not last:
        return None
    # Aguda (explicit accent on the final vowel cluster) → +1 syllable.
    accent = _explicit_accent_class(last)
    if accent == "aguda":
        return (
            f"Final word '{words[-1]}' is *aguda* (stress on the last "
            "syllable): Spanish verse adds 1 metrical syllable."
        )
    if accent == "esdrujula":
        return (
            f"Final word '{words[-1]}' is *esdrújula* (stress before the "
            "last syllable): Spanish verse subtracts 1 metrical syllable."
        )
    if _is_llana_end(last):
        return None  # Llana: no adjustment.
    return (
        f"Final word '{words[-1]}' ends in a consonant (not -n/-s): Spanish "
        "verse treats it as *aguda*, adding 1 metrical syllable."
    )


def _fix_tips(language: str, status: str) -> list[str]:
    """Craft-specific, actionable fix tips for a short/over line."""
    if language == "es":
        if status == "short":
            return [
                "To gain a syllable: use a longer word or synonym "
                "(e.g. 'luz' → 'claridad'), or *avoid* a sinalefa by breaking "
                "a vowel junction with a pause.",
            ]
        if status == "over":
            return [
                "To lose a syllable: let two adjacent vowels merge in a "
                "sinalefa (e.g. 'la aurora' → 3 syllables), or swap a longer "
                "word for a shorter one.",
            ]
    elif language == "it":
        if status == "short":
            return [
                "To gain a syllable: a longer word, or keep two vowels apart across words "
                "(dialefe), e.g. after a stressed final vowel ('è | amara').",
            ]
        if status == "over":
            return [
                "To lose a syllable: let a final and an initial vowel merge (sinalefe, "
                "'selvaggia e aspra'), elide ('lo amore' → \"l'amore\"), or truncate ('amore' → 'amor').",
            ]
    elif language == "de":
        if status == "short":
            return ["To gain a syllable: a longer word, or undo an elision ('hab'' → 'habe')."]
        if status == "over":
            return [
                "To lose a syllable: elide an unstressed e ('habe ich' → \"hab' ich\") or use a shorter word."
            ]
    elif language == "fr":
        if status == "short":
            return [
                "To gain a syllable: a longer word, or let a mute e count before a consonant "
                "('une ombre' → 'une rose')."
            ]
        if status == "over":
            return [
                "To lose a syllable: elide a mute e before a vowel ('une rose' → 'une âme') or use a shorter word."
            ]
    elif language == "en":
        if status == "short":
            return [
                "To gain a syllable: choose a longer word, or uncontract ('can't' → 'cannot').",
            ]
        if status == "over":
            return [
                "To lose a syllable: use a contraction or elision, or a shorter synonym.",
            ]
    return []


def _apply_target_check(
    lesson: ScanLesson, actual: int, target: int | None, form_label: str
) -> None:
    """Record the target comparison (exact/short/over) when a target is set."""
    if target is None:
        return
    if actual == target:
        lesson.messages.append(f"Exact match: {actual} syllables — that's the target{form_label}.")
    elif actual < target:
        lesson.status = "short"
        lesson.messages.append(
            f"Short by {target - actual}: this line has {actual} "
            f"syllables; the target{form_label} is {target}."
        )
    else:
        lesson.status = "over"
        lesson.messages.append(
            f"Over by {actual - target}: this line has {actual} "
            f"syllables; the target{form_label} is {target}."
        )


def _spanish_lesson(lesson: ScanLesson, line: str) -> None:
    """Add sinalefa + final-word stress notes for Spanish lines."""
    pairs = sinalefa_pairs(line)
    lesson.sinalefas = len(pairs)
    lesson.sinalefa_pairs = pairs
    if pairs:
        joined = ", ".join(f"'{a} {b}'" for a, b in pairs)
        lesson.messages.append(
            f"Sinalefa detected ({joined}): the two vowel sounds merge and "
            "count as a single metrical syllable."
        )
    note = _spanish_final_word_note(line)
    if note:
        lesson.final_word_note = note
        lesson.messages.append(note)


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many.format(n=n)


# The page speaks one language per session (docs/hack_apertus/PACKAGING_UX_PLAN.md, U1).
# English text stays inline below, as the CLI has always shown it; these are its es/it forms.
_UI: dict[str, dict[str, str]] = {
    "es": {
        "empty": "Verso vacío: escribe algo primero.",
        "exact": "Exacto: {a} sílabas, la medida del verso.",
        "short": "{missing}: este verso tiene {a}; la medida es {t}.",
        "over": "{extra}: este verso tiene {a}; la medida es {t}.",
        "sinalefa": "Sinalefa ({pairs}): las dos vocales se unen y cuentan como una sola sílaba.",
        "aguda": "La última palabra, '{w}', es aguda (acento en la última sílaba): el verso suma 1 sílaba.",
        "esdrujula": "La última palabra, '{w}', es esdrújula: el verso resta 1 sílaba.",
        "consonant": "La última palabra, '{w}', termina en consonante (no -n ni -s): cuenta como aguda y suma 1 sílaba.",
        "tip_short": "Para ganar una sílaba: una palabra más larga ('luz' → 'claridad'), o evita una sinalefa separando dos vocales.",
        "tip_over": "Para perder una sílaba: deja que dos vocales vecinas se unan en sinalefa ('la aurora' son 3 sílabas), o usa una palabra más corta.",
    },
    "it": {
        "empty": "Verso vuoto: scrivi qualcosa prima.",
        "exact": "Esatto: {a} sillabe, la misura del verso.",
        "short": "{missing}: questo verso ne ha {a}; la misura è {t}.",
        "over": "{extra}: questo verso ne ha {a}; la misura è {t}.",
        "tip_short": "Per guadagnare una sillaba: una parola più lunga, o tieni separate due vocali tra parole (dialefe), per esempio dopo una vocale finale accentata ('è | amara').",
        "tip_over": "Per perdere una sillaba: lascia che una vocale finale e una iniziale si fondano (sinalefe: 'selvaggia e aspra'), elidi ('lo amore' → \"l'amore\") o tronca ('amore' → 'amor').",
    },
    "de": {
        "empty": "Leerer Vers: schreib zuerst etwas.",
        "exact": "Genau: {a} Silben bis zur letzten Hebung, das Maß des Verses.",
        "short": "{missing}: dieser Vers hat {a} bis zur letzten Hebung; das Maß ist {t}.",
        "over": "{extra}: dieser Vers hat {a} bis zur letzten Hebung; das Maß ist {t}.",
        "tip_short": "Um eine Silbe zu gewinnen: ein längeres Wort, oder eine Auslassung rückgängig machen („hab'“ → „habe“).",
        "tip_over": "Um eine Silbe zu verlieren: ein unbetontes e auslassen („habe ich“ → „hab' ich“) oder ein kürzeres Wort wählen.",
    },
    "fr": {
        "empty": "Vers vide : écris d'abord quelque chose.",
        "exact": "Juste : {a} syllabes, la mesure du vers.",
        "short": "{missing} : ce vers en a {a} ; la mesure est de {t}.",
        "over": "{extra} : ce vers en a {a} ; la mesure est de {t}.",
        "tip_short": "Pour gagner une syllabe : un mot plus long, ou un e muet qui compte devant une consonne (« une ombre » → « une rose »).",
        "tip_over": "Pour perdre une syllabe : élide un e muet devant une voyelle (« une rose » → « une âme ») ou choisis un mot plus court.",
    },
}


def _ui_counts(ui: str, actual: int, target: int) -> dict[str, str]:
    d = abs(target - actual)
    if ui == "es":
        return {
            "missing": _plural(d, "Falta 1 sílaba", "Faltan {n} sílabas"),
            "extra": _plural(d, "Sobra 1 sílaba", "Sobran {n} sílabas"),
        }
    if ui == "de":
        return {
            "missing": _plural(d, "1 Silbe fehlt", "{n} Silben fehlen"),
            "extra": _plural(d, "1 Silbe zu viel", "{n} Silben zu viel"),
        }
    if ui == "fr":
        return {
            "missing": _plural(d, "Il manque 1 syllabe", "Il manque {n} syllabes"),
            "extra": _plural(d, "1 syllabe de trop", "{n} syllabes de trop"),
        }
    return {
        "missing": _plural(d, "Manca 1 sillaba", "Mancano {n} sillabe"),
        "extra": _plural(d, "C'è 1 sillaba di troppo", "Ci sono {n} sillabe di troppo"),
    }


def _localise(lesson: ScanLesson, ui: str, line: str) -> None:
    """Rewrite a lesson's messages in the page's language (es, it, de, fr); English is left as is."""
    table = _UI.get(ui)
    if table is None:
        return
    msgs: list[str] = []
    a, t = lesson.metrical_syllable_count, lesson.target_syllables
    if not line.strip():
        lesson.messages = [table["empty"]]
        return
    if t is not None:
        key = {"ok": "exact", "short": "short", "over": "over"}[lesson.status]
        msgs.append(table[key].format(a=a, t=t, **_ui_counts(ui, a, t)))
    if ui == "es" and lesson.sinalefa_pairs:
        pairs = ", ".join(f"'{x} {y}'" for x, y in lesson.sinalefa_pairs)
        msgs.append(table["sinalefa"].format(pairs=pairs))
    if ui == "es" and lesson.final_word_note:
        words = [w for w in line.split() if w.strip()]
        last = words[-1].lower().rstrip(".,;:!?\"'") if words else ""
        kind = _explicit_accent_class(last) or "consonant"
        msgs.append(
            table[
                "aguda" if kind == "aguda" else "esdrujula" if kind == "esdrujula" else "consonant"
            ].format(w=words[-1])
        )
    if lesson.status in ("short", "over"):
        msgs.append(table["tip_short" if lesson.status == "short" else "tip_over"])
    lesson.messages = msgs


def teach_scan(
    scan: ScanResult,
    target_syllables: int | None = None,
    *,
    language: str = "es",
    form_name: str | None = None,
    ui_language: str = "en",
) -> ScanLesson:
    """Build the teaching lesson for one scanned line.

    Args:
        scan: The deterministic scan result from a phonology backend.
        target_syllables: Optional metre target to teach against (e.g. 11 for
            a Spanish soneto, or the per-line haiku target).
        language: Language code ('es' or 'en') — selects which craft rules and
            fix tips are taught.
        form_name: Optional form name to name in the lesson (e.g. 'soneto').
        ui_language: Language of the messages: 'en' (the CLI's), or 'es'/'it' for the page.

    Returns:
        A ``ScanLesson`` with a human-readable list of why + how-to-fix
        messages. Pure and deterministic.
    """
    actual = scan.metrical_syllable_count
    lesson = ScanLesson(
        line=scan.line,
        metrical_syllable_count=actual,
        target_syllables=target_syllables,
        stress=stress_marks(scan.stress_pattern),
    )

    if not scan.line.strip():
        lesson.messages.append("Empty line — write something first.")
        _localise(lesson, ui_language, scan.line)
        return lesson

    form_label = f" of a {form_name}" if form_name else ""
    if target_syllables is not None:
        _apply_target_check(lesson, actual, target_syllables, form_label)

    if language == "es":
        _spanish_lesson(lesson, scan.line)

    if lesson.status != "ok":
        lesson.messages.extend(_fix_tips(language, lesson.status))
    _localise(lesson, ui_language, scan.line)
    return lesson


def format_scan(
    scan: ScanResult,
    target_syllables: int | None = None,
    *,
    language: str = "es",
    form_name: str | None = None,
) -> str:
    """Plain-text rendering of a scan lesson (testable, non-Rich)."""
    lesson = teach_scan(
        scan,
        target_syllables,
        language=language,
        form_name=form_name,
    )
    lines = [
        f"'{lesson.line}'",
        f"Metrical syllables: {lesson.metrical_syllable_count}"
        + (f"  (target: {target_syllables})" if target_syllables is not None else ""),
    ]
    if lesson.stress and lesson.stress != "—":
        lines.append(f"Stress: {lesson.stress}")
    if lesson.status != "ok" and not scan.is_valid:
        lines.append("Validity: line is invalid for its scan (see messages).")
    lines.extend(f"• {m}" for m in lesson.messages)
    return "\n".join(lines)

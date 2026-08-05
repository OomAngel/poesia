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
        ends_vowel = w1[-1] in VOWELS or (len(w1) >= 2 and w1[-1] in "ns" and w1[-2] in VOWELS)
        starts_vowel = (
            w2[0] in VOWELS or (w2[0] == "h" and len(w2) > 1 and w2[1] in VOWELS) or w2[0] == "y"
        )
        if ends_vowel and starts_vowel:
            pairs.append((words[i].strip(".,;:!?\"'"), words[i + 1].strip(".,;:!?\"'¡¿")))
    return pairs


def _spanish_final_word_note(line: str) -> str | None:
    """Describe how the final word's stress affects Spanish metrical counting."""
    words = [w for w in line.split() if w.strip()]
    if not words:
        return None
    last = words[-1].lower().rstrip(".,;:!?\"'")
    if not last:
        return None
    # Aguda (explicit accent on the final vowel cluster) → +1 syllable.
    for i, char in enumerate(last):
        if char in "áéíóú":
            remaining = last[i + 1 :]
            if not any(c in VOWELS for c in remaining):
                return (
                    f"Final word '{words[-1]}' is *aguda* (stress on the last "
                    "syllable): Spanish verse adds 1 metrical syllable."
                )
            return (
                f"Final word '{words[-1]}' is *esdrújula* (stress before the "
                "last syllable): Spanish verse subtracts 1 metrical syllable."
            )
    if last[-1] in "aeiou" or (len(last) >= 2 and last[-1] in "ns" and last[-2] in "aeiou"):
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


def teach_scan(
    scan: ScanResult,
    target_syllables: int | None = None,
    *,
    language: str = "es",
    form_name: str | None = None,
) -> ScanLesson:
    """Build the teaching lesson for one scanned line.

    Args:
        scan: The deterministic scan result from a phonology backend.
        target_syllables: Optional metre target to teach against (e.g. 11 for
            a Spanish soneto, or the per-line haiku target).
        language: Language code ('es' or 'en') — selects which craft rules and
            fix tips are taught.
        form_name: Optional form name to name in the lesson (e.g. 'soneto').

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
        return lesson

    form_label = f" of a {form_name}" if form_name else ""
    if target_syllables is not None:
        if actual == target_syllables:
            lesson.messages.append(
                f"Exact match: {actual} syllables — that's the target{form_label}."
            )
        elif actual < target_syllables:
            lesson.status = "short"
            lesson.messages.append(
                f"Short by {target_syllables - actual}: this line has {actual} "
                f"syllables; the target{form_label} is {target_syllables}."
            )
        else:
            lesson.status = "over"
            lesson.messages.append(
                f"Over by {actual - target_syllables}: this line has {actual} "
                f"syllables; the target{form_label} is {target_syllables}."
            )

    if language == "es":
        pairs = sinalefa_pairs(scan.line)
        lesson.sinalefas = len(pairs)
        lesson.sinalefa_pairs = pairs
        if pairs:
            joined = ", ".join(f"'{a} {b}'" for a, b in pairs)
            lesson.messages.append(
                f"Sinalefa detected ({joined}): the two vowel sounds merge and "
                "count as a single metrical syllable."
            )
        note = _spanish_final_word_note(scan.line)
        if note:
            lesson.final_word_note = note
            lesson.messages.append(note)

    if lesson.status != "ok":
        lesson.messages.extend(_fix_tips(language, lesson.status))
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

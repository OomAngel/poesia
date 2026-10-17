"""What to tell the model when a line fails a gate, per defect and language.

Lessons kept (PoesIA 2026-08 to 2026-10): name the rhyme to reach and offer words "pick one or
find your own", never force an exact end word (forcing bent the sense to the word; the share
of Calaveritas lines ending on a family's six commonest words fell from 89% to 40% once it
stopped); say how many syllables to add or remove, since models shorten far better than they
count; ask for the smallest change that keeps the meaning; never show raw rhyme keys.
"""

from __future__ import annotations

from poesia.quality.gates import Defect

_WHY: dict[str, dict[Defect, str]] = {
    "es": {
        Defect.METRE: "no tiene las sílabas que pide el verso",
        Defect.RHYME: "no rima con el verso que le toca",
        Defect.TACKED: "termina con una palabra suelta después de una coma",
        Defect.DANGLING: "termina en una palabra que no puede cerrar un verso",
        Defect.REPEATED: "repite otro verso",
        Defect.OPENING: "empieza igual que otro verso de la estrofa",
        Defect.UNKNOWN_WORD: "usa una palabra que no existe o no se entiende",
        Defect.SHAPE: "no es un verso completo",
        Defect.REPEATED_WORD: "repite una palabra que ya está en el poema",
        Defect.NEAR_COPY_RHYME: "rima con una palabra casi igual a la otra",
    },
    "en": {
        Defect.METRE: "does not have the syllables the line needs",
        Defect.RHYME: "does not rhyme with its partner line",
        Defect.TACKED: "ends on a single word tacked on after a comma",
        Defect.DANGLING: "ends on a word that cannot close a line",
        Defect.REPEATED: "repeats another line",
        Defect.OPENING: "opens like another line of the stanza",
        Defect.UNKNOWN_WORD: "uses a word that does not exist or makes no sense",
        Defect.SHAPE: "is not a complete line",
        Defect.REPEATED_WORD: "repeats a word already in the poem",
        Defect.NEAR_COPY_RHYME: "rhymes on a word that is almost the same as the other",
    },
}

_SMALLEST = {
    "es": "Corrígelo cambiando lo mínimo: conserva su sentido y sus imágenes, en español natural.",
    "en": "Fix it with the smallest change: keep its meaning and images, in natural English.",
}


def syllable_hint(language: str, count: int, target: int) -> str:
    d = count - target
    if language == "es":
        return f"tiene {count} sílabas y debe tener {target}: " + (
            f"quítale {d}" if d > 0 else f"añádele {-d}"
        )
    return f"has {count} syllables and needs {target}: " + (
        f"take away {d}" if d > 0 else f"add {-d}"
    )


def rhyme_hint(language: str, rhyme_with: str, bank: list[str]) -> str:
    words = ", ".join(bank)
    if language == "es":
        out = f"Debe rimar con «{rhyme_with}», sin repetir «{rhyme_with}»."
        if words:
            out += f" Palabras que riman, por si te sirven: {words}; o usa otra tuya que rime."
        return out
    out = f'It must rhyme with "{rhyme_with}", without using "{rhyme_with}" again.'
    if words:
        out += f" Rhyming words, if they help: {words}; or use your own."
    return out


def instruction(
    language: str,
    line: str,
    defects: list[Defect],
    *,
    count: int | None = None,
    target: int | None = None,
    rhyme_with: str | None = None,
    bank: list[str] | None = None,
) -> str:
    """One repair request for ``line`` naming every defect, in ``language`` (es or en)."""
    lang = language if language in _WHY else "en"
    reasons = []
    for d in defects:
        if d is Defect.METRE and count is not None and target is not None:
            reasons.append(syllable_hint(lang, count, target))
        else:
            reasons.append(_WHY[lang][d])
    head = (
        f"Este verso {'; '.join(reasons)}: «{line}»."
        if lang == "es"
        else f'This line {"; ".join(reasons)}: "{line}".'
    )
    out = head + " " + _SMALLEST[lang]
    if rhyme_with:
        out += " " + rhyme_hint(lang, rhyme_with, bank or [])
    return out

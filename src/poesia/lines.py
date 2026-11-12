"""One line of a poem in its place: scan, lesson, rhyme partner and syllable view.

Engine functions shared by the writing page (``poesia.webapp``), the training-data and
evaluation scripts, and the private quality work (moved out of ``webapp.py`` on 2026-11-12,
``docs/APP_PLAN_2026-11-12.md`` A2, so that engine code never imports the page).
``scan_line`` is the deterministic check of a line; the page shows its result as is.
"""

from __future__ import annotations

from typing import Any

FREE = "free"


def _phonology(language: str) -> Any:
    if language == "es":
        from poesia.phonology.spanish import SpanishPhonology

        return SpanishPhonology()
    if language == "en":
        from poesia.phonology.english import EnglishPhonology

        return EnglishPhonology()
    if language == "it":
        from poesia.phonology.italian import ItalianPhonology

        return ItalianPhonology()
    if language == "de":
        from poesia.phonology.german import GermanPhonology

        return GermanPhonology()
    if language == "fr":
        from poesia.phonology.french import FrenchPhonology

        return FrenchPhonology()
    raise ValueError(f"no phonology for language '{language}'")


def _form(language: str, name: str) -> Any:
    """The FormSpec, or None for free verse."""
    if name == FREE:
        return None
    from poesia.forms.definitions import get_form

    return get_form(name, language)


def _target(form: Any, index: int) -> int | None:
    if form is None:
        return None
    return (
        form.syllables_for_line(index) if index < form.total_lines or not form.total_lines else None
    )


def _letter(form: Any, index: int) -> str:
    if form is None:
        return ""
    scheme = form.rhyme_scheme.replace(" ", "")
    return scheme[index] if index < len(scheme) else ""


def _partner_index(form: Any, index: int) -> int | None:
    """First earlier line in the same rhyme group, or None (first of its group / unrhymed)."""
    if form is None:
        return None
    letter = _letter(form, index)
    if not letter.isalpha():
        return None
    scheme = form.rhyme_scheme.replace(" ", "")
    for j in range(index):
        if scheme[j] == letter:
            return j
    return None


# Function words per language, for spotting a line written in another language than the
# form's (U5). Shared words ("la", "in", "no", "con") count for each language they belong to.
_FUNCTION_WORDS = {
    "es": set(
        "el la los las que de y en con por para del una un como mi su sus sin se lo al más pero es no muy".split()
    ),
    "en": set(
        "the and of to in a is my with on for that it as his her your from by at not are was i you we".split()
    ),
    "it": set(
        "il lo la gli le che di e in con per del della una un come mio mia sua non si nel nella al ma è ed dei".split()
    ),
    "de": set(
        "der die das und ist nicht ich du er sie es wir ein eine mit von zu auf dem den des im mein dein sich auch wie".split()
    ),
    "fr": set(
        "le la les et est un une des du de que qui dans pour pas ne je tu il elle nous vous mon ma mes sur au aux".split()
    ),
}
_LANG_NAME = {
    "es": {"es": "español", "en": "inglés", "it": "italiano", "de": "alemán", "fr": "francés"},
    "en": {"es": "Spanish", "en": "English", "it": "Italian", "de": "German", "fr": "French"},
    "it": {"es": "spagnolo", "en": "inglese", "it": "italiano", "de": "tedesco", "fr": "francese"},
    "de": {
        "es": "Spanisch",
        "en": "Englisch",
        "it": "Italienisch",
        "de": "Deutsch",
        "fr": "Französisch",
    },
    "fr": {"es": "espagnol", "en": "anglais", "it": "italien", "de": "allemand", "fr": "français"},
}
_MISMATCH = {
    "es": "Este verso parece estar en {other}; esta forma cuenta las sílabas en {own}.",
    "en": "This line looks {other}; this form counts syllables in {own}.",
    "it": "Questo verso sembra in {other}; questa forma conta le sillabe in {own}.",
    "de": "Dieser Vers sieht nach {other} aus; diese Form zählt die Silben auf {own}.",
    "fr": "Ce vers semble être en {other} ; cette forme compte les syllabes en {own}.",
}


def guess_language(line: str) -> str | None:
    """The language the function words point to clearly, else None."""
    words = [w.strip(".,;:!?¡¿«»\"'()").lower() for w in line.replace("’", "'").split()]
    words = [w.split("'")[-1] if "'" in w else w for w in words]
    scores = {lang: sum(w in fw for w in words) for lang, fw in _FUNCTION_WORDS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (best, top), (_, second) = ranked[0], ranked[1]
    return best if top >= 2 and top - second >= 2 else None


def scan_line(
    line: str, language: str, form_name: str, index: int, lines: list[str]
) -> dict[str, Any]:
    """Deterministic check of one line in its place in the poem, with the lesson."""
    from poesia.teaching import teach_scan

    form = _form(language, form_name)
    phon = _phonology(language)
    target = _target(form, index)
    scan = phon.scan_line(line)
    lesson = teach_scan(
        scan, target, language=language, form_name=getattr(form, "name", None), ui_language=language
    )
    letter = _letter(form, index)
    partner = _partner_index(form, index)
    rhymes: bool | None = None
    partner_line = None
    key = phon.rhyme_key(line).consonant if line.strip() else ""
    if partner is not None and partner < len(lines) and lines[partner].strip():
        partner_line = lines[partner]
        rhymes = bool(key) and key == phon.rhyme_key(partner_line).consonant
    messages = list(lesson.messages)
    looks_like = guess_language(line)
    mismatch = looks_like is not None and looks_like != language
    if looks_like is not None and mismatch:
        names = _LANG_NAME[language]
        messages.insert(0, _MISMATCH[language].format(other=names[looks_like], own=names[language]))
    if rhymes is False and partner is not None:
        messages.append(
            {
                "en": f"Rhyme {letter}: this line should rhyme with line {partner + 1} "
                f"(“{partner_line}”). Change the last word.",
                "es": f"Rima {letter}: este verso debe rimar con el verso {partner + 1} "
                f"(«{partner_line}»). Cambia la última palabra.",
                "it": f"Rima {letter}: questo verso deve rimare con il verso {partner + 1} "
                f"(«{partner_line}»). Cambia l'ultima parola.",
                "de": f"Reim {letter}: Dieser Vers sollte sich auf Vers {partner + 1} reimen "
                f"(„{partner_line}“). Ändere das letzte Wort.",
                "fr": f"Rime {letter} : ce vers doit rimer avec le vers {partner + 1} "
                f"(« {partner_line} »). Change le dernier mot.",
            }[language]
        )
    return {
        "index": index,
        "syllables": scan.metrical_syllable_count,
        "target": target,
        "status": lesson.status,
        "stress": lesson.stress,
        "rhyme_letter": letter,
        "rhyme_key": key,
        "rhyme_partner": partner,
        "rhymes": rhymes,
        "messages": messages,
        "other_language": looks_like if mismatch else None,
        # A line in another language is shown in that language's syllables, as the hint says.
        "view": _view(line, looks_like if looks_like is not None and mismatch else language),
    }


def _view(line: str, language: str) -> list[dict[str, Any]]:
    """Syllables for display (poesia.scansion_view); never fails the scan."""
    try:
        from poesia.scansion_view import syllable_view

        return syllable_view(line, language)
    except Exception:
        return []

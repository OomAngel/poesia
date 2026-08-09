"""Tests for the teaching voice (poesia.teaching).

The teaching voice turns deterministic ScanResults into human *why + how to
fix* lessons — pure functions, so these tests never need phonology backends
installed.
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult, Stress
from poesia.teaching import (
    format_scan,
    sinalefa_pairs,
    stress_marks,
    teach_scan,
)


def _scan(
    line: str,
    count: int,
    *,
    valid: bool = True,
    pattern: tuple[Stress, ...] | None = None,
) -> ScanResult:
    return ScanResult(
        line=line,
        metrical_syllable_count=count,
        stress_pattern=pattern or (Stress.UNSTRESSED,) * count,
        is_valid=valid,
        violations=[],
        rhyme_key=RhymeKey(consonant="", assonant=""),
    )


# ── stress_marks ───────────────────────────────────────────────────────────


def test_stress_marks_render_primary_secondary_unstressed() -> None:
    pattern = (Stress.PRIMARY, Stress.UNSTRESSED, Stress.SECONDARY)
    assert stress_marks(pattern) == "S u s"


def test_stress_marks_empty_pattern() -> None:
    assert stress_marks(()) == "—"


# ── sinalefa_pairs ─────────────────────────────────────────────────────────


def test_sinalefa_pairs_detects_vowel_merger() -> None:
    pairs = sinalefa_pairs("la aurora es hermosa")
    # "la aurora" (a + a) and "aurora es" (a + e) both merge.
    assert ("la", "aurora") in pairs
    assert ("aurora", "es") in pairs


def test_sinalefa_pairs_handles_h_vowel() -> None:
    assert ("la", "hierba") in sinalefa_pairs("la hierba crece")


def test_sinalefa_pairs_empty_line() -> None:
    assert sinalefa_pairs("") == []


# ── teach_scan ─────────────────────────────────────────────────────────────


def test_teach_scan_exact_match() -> None:
    lesson = teach_scan(_scan("verso perfecto", 11), 11, language="es", form_name="soneto")
    assert lesson.on_target
    assert lesson.status == "ok"
    assert any("Exact match: 11 syllables" in m for m in lesson.messages)


def test_teach_scan_short_line_gives_delta_and_fix() -> None:
    lesson = teach_scan(_scan("verso corto", 8), 11, language="es", form_name="soneto")
    assert lesson.status == "short"
    assert lesson.target_syllables == 11
    assert any("Short by 3" in m for m in lesson.messages)
    assert any("To gain a syllable" in m for m in lesson.messages)


def test_teach_scan_over_line_gives_delta_and_fix() -> None:
    lesson = teach_scan(_scan("verso demasiado largo para la forma", 13), 11, language="es")
    assert lesson.status == "over"
    assert any("Over by 2" in m for m in lesson.messages)
    assert any("To lose a syllable" in m for m in lesson.messages)


def test_teach_scan_english_tips() -> None:
    lesson = teach_scan(
        _scan("line too long", 12), 10, language="en", form_name="sonnet_shakespearean"
    )
    assert lesson.status == "over"
    assert any("To lose a syllable" in m for m in lesson.messages)


def test_teach_scan_sinalefa_message() -> None:
    lesson = teach_scan(_scan("la aurora brilla", 6), None, language="es")
    assert lesson.sinalefas >= 1
    assert any("Sinalefa detected" in m for m in lesson.messages)


def test_teach_scan_empty_line() -> None:
    lesson = teach_scan(_scan("", 0), 11, language="es")
    assert any("Empty line" in m for m in lesson.messages)


def test_teach_scan_no_target_has_no_status() -> None:
    lesson = teach_scan(_scan("verso libre", 7), None, language="es")
    assert lesson.status == "ok"
    assert lesson.on_target


def test_teach_scan_aguda_final_word_note() -> None:
    lesson = teach_scan(_scan("viene la razón", 6), None, language="es")
    assert lesson.final_word_note is not None
    assert "aguda" in lesson.final_word_note


# ── format_scan ────────────────────────────────────────────────────────────


def test_format_scan_contains_key_lines() -> None:
    text = format_scan(_scan("la aurora brilla", 6), 7, language="es", form_name="haiku")
    assert "'la aurora brilla'" in text
    assert "Metrical syllables: 6" in text
    assert "target: 7" in text
    assert "Short by 1" in text


def test_format_scan_without_target_is_minimal() -> None:
    text = format_scan(_scan("verso suelto", 5), None, language="es")
    assert "Metrical syllables: 5" in text
    assert "target:" not in text

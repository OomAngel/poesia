"""Tests for scripts/generate_synthetic_repair_pairs.py's corruption logic."""

from __future__ import annotations

import json
import random

from poesia.phonology.spanish import SpanishPhonology
from scripts.generate_synthetic_repair_pairs import (
    _BOILERPLATE_RE,
    corrupt_rhyme,
    corrupt_syllables,
    extract_lines,
)


def test_corrupt_syllables_changes_the_count() -> None:
    phonology = SpanishPhonology()
    line = "en el jardín florece la rosa de primavera"
    target = phonology.scan_line(line).metrical_syllable_count

    result = corrupt_syllables(phonology, line, target, random.Random(0))

    assert result is not None
    corrupted_line, actual_syllables = result
    assert corrupted_line != line
    assert actual_syllables != target


def test_corrupt_rhyme_breaks_the_rhyme_and_keeps_original_word() -> None:
    phonology = SpanishPhonology()
    line = "bajo la luna brillante caminan las sombras"
    target_rhyme_key = phonology.rhyme_key(line).consonant

    result = corrupt_rhyme(phonology, line, target_rhyme_key, random.Random(0))

    assert result is not None
    corrupted_line, example_word = result
    assert example_word == "sombras"
    assert phonology.rhyme_key(corrupted_line).consonant != target_rhyme_key


def test_boilerplate_filter_catches_gutenberg_legal_text() -> None:
    contaminated = "You agree to indemnify and hold the Foundation harmless"
    assert _BOILERPLATE_RE.search(contaminated)


def test_boilerplate_filter_does_not_flag_ordinary_spanish_verse() -> None:
    clean = "bajo la luna brillante caminan las sombras"
    assert not _BOILERPLATE_RE.search(clean)


def test_extract_lines_skips_english_records(tmp_path) -> None:
    corpus_dir = tmp_path / "training_data_structured"
    corpus_dir.mkdir()
    (corpus_dir / "es_book.jsonl").write_text(
        json.dumps(
            {
                "completion": "bajo la luna brillante caminan las sombras",
                "language": "es",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (corpus_dir / "en_book.jsonl").write_text(
        json.dumps(
            {
                "completion": "success is counted sweetest by those who ne'er succeed",
                "language": "en",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    lines = extract_lines(str(corpus_dir / "*.jsonl"))

    assert lines == ["bajo la luna brillante caminan las sombras"]

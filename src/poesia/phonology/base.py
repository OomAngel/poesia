"""Shared data structures for the phonology layer.

Every language-specific scanner (spanish.py, english.py, multilingual.py)
returns these structures so the evaluation layer can stay language-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Stress(Enum):
    """Lexical/metrical stress marker for a single syllable."""

    UNSTRESSED = 0
    PRIMARY = 1
    SECONDARY = 2


@dataclass(frozen=True)
class Syllable:
    """A single syllable with its orthographic form and stress marking."""

    text: str
    stress: Stress = Stress.UNSTRESSED
    phonemes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RhymeKey:
    """Normalized rhyme signature for a line, used for rhyme-scheme detection.

    `consonant` captures full (consonant) rhyme; `assonant` captures vowel-only
    rhyme, which matters heavily in Spanish versification.
    """

    consonant: str
    assonant: str


@dataclass
class ScanResult:
    """Result of scanning a single line of verse.

    Attributes:
        line: the original input text.
        syllables: ordered syllable breakdown.
        metrical_syllable_count: count after applying language-specific rules
            (e.g. Spanish sinalefa, English elision) — NOT the same as naive
            orthographic syllable count.
        stress_pattern: tuple of Stress values in metrical position order.
        rhyme_key: RhymeKey for this line's ending, or None if undetermined.
        is_valid: whether the line satisfies the target form's constraints.
        violations: human-readable list of constraint violations, empty if valid.
    """

    line: str
    syllables: list[Syllable] = field(default_factory=list)
    metrical_syllable_count: int = 0
    stress_pattern: tuple[Stress, ...] = field(default_factory=tuple)
    rhyme_key: RhymeKey | None = None
    is_valid: bool = False
    violations: list[str] = field(default_factory=list)

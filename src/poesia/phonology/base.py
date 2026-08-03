"""Shared data structures for the phonology layer.

Every language-specific scanner (spanish.py, english.py, multilingual.py)
returns these structures so the evaluation layer can stay language-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class PhonologyBackend(Protocol):
    """Structural interface shared by all language phonology backends.

    Spanish, English and Dutch scanners each implement ``scan_line`` and
    ``rhyme_key`` behind their own lazy backend loading; consumers type against
    this Protocol so the evaluation layer stays language-agnostic.
    """

    def scan_line(self, line: str) -> ScanResult:
        """Scan one line, returning syllables, stress and validity."""
        ...

    def rhyme_key(self, line: str) -> RhymeKey:
        """Compute the rhyme key for a line (stressed tail phonemes)."""
        ...


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

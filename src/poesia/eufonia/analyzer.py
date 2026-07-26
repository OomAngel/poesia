"""Sound/euphony analysis over a scanned poem.

Consumes `poesia.phonology` ScanResult objects (never re-derives phonemes
itself) and reports on:
    - rhyme scheme detection across a stanza (from RhymeKey sequences)
    - assonance/consonance density within and across lines
    - cacophony flags: awkward consonant clusters, excessive sibilance, etc.

Phase 0 status: data structures + interface only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from poesia.phonology.base import ScanResult


@dataclass
class EuphonyReport:
    """Result of a euphony analysis pass over one or more scanned lines."""

    rhyme_scheme: str = ""  # e.g. "ABAB" once detected
    assonance_score: float = 0.0  # 0-1, higher = more internal vowel echo
    consonance_score: float = 0.0  # 0-1, higher = more internal consonant echo
    cacophony_flags: list[str] = field(default_factory=list)


class EuphonyAnalyzer:
    """Analyzes sound quality across a poem's scanned lines."""

    def analyze(self, scans: list[ScanResult]) -> EuphonyReport:
        """Produce a EuphonyReport for a sequence of already-scanned lines."""
        raise NotImplementedError(
            "EuphonyAnalyzer.analyze pending rhyme-scheme detection (Phase 1)."
        )

    def detect_rhyme_scheme(self, scans: list[ScanResult]) -> str:
        """Infer a letter-notation rhyme scheme (e.g. 'ABAB') from RhymeKeys."""
        raise NotImplementedError("Rhyme scheme detection pending Phase 1.")

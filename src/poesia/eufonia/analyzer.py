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
        if not scans:
            return EuphonyReport()

        rhyme_scheme = self.detect_rhyme_scheme(scans)
        assonance = self._calculate_assonance(scans)
        consonance = self._calculate_consonance(scans)
        flags = self._detect_cacophony(scans)

        return EuphonyReport(
            rhyme_scheme=rhyme_scheme,
            assonance_score=assonance,
            consonance_score=consonance,
            cacophony_flags=flags,
        )

    def detect_rhyme_scheme(self, scans: list[ScanResult]) -> str:
        """Infer a letter-notation rhyme scheme (e.g. 'ABAB') from RhymeKeys."""
        if not scans:
            return ""

        assigned_letters: list[str] = []
        key_to_letter: dict[tuple[str, str], str] = {}
        next_letter_idx = 0

        for scan in scans:
            if not scan.rhyme_key:
                assigned_letters.append("X")
                continue

            rkey = (scan.rhyme_key.consonant.lower(), scan.rhyme_key.assonant.lower())

            # Check for existing match (consonant or assonant match)
            matched_letter = None
            for (existing_c, existing_a), letter in key_to_letter.items():
                if (rkey[0] and rkey[0] == existing_c) or (rkey[1] and rkey[1] == existing_a):
                    matched_letter = letter
                    break

            if matched_letter:
                assigned_letters.append(matched_letter)
            else:
                letter = chr(ord("A") + next_letter_idx)
                next_letter_idx += 1
                key_to_letter[rkey] = letter
                assigned_letters.append(letter)

        return "".join(assigned_letters)

    def _calculate_assonance(self, scans: list[ScanResult]) -> float:
        """Calculate vowel repetition density (0.0 to 1.0)."""
        vowels = "aeiouyáéíóú"
        vowel_counts: dict[str, int] = {}
        total_vowels = 0

        for scan in scans:
            text = scan.line.lower()
            for char in text:
                if char in vowels:
                    vowel_counts[char] = vowel_counts.get(char, 0) + 1
                    total_vowels += 1

        if total_vowels < 2:
            return 0.0

        # Measure concentration of dominant vowels
        max_vowel_count = max(vowel_counts.values()) if vowel_counts else 0
        return min(1.0, round(max_vowel_count / total_vowels, 3))

    def _calculate_consonance(self, scans: list[ScanResult]) -> float:
        """Calculate consonant repetition density (0.0 to 1.0)."""
        vowels = "aeiouyáéíóú \t\n\r.,!?;:-'\""
        consonant_counts: dict[str, int] = {}
        total_consonants = 0

        for scan in scans:
            text = scan.line.lower()
            for char in text:
                if char.isalpha() and char not in vowels:
                    consonant_counts[char] = consonant_counts.get(char, 0) + 1
                    total_consonants += 1

        if total_consonants < 2:
            return 0.0

        max_consonant_count = max(consonant_counts.values()) if consonant_counts else 0
        return min(1.0, round(max_consonant_count / total_consonants, 3))

    def _detect_cacophony(self, scans: list[ScanResult]) -> list[str]:
        """Detect harsh phonetic patterns such as excessive sibilance."""
        flags: list[str] = []

        for i, scan in enumerate(scans, 1):
            text = scan.line.lower()
            # Excessive sibilance check ('s' / 'z')
            sibilants = sum(1 for c in text if c in "sz")
            if len(text) > 0 and (sibilants / len(text)) > 0.25:
                flags.append(f"Line {i}: Excessive sibilance detected ('s'/'z' frequency > 25%)")

        return flags

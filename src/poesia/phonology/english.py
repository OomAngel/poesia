"""English phonology / scansion backend.

Wraps `pronouncing` (CMUdict-backed) for rhyme lookup, phoneme sequences and
lexical stress, and `prosodic` for full metrical parsing (feet, stress
sequences, alternative scansions). `phonemizer` (eSpeak NG backend) is the
fallback for out-of-vocabulary words not present in CMUdict.

Phase 0 status: interface + stub implementation.
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult, Stress


class EnglishPhonology:
    """Scans and validates English verse lines.

    Backends (lazily imported):
        - pronouncing (+ cmudict): rhyme lookup, phoneme sequences, stress
        - prosodic: full metrical parsing (feet, alternative scansions)
        - phonemizer: OOV word fallback via eSpeak NG
    """

    def __init__(self) -> None:
        self._pronouncing = None  # lazy-loaded

    def _ensure_pronouncing(self):
        if self._pronouncing is None:
            try:
                import pronouncing  # type: ignore[import-untyped]
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise RuntimeError(
                    "pronouncing is not installed. Run: pip install -e '.[english]'"
                ) from exc
            self._pronouncing = pronouncing
        return self._pronouncing

    def stresses_for_word(self, word: str) -> str | None:
        """Return the CMUdict stress digit string for a word, e.g. '1' or '0102'."""
        pronouncing = self._ensure_pronouncing()
        phones = pronouncing.phones_for_word(word.lower())
        if not phones:
            return None
        return pronouncing.stresses(phones[0])

    def rhymes_for_word(self, word: str) -> list[str]:
        """Return CMUdict rhyme candidates for a word."""
        pronouncing = self._ensure_pronouncing()
        return pronouncing.rhymes(word.lower())

    def scan_line(self, line: str) -> ScanResult:
        """Scan a single line of English verse.

        Phase 0: word-level stress lookup only, no full metrical foot
        parsing. Foot-level analysis is deferred to `prosodic` integration.
        """
        words = [w.strip(".,;:!?\"'()") for w in line.split()]
        stress_pattern: list[Stress] = []
        for word in words:
            digits = self.stresses_for_word(word)
            if digits is None:
                continue
            for digit in digits:
                stress_pattern.append(
                    Stress.PRIMARY
                    if digit == "1"
                    else Stress.SECONDARY
                    if digit == "2"
                    else Stress.UNSTRESSED
                )
        return ScanResult(
            line=line,
            metrical_syllable_count=len(stress_pattern),
            stress_pattern=tuple(stress_pattern),
            is_valid=len(stress_pattern) > 0,
        )

    def rhyme_key(self, line: str) -> RhymeKey:
        """Extract a rhyme signature from the final word of a line."""
        words = [w.strip(".,;:!?\"'()") for w in line.split()]
        if not words:
            raise ValueError("Cannot extract rhyme key from an empty line.")
        last_word = words[-1]
        pronouncing = self._ensure_pronouncing()
        phones = pronouncing.phones_for_word(last_word.lower())
        if not phones:
            raise ValueError(f"No pronunciation found for '{last_word}'.")
        rhyme_part = pronouncing.rhyming_part(phones[0])
        return RhymeKey(consonant=rhyme_part, assonant=rhyme_part)

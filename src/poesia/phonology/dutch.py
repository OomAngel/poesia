"""Dutch phonology / scansion backend.

Uses pyphen (hyphenation-based syllabification) for Dutch verse.
Stress detection is basic (final syllable of content words tends to be stressed
in Dutch, with exceptions for prefixes and suffixes).

For full IPA transcription, espeak-ng system binary would be needed.
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult, Stress


class DutchPhonology:
    """Scans and validates Dutch verse lines.

    Backends (lazily imported):
        - pyphen: hyphenation-based syllabification (primary)
        - phonemizer: IPA transcription (requires espeak-ng binary)
    """

    def __init__(self) -> None:
        self._pyphen = None  # lazy-loaded

    def _ensure_pyphen(self):
        if self._pyphen is None:
            try:
                import pyphen  # type: ignore[import-untyped]

                self._pyphen = pyphen.Pyphen(lang="nl_NL")
            except ImportError:
                self._pyphen = False
        return self._pyphen if self._pyphen else None

    def scan_line(self, line: str) -> ScanResult:
        """Scan a single line of Dutch verse.

        Returns a ScanResult with syllable count and basic stress pattern.
        Dutch stress is complex; this provides a simplified heuristic.
        """
        pyphen = self._ensure_pyphen()
        if not pyphen:
            raise RuntimeError("No Dutch phonology backend installed. Run: pip install pyphen")

        words = line.split()
        total_syllables = 0
        stress_pattern = []

        for word in words:
            clean_word = "".join(c for c in word if c.isalpha())
            if clean_word:
                # Get hyphenation points
                hyphenated = pyphen.inserted(clean_word.lower())
                syllables = hyphenated.split("-") if hyphenated else [clean_word]
                num_syllables = len(syllables)
                total_syllables += num_syllables

                # Dutch stress heuristic:
                # - Monosyllables: stressed
                # - Bisyllables: usually first syllable stressed
                # - Longer words: usually penultimate, but many exceptions
                if num_syllables == 1:
                    stress_pattern.append(Stress.PRIMARY)
                elif num_syllables == 2:
                    stress_pattern.extend([Stress.PRIMARY, Stress.UNSTRESSED])
                else:
                    # Penultimate stress as default
                    for i in range(num_syllables):
                        if i == num_syllables - 2:
                            stress_pattern.append(Stress.PRIMARY)
                        else:
                            stress_pattern.append(Stress.UNSTRESSED)

        return ScanResult(
            line=line,
            metrical_syllable_count=total_syllables,
            stress_pattern=tuple(stress_pattern),
            is_valid=total_syllables > 0,
        )

    def rhyme_key(self, line: str) -> RhymeKey:
        """Extract consonant + assonant rhyme signature from a line's ending."""
        import re

        clean = re.sub(r"[^\w\s]", "", line.strip().lower())
        if not clean:
            return RhymeKey(consonant="", assonant="")

        words = clean.split()
        last_word = words[-1] if words else ""

        # Dutch vowels (including digraphs simplified)
        vowels = "aeiouàèéëïöü"
        vowel_indices = [i for i, char in enumerate(last_word) if char in vowels]

        if not vowel_indices:
            return RhymeKey(consonant=last_word, assonant="")

        # Use last stressed vowel (simplified: last vowel for now)
        stress_idx = vowel_indices[-1]
        if len(vowel_indices) >= 2:
            # Penultimate vowel more likely stressed in Dutch
            stress_idx = vowel_indices[-2]

        consonant_rhyme = last_word[stress_idx:]
        assonant_rhyme = "".join([c for c in consonant_rhyme if c in vowels])

        return RhymeKey(consonant=consonant_rhyme, assonant=assonant_rhyme)

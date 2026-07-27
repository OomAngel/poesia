"""Spanish phonology / scansion backend.

Wraps (or will wrap) `rantanplan` for metric scansion + stanza classification
and `silabeador` for lower-level syllabification and stress detection, with
`fonemas` available for phonological transcription when orthography alone is
insufficient (e.g. rhyme validation under historical or dialectal spelling).

Phase 0 status: interface + stub implementation. Real backend wiring happens
once the `spanish` extra (`pip install -e ".[spanish]"`) is installed and
exercised against real verse in tests/test_phonology_spanish.py.
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult


class SpanishPhonology:
    """Scans and validates Spanish verse lines.

    Backends (lazily imported so the base package has no hard dependency):
        - rantanplan: metric syllable count, stress pattern, stanza detection
        - silabeador: syllabification + prosodic stress, lower-level fallback
        - fonemas: phonological transcription for rhyme validation
    """

    def __init__(self) -> None:
        self._rantanplan = None  # lazy-loaded
        self._silabeador = None  # lazy-loaded

    def _ensure_rantanplan(self):
        if self._rantanplan is None:
            try:
                import rantanplan  # type: ignore[import-untyped]
                self._rantanplan = rantanplan
            except ImportError:
                self._rantanplan = False  # Mark as unavailable
        return self._rantanplan if self._rantanplan else None

    def _ensure_silabeador(self):
        if self._silabeador is None:
            try:
                import silabeador  # type: ignore[import-untyped]
                self._silabeador = silabeador
            except ImportError:
                self._silabeador = False
        return self._silabeador if self._silabeador else None

    def scan_line(self, line: str) -> ScanResult:
        """Scan a single line of Spanish verse.

        Returns a ScanResult with metrical syllable count, stress pattern and
        rhyme key. Uses rantanplan if available, falls back to silabeador for
        basic syllable counting.
        """
        # Try rantanplan first (full metrical analysis)
        rantanplan = self._ensure_rantanplan()
        if rantanplan:
            analysis = rantanplan.get_scansion(line)
            return ScanResult(
                line=line,
                metrical_syllable_count=analysis.get("num_syllables", 0),
                is_valid=analysis.get("num_syllables", 0) > 0,
            )

        # Fall back to silabeador (basic syllable counting)
        silabeador = self._ensure_silabeador()
        if silabeador:
            words = line.split()
            total_syllables = 0
            for word in words:
                # Clean punctuation
                clean_word = "".join(c for c in word if c.isalpha())
                if clean_word:
                    syllables = silabeador.syllabify(clean_word)
                    total_syllables += len(syllables)
            return ScanResult(
                line=line,
                metrical_syllable_count=total_syllables,
                is_valid=total_syllables > 0,
            )

        # No backend available
        raise RuntimeError(
            "No Spanish phonology backend installed. Run: pip install silabeador"
        )

    def rhyme_key(self, line: str) -> RhymeKey:
        """Extract consonant + assonant rhyme signature from a line's ending."""
        import re

        clean = re.sub(r"[^\w\s]", "", line.strip().lower())
        if not clean:
            return RhymeKey(consonant="", assonant="")

        words = clean.split()
        last_word = words[-1] if words else ""

        # Spanish vowel mapping
        vowels = "aeiouáéíóú"
        vowel_indices = [i for i, char in enumerate(last_word) if char in vowels]

        if not vowel_indices:
            return RhymeKey(consonant=last_word, assonant="")

        # Determine last stressed vowel index (default to penultimate vowel or last vowel if aguda)
        stress_idx = vowel_indices[-1]
        for idx in vowel_indices:
            if last_word[idx] in "áéíóú":
                stress_idx = idx
                break
        else:
            if len(vowel_indices) >= 2 and last_word[-1] in "aeiouns":
                stress_idx = vowel_indices[-2]

        consonant_rhyme = last_word[stress_idx:]
        # Normalize accents
        consonant_norm = (
            consonant_rhyme.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )

        assonant_rhyme = "".join([c for c in consonant_norm if c in "aeiou"])

        return RhymeKey(consonant=consonant_norm, assonant=assonant_rhyme)

    def classify_stanza(self, lines: list[str]) -> str | None:
        """Classify a stanza against known Spanish form structures."""
        if not lines:
            return None

        try:
            rantanplan = self._ensure_rantanplan()
            analysis = rantanplan.get_scansion(lines)
            if isinstance(analysis, dict) and "stanza_type" in analysis:
                return analysis["stanza_type"]
        except Exception:
            pass

        # Pure Python fallback by line count
        count = len(lines)
        if count == 14:
            return "soneto"
        elif count == 4:
            return "cuarteto / redondilla"
        elif count == 3:
            return "terceto"
        elif count == 2:
            return "pareado"

        return f"estanza_{count}_versos"


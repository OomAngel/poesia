"""Spanish phonology / scansion backend.

Wraps `fonemas` for syllabification + stress detection, and `silabeador` as
fallback. Implements sinalefa (vowel elision across word boundaries) which is
essential for correct Spanish metre counting.

Sinalefa: When a word ends in a vowel and the next begins with a vowel (or h+vowel),
they merge into a single metrical syllable. This is THE defining nuance of Spanish
scansion that naive per-word syllable counting misses.

Example: "la aurora" → orthographic: 4 syllables, metrical: 3 (la-au-ro-ra → lau-ro-ra)
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult, Stress

# Spanish vowels (including accented)
VOWELS = set("aeiouáéíóúAEIOUÁÉÍÓÚ")
WEAK_VOWELS = set("iuíúIUÍÚ")
STRONG_VOWELS = set("aeoáéóAEOÁÉÓ")


def _count_sinalefas(words: list[str]) -> int:
    """Count sinalefas (vowel elisions) between adjacent words.

    Fallback path only (no fonemas); ``spanish_metre`` is the measured counter. A sinalefa
    occurs when word N ends in a vowel and word N+1 starts with a vowel, h + vowel, or is "y".

    Each sinalefa reduces the metrical syllable count by 1.
    """
    if len(words) < 2:
        return 0

    count = 0
    for i in range(len(words) - 1):
        word1 = words[i].lower().rstrip(".,;:!?\"'")
        word2 = words[i + 1].lower().lstrip(".,;:!?\"'¡¿")

        if not word1 or not word2:
            continue

        # A final consonant (los ojos) never joins; "y" starts a vowel only as the word "y"
        ends_vowel = word1[-1] in VOWELS
        starts_vowel = (
            word2[0] in VOWELS
            or (word2[0] == "h" and len(word2) > 1 and word2[1] in VOWELS)
            or word2 == "y"
        )

        if ends_vowel and starts_vowel:
            count += 1

    return count


def _final_stress_adjustment(words: list[str], base_count: int) -> int:
    """Adjust syllable count based on final word stress (Spanish verse rules).

    - Oxytone (aguda, stress on last syllable): +1 syllable
    - Proparoxytone (esdrújula, stress on antepenult): -1 syllable
    - Paroxytone (llana, stress on penult): no change (default)
    """
    if not words:
        return base_count

    last_word = words[-1].lower().rstrip(".,;:!?\"'")
    if not last_word:
        return base_count

    # Check for explicit accent marks
    for i, char in enumerate(last_word):
        if char in "áéíóú":
            # Accent on last syllable (aguda) → +1
            # Check if this is the last vowel cluster
            remaining = last_word[i + 1 :]
            vowels_after = sum(1 for c in remaining if c in VOWELS)
            if vowels_after == 0:
                return base_count + 1
            # Accent not on last syllable
            consonants_after = sum(1 for c in remaining if c not in VOWELS)
            if vowels_after >= 2 or (vowels_after == 1 and consonants_after > 1):
                return base_count - 1  # esdrújula
            return base_count

    # No accent mark — apply default rules
    if last_word[-1] in "aeioun s":
        # Ends in vowel/n/s → llana (penult stress) → no change
        return base_count
    else:
        # Ends in consonant (not n/s) → aguda (last syllable stress) → +1
        return base_count + 1


class SpanishPhonology:
    """Scans and validates Spanish verse lines.

    Backends (lazily imported so the base package has no hard dependency):
        - rantanplan: metric syllable count, stress pattern, stanza detection
        - silabeador: syllabification + prosodic stress, lower-level fallback
        - fonemas: phonological transcription for rhyme validation
    """

    def __init__(self, variety: str = "seseo") -> None:
        # rhyme variety: "seseo" (Mexico, Latin America; casa/caza rhyme) or "distincion"
        self.variety = variety
        self._rantanplan = None  # lazy-loaded
        self._fonemas = None  # lazy-loaded
        self._silabeador = None  # lazy-loaded (fallback)

    def _ensure_rantanplan(self):
        if self._rantanplan is None:
            try:
                import rantanplan  # type: ignore[import-untyped]

                self._rantanplan = rantanplan
            except ImportError:
                self._rantanplan = False  # Mark as unavailable
        return self._rantanplan if self._rantanplan else None

    def _ensure_fonemas(self):
        if self._fonemas is None:
            try:
                from fonemas.fonemas import Transcription  # type: ignore[import-untyped]

                self._fonemas = Transcription
            except ImportError:
                self._fonemas = False
        return self._fonemas if self._fonemas else None

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

        Returns a ScanResult with metrical syllable count (including sinalefa
        adjustments), stress pattern, and validity flag.

        Metrical count = orthographic syllables - sinalefas ± final stress adjustment
        """
        words = [w for w in line.split() if w.strip()]
        if not words:
            return ScanResult(line=line, metrical_syllable_count=0, is_valid=False)

        # Try fonemas first (syllables + stress); the count comes from spanish_metre
        Transcription = self._ensure_fonemas()
        if Transcription:
            from poesia.phonology.spanish_metre import metrical_counts
            from poesia.phonology.spanish_metre import words as metre_words

            # lexical stress per syllable, before synalepha (as before 2026-10-10)
            stress_pattern = [
                Stress.PRIMARY if "ˈ" in syl else Stress.UNSTRESSED
                for w in metre_words(line)
                for syl in w.syllables
            ]
            metrical_count, licensed = metrical_counts(line)
            return ScanResult(
                line=line,
                metrical_syllable_count=metrical_count,
                stress_pattern=tuple(stress_pattern),
                is_valid=metrical_count > 0,
                metrical_counts=licensed,
            )

        # Fall back to silabeador (basic syllable counting, no stress)
        silabeador = self._ensure_silabeador()
        if silabeador:
            total_syllables = 0
            for word in words:
                clean_word = "".join(c for c in word if c.isalpha())
                if clean_word:
                    syllables = silabeador.syllabify(clean_word)
                    total_syllables += len(syllables)

            # Apply sinalefa (vowel elision across word boundaries)
            sinalefa_count = _count_sinalefas(words)
            metrical_count = total_syllables - sinalefa_count

            # Apply final stress adjustment
            metrical_count = _final_stress_adjustment(words, metrical_count)

            return ScanResult(
                line=line,
                metrical_syllable_count=metrical_count,
                is_valid=metrical_count > 0,
            )

        # No backend available
        raise RuntimeError("No Spanish phonology backend installed. Run: pip install fonemas")

    def rhyme_key(self, line: str) -> RhymeKey:
        """Consonant + assonant rhyme by sound (``spanish_rhyme``), in this scanner's variety."""
        from poesia.phonology.spanish_rhyme import spanish_rhyme_key

        return spanish_rhyme_key(line, self.variety)

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

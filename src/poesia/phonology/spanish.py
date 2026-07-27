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

import re

from poesia.phonology.base import RhymeKey, ScanResult, Stress

# Spanish vowels (including accented)
VOWELS = set("aeiouáéíóúAEIOUÁÉÍÓÚ")
WEAK_VOWELS = set("iuíúIUÍÚ")
STRONG_VOWELS = set("aeoáéóAEOÁÉÓ")


def _count_sinalefas(words: list[str]) -> int:
    """Count sinalefas (vowel elisions) between adjacent words.

    A sinalefa occurs when:
    - Word N ends in a vowel (or vowel + consonant like 'n', 's')
    - Word N+1 starts with a vowel (or 'h' + vowel, or 'y')

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

        # Check if word1 ends in vowel (possibly followed by n/s)
        ends_vowel = False
        if word1[-1] in VOWELS:
            ends_vowel = True
        elif len(word1) >= 2 and word1[-1] in "ns" and word1[-2] in VOWELS:
            ends_vowel = True

        # Check if word2 starts with vowel (or h+vowel, or y)
        starts_vowel = False
        if word2[0] in VOWELS:
            starts_vowel = True
        elif word2[0] == "h" and len(word2) > 1 and word2[1] in VOWELS:
            starts_vowel = True
        elif word2[0] == "y":
            starts_vowel = True

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
            remaining = last_word[i + 1:]
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

    def __init__(self) -> None:
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

        # Try fonemas first (syllables + stress)
        Transcription = self._ensure_fonemas()
        if Transcription:
            total_syllables = 0
            stress_pattern: list[Stress] = []
            for word in words:
                clean_word = "".join(c for c in word if c.isalpha())
                if clean_word:
                    try:
                        t = Transcription(clean_word)
                        syllables = t.phonology.syllables
                        total_syllables += len(syllables)
                        # Check each syllable for stress marker (ˈ)
                        for syl in syllables:
                            if "ˈ" in syl:
                                stress_pattern.append(Stress.PRIMARY)
                            else:
                                stress_pattern.append(Stress.UNSTRESSED)
                    except Exception:
                        # Fallback for unknown words: estimate 1 syllable per 2-3 chars
                        est_syl = max(1, len(clean_word) // 3)
                        total_syllables += est_syl
                        stress_pattern.extend([Stress.UNSTRESSED] * est_syl)

            # Apply sinalefa (vowel elision across word boundaries)
            sinalefa_count = _count_sinalefas(words)
            metrical_count = total_syllables - sinalefa_count

            # Apply final stress adjustment (aguda +1, esdrújula -1)
            metrical_count = _final_stress_adjustment(words, metrical_count)

            return ScanResult(
                line=line,
                metrical_syllable_count=metrical_count,
                stress_pattern=tuple(stress_pattern),
                is_valid=metrical_count > 0,
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
        raise RuntimeError(
            "No Spanish phonology backend installed. Run: pip install fonemas"
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


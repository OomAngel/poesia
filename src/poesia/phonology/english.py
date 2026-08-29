"""English phonology / scansion backend.

Wraps `pronouncing` (CMUdict-backed) for rhyme lookup, phoneme sequences and
lexical stress, and `prosodic` for full metrical parsing (feet, stress
sequences, alternative scansions). `g2p_en` (a neural grapheme-to-phoneme
model, ARPAbet output — the same phoneme alphabet CMUdict uses) is the
fallback for out-of-vocabulary words not present in CMUdict: LLM-invented
forms, neologisms, proper nouns. Because both backends speak ARPAbet,
`pronouncing`'s own `stresses()`/`rhyming_part()` utilities work unmodified
on either one — a CMUdict hit and a g2p_en fallback produce directly
comparable rhyme keys, not two incompatible representations glued together.

Phase 1 status: CMUdict + g2p_en fallback cover stress/rhyme lookup for any
word, including OOV ones — previously this raised on OOV words instead of
degrading. `scan_line` is still word-level only (prosodic's foot-level
parsing is not yet wired in).
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult, Stress


class EnglishPhonology:
    """Scans and validates English verse lines.

    Backends (lazily imported):
        - pronouncing (+ cmudict): rhyme lookup, phoneme sequences, stress
        - prosodic: full metrical parsing (feet, alternative scansions)
        - g2p_en: neural G2P fallback (ARPAbet) for words CMUdict does not know
    """

    def __init__(self) -> None:
        self._pronouncing = None  # lazy-loaded
        self._g2p = None  # lazy-loaded fallback for OOV words

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

    def _ensure_g2p(self):
        """Lazy-load the g2p_en fallback.

        Returns None (never raises) if unavailable — a missing fallback
        library is treated the same as a CMUdict miss with no fallback,
        not as a reason to crash the whole generation loop over one word.
        """
        if self._g2p is None:
            try:
                from g2p_en import G2p  # type: ignore[import-untyped]
            except ImportError:  # pragma: no cover - environment dependent
                self._g2p = False
            else:
                self._g2p = G2p()
        return self._g2p or None

    def _fallback_phones(self, word: str) -> str | None:
        """ARPAbet phone string for a word CMUdict does not know, via g2p_en.

        Returned space-joined, matching the format `pronouncing.phones_for_word`
        returns, so `pronouncing.stresses`/`rhyming_part` accept it unchanged —
        no separate parsing path needed for the fallback case.
        """
        g2p = self._ensure_g2p()
        if g2p is None:
            return None
        phones = [p for p in g2p(word) if p.strip()]
        return " ".join(phones) if phones else None

    def stresses_for_word(self, word: str) -> str | None:
        """Return the CMUdict stress digit string for a word, e.g. '1' or '0102'.

        Falls back to g2p_en for words CMUdict does not know, rather than
        returning None the way an unrecognised word used to be treated.
        """
        pronouncing = self._ensure_pronouncing()
        phones = pronouncing.phones_for_word(word.lower())
        phone_str = phones[0] if phones else self._fallback_phones(word)
        if phone_str is None:
            return None
        return pronouncing.stresses(phone_str)

    def rhymes_for_word(self, word: str) -> list[str]:
        """Return CMUdict rhyme candidates for a word."""
        pronouncing = self._ensure_pronouncing()
        return pronouncing.rhymes(word.lower())

    def scan_line(self, line: str) -> ScanResult:
        """Scan a single line of English verse.

        Phase 1: word-level stress lookup only, no full metrical foot
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
        """Extract a rhyme signature from the final word of a line.

        Falls back to g2p_en for a last word CMUdict does not know. Only
        raises if neither backend can produce a pronunciation at all (no
        g2p_en installed, and the word is OOV) — matching Spanish's
        phonology, which only raises when no backend is installed at all,
        never merely because a word is unrecognised.
        """
        words = [w.strip(".,;:!?\"'()") for w in line.split()]
        if not words:
            raise ValueError("Cannot extract rhyme key from an empty line.")
        last_word = words[-1]
        pronouncing = self._ensure_pronouncing()
        phones = pronouncing.phones_for_word(last_word.lower())
        phone_str = phones[0] if phones else self._fallback_phones(last_word)
        if phone_str is None:
            raise ValueError(
                f"No pronunciation found for '{last_word}' in CMUdict, and "
                "the g2p_en fallback is unavailable. Run: "
                "pip install -e '.[english]' g2p_en"
            )
        rhyme_part = pronouncing.rhyming_part(phone_str)
        return RhymeKey(consonant=rhyme_part, assonant=rhyme_part)

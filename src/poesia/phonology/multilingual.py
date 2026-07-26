"""Multilingual phonology fallback layer.

Used when a language-specific backend (spanish.py, english.py) is unavailable,
or for out-of-vocabulary words within a supported language. Backed by
`phonemizer` (eSpeak NG / Festival backends) for phoneme sequences and
`epitran` for consistent IPA transcription across languages.

Phase 0 status: interface only.
"""

from __future__ import annotations


class MultilingualPhonology:
    """Language-agnostic phonemic transcription via phonemizer / epitran."""

    def __init__(self, language: str) -> None:
        self.language = language
        self._phonemizer_backend = None  # lazy-loaded

    def to_phonemes(self, text: str) -> str:
        """Transcribe text to a phoneme string using phonemizer's eSpeak NG backend."""
        try:
            from phonemizer import phonemize  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "phonemizer is not installed. Run: pip install -e '.[phonology-multi]'"
            ) from exc
        return phonemize(text, language=self.language, backend="espeak")

    def to_ipa(self, text: str) -> str:
        """Transcribe text to IPA using epitran (consistent cross-language IPA)."""
        try:
            import epitran  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "epitran is not installed. Run: pip install -e '.[phonology-multi]'"
            ) from exc
        epi = epitran.Epitran(self.language)
        return epi.transliterate(text)

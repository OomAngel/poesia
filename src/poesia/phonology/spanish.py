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
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise RuntimeError(
                    "rantanplan is not installed. Run: pip install -e '.[spanish]'"
                ) from exc
            self._rantanplan = rantanplan
        return self._rantanplan

    def scan_line(self, line: str) -> ScanResult:
        """Scan a single line of Spanish verse.

        Returns a ScanResult with metrical syllable count, stress pattern and
        rhyme key populated from rantanplan's analysis. Raises RuntimeError
        with an actionable message if rantanplan is not installed.
        """
        rantanplan = self._ensure_rantanplan()
        analysis = rantanplan.get_scansion(line)
        # NOTE: exact rantanplan API surface to be confirmed against installed
        # version; this is a structural placeholder for Phase 0.
        return ScanResult(
            line=line,
            metrical_syllable_count=analysis.get("num_syllables", 0),
            is_valid=analysis.get("num_syllables", 0) > 0,
        )

    def rhyme_key(self, line: str) -> RhymeKey:
        """Extract consonant + assonant rhyme signature from a line's ending."""
        raise NotImplementedError(
            "Rhyme key extraction pending fonemas/rantanplan integration."
        )

    def classify_stanza(self, lines: list[str]) -> str | None:
        """Classify a stanza against rantanplan's ~45 known Spanish forms."""
        raise NotImplementedError("Stanza classification pending rantanplan wiring.")

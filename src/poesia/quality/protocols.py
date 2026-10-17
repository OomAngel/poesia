"""Interfaces for the model-backed parts of the quality layer; clients live outside.

Evidence that shapes them (research report 2026-10-10):
- Judges should reject, not crown: the best judge in POEMetric reached Spearman 0.378 against
  seven poetry experts; for Apertus output the judge should come from another model family
  (self-preference survives prompting), and its verdict picks out stiff or senseless lines.
- Raw embedding cosines between lines bunch together (e5: 0.83-0.90 on Calaveritas lines);
  compare within a candidate set or after centring, never against a fixed threshold.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Judge(Protocol):
    def forced(self, lines: Sequence[str], language: str) -> list[int] | None:
        """0-based indexes of lines that read as forced; [] if none; None if unreadable."""
        ...


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text (normalised or not; callers centre before comparing)."""
        ...

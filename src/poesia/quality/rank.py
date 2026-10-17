"""Choose among candidate lines or stanzas: gates first, then sense, then form distance.

The order is lexicographic, as in the web page's ``_proposal_rank`` (the one ranking in the
engine that never lost rhyme): a candidate with no defect always beats one with a defect;
among equals, the higher sense score wins; form distance only breaks ties. Sense signals are
added with their weights; a signal that was not measured is recorded as absent and adds
nothing, so it can never stand in for a zero or move weight onto the others.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from poesia.quality.gates import Defect


@dataclass
class Candidate:
    text: str
    defects: list[Defect] = field(default_factory=list)
    form_distance: float = 0.0  # e.g. |count - target| when outside the licensed set
    signals: dict[str, float | None] = field(default_factory=dict)  # None = not measured

    @property
    def passes(self) -> bool:
        return not self.defects

    def sense(self, weights: Mapping[str, float]) -> float:
        return sum(
            weights.get(name, 0.0) * value
            for name, value in self.signals.items()
            if value is not None
        )

    def absent(self) -> list[str]:
        return [name for name, value in self.signals.items() if value is None]


def rank(candidates: Iterable[Candidate], weights: Mapping[str, float]) -> list[Candidate]:
    """Best first. Stable: equal candidates keep their order."""
    return sorted(
        candidates,
        key=lambda c: (len(c.defects), -c.sense(weights), c.form_distance),
    )


def best(candidates: Iterable[Candidate], weights: Mapping[str, float]) -> Candidate | None:
    ranked = rank(candidates, weights)
    return ranked[0] if ranked else None

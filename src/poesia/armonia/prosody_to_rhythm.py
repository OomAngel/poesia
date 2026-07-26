"""Prosody -> rhythm mapping: the conceptual bridge between phonology and music.

Maps a scanned line's stress pattern onto a rhythmic grid: PRIMARY stress ->
downbeat/strong pulse, SECONDARY -> medium pulse, UNSTRESSED -> weak/off-beat.
This is the shared idea that makes ArmonIA a natural extension of the
phonology layer rather than a bolted-on feature.

Phase 0 status: interface + naive placeholder mapping.
"""

from __future__ import annotations

from dataclasses import dataclass

from poesia.phonology.base import Stress


@dataclass(frozen=True)
class RhythmicPulse:
    """A single beat position with a relative strength weight."""

    position: int
    strength: float  # 0.0 (weak) .. 1.0 (strong downbeat)


def stress_pattern_to_pulses(stress_pattern: tuple[Stress, ...]) -> list[RhythmicPulse]:
    """Naively map a stress pattern to a sequence of rhythmic pulses.

    PRIMARY -> 1.0, SECONDARY -> 0.5, UNSTRESSED -> 0.15. Phase 2 upgrade:
    feed this into `poesia.armonia.backends.ScoreBackend` to produce an
    actual MIDI/MusicXML rhythm track via music21.
    """
    weight_by_stress = {
        Stress.PRIMARY: 1.0,
        Stress.SECONDARY: 0.5,
        Stress.UNSTRESSED: 0.15,
    }
    return [
        RhythmicPulse(position=i, strength=weight_by_stress[s])
        for i, s in enumerate(stress_pattern)
    ]

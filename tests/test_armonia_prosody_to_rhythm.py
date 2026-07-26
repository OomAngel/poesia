"""Tests for poesia.armonia.prosody_to_rhythm: stress pattern -> rhythm pulses."""

from __future__ import annotations

from poesia.armonia.prosody_to_rhythm import RhythmicPulse, stress_pattern_to_pulses
from poesia.phonology.base import Stress


def test_empty_stress_pattern_yields_no_pulses() -> None:
    assert stress_pattern_to_pulses(()) == []


def test_maps_primary_secondary_unstressed_to_expected_weights() -> None:
    pattern = (Stress.PRIMARY, Stress.SECONDARY, Stress.UNSTRESSED)
    pulses = stress_pattern_to_pulses(pattern)
    assert pulses == [
        RhythmicPulse(position=0, strength=1.0),
        RhythmicPulse(position=1, strength=0.5),
        RhythmicPulse(position=2, strength=0.15),
    ]


def test_positions_are_sequential_and_zero_indexed() -> None:
    pattern = (Stress.UNSTRESSED,) * 5
    pulses = stress_pattern_to_pulses(pattern)
    assert [p.position for p in pulses] == [0, 1, 2, 3, 4]


def test_rhythmic_pulse_is_frozen() -> None:
    pulse = RhythmicPulse(position=0, strength=1.0)
    try:
        pulse.strength = 0.0  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("RhythmicPulse should be frozen (immutable)")

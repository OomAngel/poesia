"""Music/audio backend ports for ArmonIA.

Three independent Protocol seams, matching the three tiers of ambition:
    - ScoreBackend: symbolic music (MIDI/MusicXML) from a stress pattern
    - AudioSynthBackend: renders a symbolic score to audio (soundfont)
    - RecitationBackend: text-to-speech recitation of the poem itself

Keeping these separate means a user can get spoken recitation (cheapest,
via eSpeak NG through the phonology layer's existing dependency) without
pulling in the heavier symbolic-music or AI-music-generation stacks.
"""

from __future__ import annotations

from typing import Protocol

from poesia.phonology.base import Stress


class ScoreBackend(Protocol):
    """Produces a symbolic score (e.g. MIDI bytes) from a stress pattern."""

    def stress_to_score(self, stress_pattern: tuple[Stress, ...], tempo_bpm: int = 90) -> bytes:
        """Map a stress pattern to a symbolic score and return MIDI bytes."""
        ...


class AudioSynthBackend(Protocol):
    """Renders a symbolic score to audio."""

    def render(self, score_bytes: bytes) -> bytes:
        """Return raw audio bytes (WAV) rendered from a MIDI score."""
        ...


class RecitationBackend(Protocol):
    """Text-to-speech recitation of a poem."""

    def recite(self, text: str, language: str) -> bytes:
        """Return raw audio bytes (WAV) of the text spoken aloud."""
        ...


class StubScoreBackend:
    """Deterministic no-op ScoreBackend for tests and offline development."""

    def stress_to_score(self, stress_pattern: tuple[Stress, ...], tempo_bpm: int = 90) -> bytes:
        return b""


# --- Candidate real backends (Phase 2+, not yet implemented) ----------------
#
# Music21ScoreBackend      -> wraps `music21` for stress->rhythm mapping,
#                             MusicXML/MIDI export.
# FluidSynthAudioBackend   -> wraps `pyfluidsynth` + a .sf2 SoundFont to
#                             render MIDI to audio.
# MusicGenBackend          -> wraps `audiocraft` (Meta MusicGen) for local
#                             text-to-music generation.
# PiperRecitationBackend   -> wraps `piper` (fast, local TTS) for recitation.
# EspeakRecitationBackend  -> reuses the eSpeak NG dependency already present
#                             via `poesia.phonology.multilingual` for a free,
#                             low-quality recitation fallback.

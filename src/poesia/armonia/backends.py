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


class MidiScoreBackend:
    """Produces valid standard MIDI score bytes from a prosodic stress pattern."""

    def stress_to_score(self, stress_pattern: tuple[Stress, ...], tempo_bpm: int = 90) -> bytes:
        """Map stress pattern to rhythmic MIDI notes and return .mid bytes."""
        if not stress_pattern:
            return b""

        # MIDI Header: Format 0, 1 Track, 96 Ticks per Quarter Note (0x0060)
        header = b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60"

        # Construct Track events
        events = bytearray()

        # Set Tempo meta-event: 60,000,000 / tempo_bpm
        microseconds_per_quarter = int(60_000_000 / max(30, min(300, tempo_bpm)))
        tempo_bytes = microseconds_per_quarter.to_bytes(3, "big")
        events.extend(b"\x00\xff\x51\x03" + tempo_bytes)

        note = 60  # Middle C (C4)
        ticks_per_quarter = 96
        ticks_per_eighth = 48

        for stress in stress_pattern:
            if stress == Stress.PRIMARY:
                duration = ticks_per_quarter
                velocity = 100
            elif stress == Stress.SECONDARY:
                duration = ticks_per_eighth
                velocity = 70
            else:  # UNSTRESSED
                duration = ticks_per_eighth
                velocity = 40

            # Note On (Channel 0, Note 60, Velocity)
            events.extend(b"\x00\x90" + bytes([note, velocity]))

            # Note Off after duration ticks
            # Convert duration to variable-length quantity
            delta_time = self._to_var_length(duration)
            events.extend(delta_time + b"\x80" + bytes([note, 0]))

        # End of Track meta event
        events.extend(b"\x00\xff\x2f\x00")

        track_header = b"MTrk" + len(events).to_bytes(4, "big")
        return header + track_header + bytes(events)

    @staticmethod
    def _to_var_length(val: int) -> bytes:
        """Convert integer to MIDI variable length byte sequence."""
        buf = bytearray()
        buf.append(val & 0x7F)
        val >>= 7
        while val > 0:
            buf.insert(0, (val & 0x7F) | 0x80)
            val >>= 7
        return bytes(buf)


class EspeakRecitationBackend:
    """Text-to-speech recitation using system eSpeak NG binary."""

    def recite(self, text: str, language: str = "es") -> bytes:
        import shutil
        import subprocess

        espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        if not espeak_bin:
            raise RuntimeError(
                "eSpeak NG binary is not installed. Install via your package manager "
                "(e.g. 'sudo apt install espeak-ng')."
            )

        lang_code = "es" if language.lower().startswith("es") else "en"
        cmd = [espeak_bin, "-v", lang_code, "--stdout", text]

        try:
            res = subprocess.run(cmd, capture_output=True, check=True)  # noqa: S603 - trusted fixed binary + arg list
            return res.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"eSpeak recitation failed: {e.stderr.decode('utf-8')}") from e

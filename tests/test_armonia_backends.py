"""Unit tests for ArmonIA backends (MidiScoreBackend and EspeakRecitationBackend)."""

from __future__ import annotations

import pytest

from poesia.armonia.backends import EspeakRecitationBackend, MidiScoreBackend
from poesia.phonology.base import Stress


def test_midi_score_backend_empty() -> None:
    backend = MidiScoreBackend()
    assert backend.stress_to_score(()) == b""


def test_midi_score_backend_valid_midi() -> None:
    backend = MidiScoreBackend()
    pattern = (Stress.PRIMARY, Stress.UNSTRESSED, Stress.SECONDARY, Stress.PRIMARY)
    midi_bytes = backend.stress_to_score(pattern, tempo_bpm=120)

    assert midi_bytes.startswith(b"MThd")
    assert b"MTrk" in midi_bytes


def test_espeak_recitation_backend_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate a machine without eSpeak NG (the desktop has it since 2026-10-07).
    monkeypatch.setattr("shutil.which", lambda _name: None)
    backend = EspeakRecitationBackend()
    with pytest.raises(RuntimeError, match="eSpeak NG binary is not installed"):
        backend.recite("En el principio era el Verbo", language="es")


def test_espeak_recitation_backend_returns_wav_when_installed() -> None:
    import shutil

    if not (shutil.which("espeak-ng") or shutil.which("espeak")):
        pytest.skip("eSpeak NG not installed on this machine")
    audio = EspeakRecitationBackend().recite("En el principio era el Verbo", language="es")
    assert audio.startswith(b"RIFF")

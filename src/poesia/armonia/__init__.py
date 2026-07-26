"""ArmonIA — music.

*Armonía* (harmony). Turns a poem's prosody into music: stressed syllables
map to rhythmic downbeats, stanza structure maps to phrase/section
structure. Distinct from EufonIA (which judges the sound of the words
themselves) — ArmonIA is the module that produces actual audio/score output.

Backends span three tiers: symbolic (score/MIDI via music21), audio
rendering (soundfont synthesis), and AI music generation (MusicGen) or
text-to-speech recitation. See `backends.py` for the Protocol seams.

Phase 0 status: interfaces only.
"""

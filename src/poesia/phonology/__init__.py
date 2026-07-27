"""Deterministic phonology and prosody validators.

This package must never call an LLM. It is the "ground truth" layer that
scans, scores and validates candidate lines produced upstream by the
generation layer. Keep it fast, deterministic and language-scoped.

Modules:
    base.py      - shared data structures (ScanResult, StressPattern, RhymeKey)
    spanish.py   - rantanplan / silabeador / fonemas backed scansion
    english.py   - pronouncing / cmudict / prosodic backed scansion
    dutch.py     - pyphen-backed syllabification for Dutch
    multilingual.py - phonemizer / epitran fallback for OOV or new languages
"""

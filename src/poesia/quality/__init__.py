"""Shared poem-quality layer for every PoesIA deployment (engine, web page, entry, Calaveritas).

Design and evidence: ``docs/research/reports/PoesIA shared poem quality layer.md`` (2026-10-10).
In short, gate the form, rank the sense, measure drift:

- ``gates``: one pure check per defect, each returning a defect code or ``None``. Metre passes
  when the target is among the counts the language's licences allow (``ScanResult.
  metrical_counts``); rhyme is decided by the phonetic key, never by a model.
- ``rank``: candidates that pass every gate come first, then the sense score, then distance
  from the form as a tie-breaker. Signals are added, never renormalised, and an absent signal
  is kept apart from a zero (the engine's ``composite_score`` let an unrhymed exact line beat a
  rhyming one when no embedding client was loaded).
- ``diversity``: batch measures of drift (distinct openings, end-word concentration).
- ``repair``: the instruction for each defect, per language, naming the rhyme to reach with
  "one of these or your own" and never a forced word.
- ``protocols``: ``Judge`` and ``Embedder`` interfaces; concrete clients stay outside.

Layering: imports only ``poesia.quality`` and ``poesia.phonology``.
"""

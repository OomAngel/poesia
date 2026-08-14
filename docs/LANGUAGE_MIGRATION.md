# Language migration notes

Recorded 2026-08-14 — federation/engine review (see `ci-infra/docs/FEDERATION.md`).

## Candidate: phonology + prosody/rhyme engine → Rust crate

- **What**: `src/poesia/phonology/` (base/dutch/english/spanish/multilingual),
  `src/poesia/armonia/prosody_to_rhythm.py`, `src/poesia/generation/rhyme_tracker.py`.
- **Why**: pure deterministic algorithm, zero ML — the cleanest native extraction in the
  estate. A `poesia-phonology` crate is exhaustively testable and shareable.
- **Stays Python**: the LLM generation layer, orchestration, illustration/collections.

## Federation tie-in

A versioned Rust crate is the cleanest "live on its own" artifact + release surface for a
shared agent. Python remains the agent's orchestration/LLM glue.

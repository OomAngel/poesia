# Active Context — PoesIA

_Last updated: Phase 0 scaffold completion._

## What We Just Did

Completed the Phase 0 scaffold for **PoesIA**, a personal hybrid poetry-writing
tool (LLM generation + deterministic phonology validation), with a family of
five sub-modules each named after a real Spanish "-ía" word matching its
responsibility:

- `poesia` (root CLI: `write`, `scan`) — the generation loop itself
- `eufonia` — sound/euphony analysis (rhyme scheme, assonance, consonance)
- `galeria` — illustration (auca/aleluya illustrated-verse sheets)
- `armonia` — music (prosody → rhythm → score/audio/recitation)
- `memoria` — poem library now, Graph RAG corpus later (Phase 3)

Renamed the whole project from an earlier `poiesis` scaffold to `poesia`
after a long naming search (see `docs/NAMING.md` for the full story).
Verified `poesia` is unregistered on PyPI (HTTP 404).

Wrote four docs: `docs/ARCHITECTURE.md` (layering rules + seam discipline),
`docs/ROADMAP.md` (Phase 0/1/2/3 breakdown), `docs/NAMING.md` (naming
rationale + history), `docs/PACKAGES_SURVEYED.md` (full dependency survey by
concern area).

Added `tests/` stubs for the currently-functional pieces (`forms/definitions.py`,
`memoria/library.py`, `armonia/prosody_to_rhythm.py`, `phonology/base.py`).

Initialized local git repo — **no remote configured, intentionally**. This
is a personal project; do not add a GitHub/GitLab remote unless explicitly
asked.

## Current Focus

Phase 0 scaffold is done. Nothing is actively "in flight" right now — the
next work session should pick up Phase 1 from `docs/ROADMAP.md`:

1. Wire a real `LLMClient` (llama-cpp-python or transformers backend) to
   replace `StubLLMClient`.
2. Implement `EuphonyAnalyzer.analyze()` for real (currently
   `NotImplementedError`) — this is the first real EufonIA feature.
3. Add sentence-transformers-based `theme_score`/`novelty_score` in
   `evaluation/metrics.py` (currently `NotImplementedError`).
4. Persist `memoria.Library` to disk (JSON or SQLite) instead of in-memory.

## Open Questions

- LLM backend choice not yet made (local llama.cpp GGUF model vs. hosted API
  vs. both via the `LLMClient` Protocol) — deferred to Phase 1 start.
- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred per
  `docs/PACKAGES_SURVEYED.md` — do not implement `memoria/graphrag.py` until
  this is decided.
- No web frontend planned; CLI-only for the foreseeable future (explicit
  non-goal, see `docs/ROADMAP.md`).

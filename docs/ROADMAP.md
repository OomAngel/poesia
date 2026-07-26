# Roadmap

## Phase 0 — Scaffold (current)

- [x] Package layout: `phonology/`, `generation/`, `evaluation/`, `forms/`
- [x] Spanish + English phonology interfaces (rantanplan/silabeador,
      pronouncing/prosodic), lazy-imported, stub-safe without the extras installed
- [x] `StubLLMClient` + `ConstrainedLoop` control-flow skeleton
      (generate → score → repair, no real LLM call yet)
- [x] Form registry: soneto, romance (ES), Shakespearean sonnet, haiku (EN)
- [x] Four -IA feature modules scaffolded as documented interfaces:
      `eufonia/` (sound analysis), `galeria/` (illustration), `memoria/`
      (collections + future Graph RAG), `armonia/` (music)
- [x] CLI wired: `poesia write|scan|eufonia|galeria|memoria|armonia`
- [ ] Unit tests for phonology base types + form registry
- [ ] `git init` + first local commit

Phase 0 explicitly does **not** call any real LLM, image, or music backend.
Every heavy dependency is behind a lazy import with an actionable
`RuntimeError` pointing at the right `pip install -e ".[extra]"`.

## Phase 1 — Real generation loop

- Wire one real `LLMClient` implementation (hosted API first — fastest path
  to validate the loop; `llama-cpp-python` local inference as a follow-up)
- Wire `sentence-transformers` for `theme_score` / `novelty_score` in
  `evaluation/metrics.py` (currently `NotImplementedError`)
- Implement `EufonyAnalyzer.analyze` (rhyme scheme detection from RhymeKey
  sequences) — this is the natural first real feature to land, since it only
  needs the phonology layer, not an LLM or heavy ML.
- Persist `MemorIA.Library` to disk (JSON or SQLite) instead of in-memory only

## Phase 2 — Illustration, music, stylistic grounding

- `GalerIA`: wire one real `ImageBackend` (start with `openai` or
  `replicate` — hosted, no local GPU requirement), implement
  `AucaComposer.compose_panel` via Pillow + a diacritic-safe font
  (Noto Serif / EB Garamond), implement `export_pdf` via WeasyPrint
- `ArmonIA`: wire `music21` for `ScoreBackend` (stress pattern → MIDI),
  optionally `pyfluidsynth` for audio rendering; recitation via eSpeak NG
  (already a `phonology-multi` dependency) as the cheapest first step before
  considering `piper`/Coqui TTS
- Corpus ingestion groundwork: collect a small poet-specific corpus,
  evaluate KenLM vs. a transformer-based perplexity scorer (`lm-scorer`) for
  the cliché-penalty upgrade path noted in `evaluation/metrics.py`

## Phase 3 — Graph RAG (MemorIA)

- Land the storage backend decision (in-memory `networkx` graph vs. `neo4j`)
  — see `docs/PACKAGES_SURVEYED.md` for the tradeoff notes
- Implement `GraphRAGRetriever.ingest` / `.retrieve` in `memoria/graphrag.py`
- Poet/style nodes, influence edges, semantic-neighbourhood edges via
  `sentence-transformers` embeddings
- Wire retrieval into `CandidateGenerator` prompts as few-shot grounding,
  and into `GalerIA` illustration prompts for style anchoring

## Explicit non-goals for now

- No web frontend (Fabric.js, React) until a concrete need for interactive
  drag/drop poem-image composition emerges — Python-only Phase 0-2.
- No C++ code yet. The only anticipated C++ touch-points remain
  `llama.cpp` (via `llama-cpp-python`), eSpeak NG (already wrapped by
  `phonemizer`), and `OpenFst`/`Pynini` if a formal grammar-based metrical
  validator is ever justified by scale — none of these are needed at
  current project size.

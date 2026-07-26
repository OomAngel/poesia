# Tasks — PoesIA (Kanban)

## DONE (Phase 0)

- [x] Scaffold project (pyproject.toml, .gitignore, README)
- [x] `phonology/` — base dataclasses (Stress, Syllable, RhymeKey, ScanResult)
      + Spanish (rantanplan) / English (pronouncing) / multilingual
      (phonemizer/epitran) backends (lazy-imported)
- [x] `evaluation/` — metre_score, rhyme_score, cliche_penalty functional;
      theme_score/novelty_score stubbed (need sentence-transformers)
- [x] `forms/` — FormSpec + registry (soneto, romance, sonnet_shakespearean,
      haiku)
- [x] `generation/` — LLMClient Protocol + StubLLMClient, CandidateGenerator,
      ConstrainedLoop (generate→score→repair loop, functional against stub)
- [x] `eufonia/` — EuphonyAnalyzer skeleton (analyze() stubbed)
- [x] `galeria/` — ImageBackend Protocol + StubImageBackend (functional,
      returns real 1x1 PNG), AucaPanel/AucaComposer (compose/export stubbed)
- [x] `armonia/` — ScoreBackend/AudioSynthBackend/RecitationBackend Protocols,
      StubScoreBackend, stress_pattern_to_pulses (functional)
- [x] `memoria/` — PoemRecord + Library (fully functional, in-memory),
      GraphRAGRetriever skeleton (Phase 3, stubbed)
- [x] CLI wired: root `write`/`scan` + `eufonia analyze`, `galeria illustrate`,
      `memoria list/search`, `armonia rhythm`
- [x] Docs: ARCHITECTURE.md, ROADMAP.md, NAMING.md, PACKAGES_SURVEYED.md
- [x] memory-bank/ continuity files
- [x] tests/ initial stubs
- [x] git init + first local commit (no remote)

## IN PROGRESS

_(nothing currently in flight — pick up Phase 1 below at next session start)_

## BACKLOG (Phase 1 — see docs/ROADMAP.md for full detail)

- [ ] Choose + wire a real LLMClient backend (llama-cpp-python local GGUF,
      or hosted API, behind the existing Protocol)
- [ ] Implement `EuphonyAnalyzer.analyze()` for real
- [ ] Implement `theme_score`/`novelty_score` using sentence-transformers
- [ ] Persist `memoria.Library` (JSON or SQLite)
- [ ] Implement `SpanishPhonology.rhyme_key` / `classify_stanza`
      (currently NotImplementedError)
- [ ] Expand test coverage as each stub becomes real

## BLOCKED

- [ ] `memoria/graphrag.py` — blocked on storage backend decision
      (networkx vs. neo4j); do not implement until decided (Phase 3)
- [ ] `galeria/auca.py` compose_panel/compose_sheet/export_pdf — blocked on
      Phase 2 (needs Pillow layout work + WeasyPrint, not started)
- [ ] `armonia` real backends (music21/pyfluidsynth/TTS) — blocked on Phase 2

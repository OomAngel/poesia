# Progress — PoesIA

## Phase status

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Scaffold: package layout, 5 -IA modules, docs, tests, git init | ✅ Complete |
| 1 | Real LLM generation loop, EufonIA sound analysis, theme/novelty scoring, Library persistence | ⬜ Not started |
| 2 | GalerIA illustration backends, ArmonIA music backends, corpus/KenLM | ⬜ Not started |
| 3 | MemorIA Graph RAG (storage decision, ingestion, retrieval wiring) | ⬜ Not started |

## What's functional right now (Phase 0 end state)

- `EnglishPhonology.scan_line` / `.rhyme_key` — functional (via `pronouncing`)
- `evaluation.metrics.metre_score` / `rhyme_score` / `cliche_penalty` — functional
- `generation.ConstrainedLoop.run()` — functional end-to-end against
  `StubLLMClient` (produces deterministic placeholder lines, not real poetry
  yet — that needs Phase 1's real LLMClient)
- `forms.FORM_REGISTRY` / `get_form()` — functional, 4 forms registered
- `memoria.Library` — fully functional in-memory CRUD/search
- `armonia.stress_pattern_to_pulses` — functional naive mapping
- `galeria.StubImageBackend` — functional (returns a valid placeholder PNG)
- CLI (`poesia`, `poesia eufonia`, `poesia galeria`, `poesia memoria`,
  `poesia armonia`) — all subcommands wired and runnable, though several
  underlying operations still raise `NotImplementedError` until Phase 1/2/3

## What's explicitly NOT implemented yet (raises NotImplementedError)

- `SpanishPhonology.rhyme_key`, `.classify_stanza`
- `EuphonyAnalyzer.analyze`, `.detect_rhyme_scheme`
- `AucaComposer.compose_panel/.compose_sheet/.export_pdf`
- `evaluation.metrics.theme_score`, `.novelty_score`
- `memoria.graphrag.GraphRAGRetriever.ingest/.retrieve`

## No open architectural violations tracked

This is a small personal project, not currently using the DV-*/SM-*/ST-*
violation-tracking convention from the LumiNose project. If this project
grows large enough to need that discipline, adopt it explicitly rather than
retrofitting silently.

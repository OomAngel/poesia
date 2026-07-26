# Tasks — PoesIA (Kanban)

## DONE (Phase 0, Phase 1 & Phase 2 Complete)

- [x] Scaffold project (pyproject.toml, .gitignore, README)
- [x] `phonology/` — base dataclasses & Spanish/English/multilingual wrappers
- [x] `evaluation/` — metre_score, rhyme_score, cliche_penalty, theme_score, novelty_score
- [x] `forms/` — FormSpec + registry (soneto, romance, sonnet_shakespearean, haiku)
- [x] `generation/` — LLMClient Protocol, StubLLMClient, HostedLLMClient (Gemini REST & OpenAI REST)
- [x] `AGENTS.md` — guidelines, guardrails, and commit standards
- [x] `eufonia/` — `EuphonyAnalyzer.analyze()` & `detect_rhyme_scheme()` implemented
- [x] `memoria/` — `Library` Markdown YAML frontmatter storage (`~/.poesia/poems/*.md`) + SQLite auto-index
- [x] `galeria/` — `HostedImageBackend` (DALL-E 3 & Replicate SDXL) & Pillow `AucaComposer` (panel & sheet grid composition)
- [x] `armonia/` — `MidiScoreBackend` (pure Python prosodic MIDI generator) & `EspeakRecitationBackend`
- [x] `phonology/` — `SpanishPhonology.rhyme_key` & `classify_stanza`

## IN PROGRESS

- [ ] Phase 3: `memoria/graphrag.py` Graph RAG storage decision (NetworkX vs Neo4j)

## BACKLOG (Phase 3)

- [ ] `GraphRAGRetriever.ingest` / `.retrieve` implementations
- [ ] Incorporate Graph RAG few-shot retrieval into `CandidateGenerator`




## BLOCKED

- [ ] `memoria/graphrag.py` — blocked on storage backend decision (Phase 3)
- [ ] `galeria/auca.py` compose_panel/compose_sheet/export_pdf — blocked on Phase 2
- [ ] `armonia` real backends (music21/pyfluidsynth/TTS) — blocked on Phase 2



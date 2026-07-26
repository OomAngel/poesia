# Tasks — PoesIA (Kanban)

## DONE (Phases 0-3 Core Complete)

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
- [x] Phase 3: `memoria/graphrag.py` — NetworkX storage backend decision landed
- [x] `GraphRAGRetriever.ingest` / `.retrieve` implementations (commit `0135e4f`)

## IN PROGRESS

- [ ] Wire Graph RAG few-shot retrieval into `CandidateGenerator` prompts

## BACKLOG (Phase 3 Integration)

- [ ] Wire Graph RAG into `GalerIA` for illustration style anchoring
- [ ] Add embedding generation (lazy `sentence-transformers` integration)
- [ ] CLI `poesia memoria ingest` command with auto-embedding
- [ ] (Optional) Poet/style nodes + influence edges for richer graph structure

## BLOCKED

(None currently)



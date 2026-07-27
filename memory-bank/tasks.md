# Tasks — PoesIA (Kanban)

## DONE (Phases 0-3C Complete)

- [x] Scaffold project (pyproject.toml, .gitignore, README)
- [x] `phonology/` — base dataclasses & Spanish/English/multilingual wrappers
- [x] `evaluation/` — metre_score, rhyme_score, cliche_penalty, theme_score, novelty_score
- [x] `forms/` — FormSpec + registry (soneto, romance, sonnet_shakespearean, haiku)
- [x] `generation/` — LLMClient Protocol, StubLLMClient, HostedLLMClient
- [x] `eufonia/` — `EuphonyAnalyzer.analyze()` & `detect_rhyme_scheme()`
- [x] `memoria/` — Library (Markdown + SQLite)
- [x] `galeria/` — HostedImageBackend + AucaComposer
- [x] `armonia/` — MidiScoreBackend + EspeakRecitationBackend
- [x] Phase 3A: GraphRAGRetriever with NetworkX
- [x] Phase 3B: EmbeddingClient Protocol + SentenceTransformerClient (e5-base)
- [x] Phase 3C: Extended record types (Fragment, Seed, Influence)
- [x] Phase 3C: SeedExpander (WordNet, rhymes, semantic, Datamuse)
- [x] Design decisions (16 questions resolved)
- [x] First 10 personal fragments in `seeds/angel_fragments/`
- [x] Influence registry (24 poets)
- [x] Literary taxonomy

## IN PROGRESS

- [ ] Phase 3D: BriefBuilder — assemble generation prompts from:
  - Retrieved fragments
  - Expanded seeds
  - Influence anchors
  - Form spec + tone

## BACKLOG (Phase 3 Integration)

- [ ] Wire brief into CandidateGenerator
- [ ] Wire retrieval into GalerIA for style anchoring
- [ ] Ingestion CLI: `poesia memoria add-fragment|add-seed|add-influence`
- [ ] Auto-embed on ingest in GraphRAGRetriever

## BLOCKED

(None currently)



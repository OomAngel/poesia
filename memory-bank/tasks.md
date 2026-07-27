# Tasks — PoesIA (Kanban)

## DONE (Phases 0-3E Complete)

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
- [x] Phase 3D: BriefBuilder + GenerationBrief
- [x] Design decisions (16 questions resolved)
- [x] First 10 personal fragments in `seeds/angel_fragments/`
- [x] Influence registry (24 poets)
- [x] Literary taxonomy
- [x] Phase 3E: CandidateGenerator accepts GenerationBrief
- [x] Phase 3E: ConstrainedLoop wired to BriefBuilder
- [x] Phase 3E: CLI `write` with --tone/--seeds/--brief-level/--brief
- [x] Phase 3E: CLI `memoria add-fragment|add-seed|add-influence`
- [x] Phase 3E: CLI `memoria list-fragments|list-influences`
- [x] Phase 3E: Integration tests (test_integration_phase3e.py)

## IN PROGRESS

(None currently)

## BACKLOG

- [ ] Auto-embed on ingest in GraphRAGRetriever
- [ ] Wire retrieval into GalerIA for style anchoring (Phase 4)
- [ ] Test with real LLM backend (not StubLLMClient)
- [ ] Improve influence parsing from INFLUENCE_REGISTRY.md

## BLOCKED

(None currently)



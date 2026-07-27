# Tasks — PoesIA (Kanban)

## DONE (Phases 0-4 Complete)

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
- [x] Dutch phonology support via pyphen
- [x] Phase 4A: CLI `--llm gemini|openai|stub|auto` option
- [x] Phase 4B: Richer influence profile parsing (movement, era, exemplars)
- [x] Phase 4C: GalerIA style anchoring from influences
- [x] Phase 4D: Auto-embed on ingest in GraphRAGRetriever
- [x] Phase 4 tests (test_phase4_features.py)
- [x] **Gap fix**: LineScorer uses real theme_score/novelty_score/cliche_penalty
- [x] **Gap fix**: Spanish sinalefa (vowel elision) in metrical counting
- [x] **Gap fix**: CLI --brief tries real sentence-transformers first
- [x] Sinalefa + scorer tests (22 new tests)
- [x] **P0 hardening**: Embedding validation module with explicit error messages
- [x] **P0 hardening**: GraphRAGRetriever validates all embeddings (ingest + retrieval)
- [x] **P0 hardening**: LineScorer validates embeddings (theme + prior + candidates)
- [x] **P0 hardening**: Remove silent failures, expose validation errors
- [x] **P0 hardening**: 26 new tests for validation and contract enforcement
- [x] **P1 complete**: memoria list/search wired to real Library; --show-retrieval;
  --interactive human line selection with typed-own-line support; 9 new tests

## IN PROGRESS

- [ ] **RAG/LLM hardening P2:** typed graph nodes/relations and bounded explainable
  graph expansion (prerequisite: P1 now complete — see DONE below).

## BACKLOG

- [ ] P2: implement typed graph nodes/relations and bounded explainable graph expansion.
- [ ] P3: add immutable embedding/index compatibility identity and atomic versioned persistence.
- [ ] P4: build and evaluate a reviewed multilingual retrieval/generation corpus.
- [ ] P5: add hosted-provider privacy, lineage, retry, latency, token, and cost controls.
- [ ] Test with real LLM backend (set GEMINI_API_KEY or OPENAI_API_KEY)
- [ ] Phase 4E: Literary taxonomy auto-tagging
- [x] Mock-based tests for HostedLLMClient/HostedImageBackend HTTP shapes (27 tests)
- [x] Batching for Gemini API (candidateCount instead of N calls)
- [x] Move influence registry from markdown to YAML (data/influences.yaml)
- [x] GraphRAG graph-based retrieval (retrieve_graph_based with ego_graph)

## BLOCKED

(None currently)


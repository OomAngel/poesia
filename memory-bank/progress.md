# Progress — PoesIA

## Phase status

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Scaffold: package layout, 5 -IA modules, docs, tests, git init | Complete |
| 1 | Real LLM generation loop, EufonIA sound analysis, theme/novelty scoring, Library persistence | Complete |
| 2 | GalerIA illustration backends, ArmonIA music backends, corpus/KenLM | Complete |
| 3A | MemorIA Graph RAG - storage decision (NetworkX), basic ingest/retrieve | Complete |
| 3B | EmbeddingClient Protocol + SentenceTransformerClient | Complete |
| 3C | Extended record types (Fragment, Seed, Influence), SeedExpander | Complete |
| 3D | BriefBuilder + GenerationBrief with to_prompt() | Complete |
| 3E | Integration: CandidateGenerator, ConstrainedLoop, CLI wiring | Complete |
| 4 | Phase 4A-D: Gemini/OpenAI, influence profiles, GalerIA style, auto-embed | Complete |
| 5 | P0+P1 hardening, Groq, directive prompts, RhymeTracker, interactive CLI | Complete |
| 6 / P2 | Typed graph nodes/relations, bounded expansion, explainable paths | NEXT |

## What is functional now (Phase 5 end state)

- Full end-to-end poem generation with real LLM (Groq llama-3.3-70b-versatile)
- Directive prompts: syllable target, rhyme word bank, anti-repetition, output-only rule
- RhymeTracker: per-letter-group commitments, Datamuse/CMUdict/ES-offline word banks
- ConstrainedLoop with LineSelector callback for human interactive selection
- poesia memoria list/search: real SQLite-backed library
- --show-retrieval, --interactive, --show-alternatives, --save all working
- 285 tests passing

## What is NOT implemented yet

- Typed graph nodes/relations (P2)
- Bounded graph traversal with explainable paths (P2)
- Dense vs graph comparison (P2 evidence gate)
- Embedding/index compatibility descriptor (P3)
- Multilingual evaluation corpus (P4)
- Provider controls: privacy, retry, cost (P5)
- romance form default line count (deferred, not on plan)
- Literary taxonomy auto-tagging (deferred)

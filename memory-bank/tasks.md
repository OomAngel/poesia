# Tasks — PoesIA (Kanban)

## IN PROGRESS

- [ ] **P3 source fingerprints**: hash ingested content to detect a stale index
  when source files change without an explicit rebuild call.

## BACKLOG

- [ ] P4: reviewed multilingual evaluation corpus (ES + EN minimum).
- [ ] P4: retrieval relevance evaluation on real fragments.
- [ ] P4: generation grounding evaluation (formal validity + context use).
- [ ] P5: explicit opt-in before personal context reaches a hosted provider.
- [ ] P5: provider/run lineage on every saved poem.
- [ ] Phase 4E: literary taxonomy auto-tagging.
- [ ] romance form: add default line count spec.

## BLOCKED

(None currently)

## DONE

All phases through P3-compatibility are complete (327 tests passing):
- Core phonology, evaluation, forms, generation loop.
- `eufonia`, `galeria`, `armonia` sub-brands.
- `memoria` Library (Markdown + SQLite), real CLI list/search.
- GraphRAGRetriever: typed nodes/edges, traverse(), retrieve_with_paths().
- BriefBuilder wired to retriever; GenerationBrief.graph_paths.
- e5 query/passage prefix fix across all callers.
- IndexCompatibilityError, check_index_compatibility(), rebuild(), index_info().
- Atomic JSON write; versioned persistence header with load-time enforcement.
- Groq/Gemini/OpenAI backends, RhymeTracker, directive prompts.
- --interactive, --show-retrieval (with graph paths), --show-alternatives.

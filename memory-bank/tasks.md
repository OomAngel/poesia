# Tasks — PoesIA (Kanban)

## IN PROGRESS

(None — all active phases complete)

## BACKLOG

- [x] romance form: add `--lines` CLI param for variable-length support
- [ ] Phase 4E: literary taxonomy auto-tagging (movement/era retrieval, brief context)
- [ ] Wire retrieval into GalerIA for illustration style anchoring
- [ ] WordNet Spanish (`omw-es:1.4`) — retry when server is up
- [ ] Exact syllable filtering for training data (500 structured sonetos avg 10.5 syll)
- [ ] Monitoring (when a deployed instance exists — not needed for local-only use)

## DONE

All phases P0–P5 complete (400+ tests passing):
- Core phonology, evaluation, forms, generation loop.
- `eufonia`, `galeria`, `armonia` sub-brands.
- `memoria` Library (Markdown + SQLite), real CLI list/search.
- GraphRAGRetriever: typed nodes/edges, traverse(), retrieve_with_paths().
- BriefBuilder wired to retriever; GenerationBrief.graph_paths.
- e5 query/passage prefix fix across all callers.
- IndexCompatibilityError, check_index_compatibility(), rebuild(), index_info().
- Atomic JSON write; versioned persistence header with load-time enforcement.
- P3 source fingerprints: _compute_fingerprint(), is_stale(), content_fingerprint in JSON header, CLI stale-index warning.
- Groq/Gemini/OpenAI backends, RhymeTracker, directive prompts.
- --interactive, --show-retrieval (with graph paths), --show-alternatives.
- P4: end-word anti-repetition penalty (end_word_penalty).
- P4: fragment fidelity scoring signal.
- P4: Groq 429 rate-limit retry with back-off.
- P4: fragment frontmatter parsing + CLI ingest-all command.
- P4: 13 English fragments (multilingual corpus, ES+EN).
- P4: _parse_yaml_list fix (block list fallthrough).
- P4: evaluation corpus verification tests.
- P4: embedding profile frozen to intfloat/multilingual-e5-small.
- P4: retrieval relevance tests (self-retrieval, cross-lingual, graph paths, language filter).
- P4: generation grounding tests (brief building, formal validity, scoring signals).
- P5: privacy confirmation before personal context reaches a hosted LLM.
- P5: --yes flag to skip privacy prompt.
- P5: provider/run lineage in saved frontmatter (provider, n_candidates, latency, temperature, total_tokens).
- P5: structured exception hierarchy (PoesiaError, 10 subtypes).
- P5: LLMUsage tracking (prompt_tokens, completion_tokens, latency_ms).
- P5: OllamaClient for local/offline LLM generation.

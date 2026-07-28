# PoesIA RAG, GraphRAG, and LLM Engineering Hardening Plan

Doc class: canonical implementation authority for RAG/LLM work  
Status: active  
Last updated: 2026-07-28 (P0–P5 complete — all hardening phases done)  
Scope: `memoria/`, embedding-backed evaluation, retrieval-informed generation,
hosted LLM integration, and their CLI paths

This document is the sequencing and completion authority for RAG, GraphRAG,
embeddings, and LLM lifecycle work. A phase must not be called complete because
files exist or an aggregate test count passes; it requires the stated acceptance
evidence.

---

## Current state

**P0–P5 are complete.** 400+ tests passing.

### What is implemented and verified

- Provider-neutral `LLMClient` protocol; Gemini, OpenAI, and Groq backends.
- Deterministic generate → validate → score → rank → repair loop.
- `RhymeTracker`: per-line commitment with Datamuse/CMUdict/offline word bank.
- Directive prompts: syllable target, rhyme word bank, anti-repetition per line.
- `embed_one()` / `embed()` contract enforced; `text_type="passage"|"query"` on
  all callers so e5 models get the correct prefix for stored docs vs queries.
- Embedding validation at all boundaries (rank, dimension, numeric, finite).
- `NodeType` / `RelationType` typed graph schema (poem, fragment, influence,
  seed, theme; similar_to, inspired_by, explores, contains).
- `GraphHop` + `GraphPath` with `to_display_string()` for explainable paths:
  `pattern-finder -[similar_to 0.82]-> hound -[inspired_by]-> Garcia Lorca`
- `traverse()`: bounded BFS with max_hops, budget, typed edge/node filters.
- `retrieve_with_paths()`: dense seeds + graph expansion, returns
  `(node_id, score, GraphPath|None)` triples.
- `BriefBuilder.build()` calls `retriever.retrieve_with_paths()` when wired;
  `GenerationBrief.graph_paths` carries the result.
- `--show-retrieval` displays typed hop chains in the CLI.
- `IndexCompatibilityError`: raised when an embedding client mismatches the
  loaded index model_id or dimension — prevents silent corruption on model swap.
- `rebuild(records, client)`: wipes graph and re-ingests under new model identity.
- `index_info()`: returns schema_version, model_id, dimension, node/edge counts.
- Atomic JSON write (temp → `os.replace`) — no partial writes on crash.
- Versioned `graphrag.json` header: schema_version, model_id, embedding_dimension
  restored on load and checked against active client.
- Source fingerprints: `_compute_fingerprint()` + `is_stale()` detect stale indices.
- Markdown/SQLite `Library` with real `list`/`search` CLI.
- `--interactive` human line-by-line selection with typed-own-line support.
- Multilingual evaluation corpus (13 ES + 13 EN fragments).
- Retrieval relevance evaluation: self-retrieval, cross-lingual, graph paths.
- Generation grounding evaluation: formal validity, fragment fidelity scoring.
- Embedding profile frozen to `intfloat/multilingual-e5-small` after comparative eval.
- OllamaClient: local/offline LLM backend (gemma2:2b default, configurable).
- Privacy confirmation before personal context reaches a hosted provider.
- Provider/run lineage in saved poem frontmatter (provider, n_candidates, temperature, latency_ms, total_tokens).
- Structured exception hierarchy: ``PoesiaError`` base with 10 subtypes.
- ``LLMUsage`` dataclass with token and latency tracking.
- 400+ tests passing.

### Honest positioning

> PoesIA is a hybrid deterministic/LLM poetry system with verified dense
> personal-context retrieval, typed semantic graph traversal with explainable
> paths, a complete end-to-end generation+selection+save journey, immutable
> index compatibility enforcement, source fingerprinting for stale-index
> detection, a frozen multilingual embedding profile (e5-small, 384d),
> a reviewed evaluation corpus (ES+EN), privacy controls, provider/run
> lineage, structured error handling, and an OllamaClient for local/offline
> generation. It meets all definition-of-done criteria for an integrated
> GraphRAG generation system.

---

## Implementation sequence

### P0 — Restore semantic correctness ✅

Scalar/batch embedding contract enforced. Embedding validation at all
boundaries. Silent semantic failures removed.

### P1 — Complete one end-to-end RAG journey ✅

Library wired to CLI. Library poems convertible to retrieval context.
Generate → validate → present → save with provenance.

### P2 — Make graph structure materially useful ✅

Typed nodes/edges. Bounded traversal with explainable paths.
`retrieve_with_paths()`. BriefBuilder wired to retriever.
Evidence gate: `test_dense_vs_graph_retrieval_differ()` proves graph
reaches nodes unreachable by dense-only retrieval.
E5 query/passage prefix fixed across all callers.

### P3 — Make artifacts reproducible ✅

1. ✅ Immutable index compatibility: `IndexCompatibilityError`, `check_index_compatibility()`,
   `rebuild()`, `index_info()`. Compatibility enforced in `ingest()`,
   `add_fragment_node()`, `add_influence_node()`.
2. ✅ Atomic write: `_save()` writes to `.tmp` then `os.replace()`.
3. ✅ Versioned header: schema_version, model_id, embedding_dimension
   in JSON; restored and enforced on load.
4. ✅ Source fingerprints: `_compute_fingerprint()` hashes ingested content;
   `is_stale(records)` detects when source files changed without a full rebuild;
   `content_fingerprint` in JSON header; CLI stale-index warning.

### P4 — Establish evaluation ✅

1. ✅ Multilingual evaluation corpus (13 ES + 13 EN fragments).
2. ✅ Retrieval relevance eval: self-retrieval MRR@5, cross-lingual, graph paths.
3. ✅ Generation grounding eval: formal validity, fragment fidelity scoring signal.
4. ✅ Embedding profile frozen to `intfloat/multilingual-e5-small` after comparative
   evaluation of 3 candidate models (e5-base, e5-small, all-MiniLM-L6-v2).

### P5 — Provider and operational controls ✅

1. ✅ Explicit opt-in before personal context reaches a hosted provider:
   privacy notice with fragment listing, --yes flag to suppress.
2. ✅ Provider/run lineage stored alongside every saved poem:
   PoemProvenance extended with provider, n_candidates, temperature, latency_ms.
   All fields written to markdown frontmatter on --save.
3. ✅ Structured failure types: ``PoesiaError`` hierarchy (10 types), dual-inheritance
   for legacy compatibility, ``LLMProviderError`` with structured attributes,
   ``LLMUsage`` dataclass with token/count/latency tracking from provider responses.
4. ✅ (Deferred) Monitoring when a deployed instance exists — not needed for local-only use.

### P5 supplement — OllamaClient (local inference)

1. ✅ ``OllamaClient`` implements ``LLMClient`` Protocol via Ollama REST API.
2. ✅ Default model: ``gemma2:2b`` (~1.5 GB download, ~3 GB RAM).
3. ✅ Configurable via ``OLLAMA_MODEL`` and ``OLLAMA_HOST`` env vars.
4. ✅ Wired into CLI as ``--llm ollama`` (no privacy prompt since local).
5. ✅ ``LLMUsage`` tracking for latency and token estimates.

## Definition of done

PoesIA may claim an integrated GraphRAG generation system when:

- an exact corpus version is ingested with a verified compatible embedding profile;
- retrieval returns relevant records plus explainable graph paths;
- the graph materially affects selected generation context (evidence on record);
- context is visible in the generation brief;
- candidates are validated and presented for human choice;
- accepted output preserves source/model/configuration provenance;
- dense-only and graph-enhanced retrieval have been compared on reviewed examples;
- private context cannot reach a hosted provider without an explicit decision;
- failures are visible rather than silently converted into success;
- the CLI executes the complete user journey end to end.

# PoesIA RAG, GraphRAG, and LLM Engineering Hardening Plan

Doc class: canonical implementation authority for RAG/LLM work  
Status: active  
Last updated: 2026-07-27 (P3 compatibility check complete)  
Scope: `memoria/`, embedding-backed evaluation, retrieval-informed generation,
hosted LLM integration, and their CLI paths

This document is the sequencing and completion authority for RAG, GraphRAG,
embeddings, and LLM lifecycle work. A phase must not be called complete because
files exist or an aggregate test count passes; it requires the stated acceptance
evidence.

---

## Current state

**P0, P1, P2, and P3-compatibility are complete.** 327 tests passing.

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
- Markdown/SQLite `Library` with real `list`/`search` CLI.
- `--interactive` human line-by-line selection with typed-own-line support.
- 327 tests passing.

### Honest positioning

> PoesIA is a hybrid deterministic/LLM poetry system with verified dense
> personal-context retrieval, typed semantic graph traversal with explainable
> paths, a complete end-to-end generation+selection+save journey, and immutable
> index compatibility enforcement. It is not yet a production GraphRAG system
> (no evaluated multilingual corpus, no provider privacy controls).

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

### P3 — Make artifacts reproducible ← CURRENT (compatibility check done)

1. ✅ Immutable index compatibility: `IndexCompatibilityError`, `check_index_compatibility()`,
   `rebuild()`, `index_info()`. Compatibility enforced in `ingest()`,
   `add_fragment_node()`, `add_influence_node()`.
2. ✅ Atomic write: `_save()` writes to `.tmp` then `os.replace()`.
3. ✅ Versioned header: schema_version, model_id, embedding_dimension
   in JSON; restored and enforced on load.
4. ☐ Source fingerprints: hash ingested content to detect stale index
   when source files change without a full rebuild.

P3 is considered complete when source fingerprinting lands. That is the
only remaining item.

### P4 — Establish evaluation

1. Build a reviewed multilingual corpus (ES + EN minimum).
2. Evaluate retrieval: relevance of returned fragments and graph paths.
3. Evaluate generation: formal validity + contextual grounding.
4. Freeze an embedding profile only after comparative evidence.

### P5 — Provider and operational controls

1. Explicit opt-in before personal context reaches a hosted provider.
2. Provider/run lineage stored alongside every saved poem.
3. Retry, structured failure, latency, token, and cost metadata.
4. Monitoring only when a deployed instance exists.

---

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

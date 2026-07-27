# Active Context — PoesIA

_Last updated: 2026-07-27 — End of session. P0 + P1 + P2 complete. Next: P3._

---

## Instant re-entry checklist

```bash
cd /home/angel/dev/poesia
conda activate poesia
python -m pytest tests/ --tb=no -q   # should say 313 passed
export GROQ_API_KEY=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
```

Quick sanity test:
```bash
poesia write --theme "luna sobre el mar" --form haiku --language es --llm groq --n-candidates 3
```

---

## What was completed this session (Phase P2)

| Sub-task | What shipped |
|---|---|
| E5 prefix fix | `SentenceTransformerClient.embed()` now accepts `text_type="query"|"passage"`. All callers (ingest, BriefBuilder) use `"passage"` for stored docs and `"query"` for queries. |
| Typed graph schema | `NodeType` and `RelationType` enums added to `records.py`. `ingest()` stores `node_type="poem"`. Semantic edges carry `relation_type="similar_to"`. |
| Typed node management | `add_fragment_node()`, `add_influence_node()`, `add_typed_edge()` in `GraphRAGRetriever`. |
| `GraphHop` + `GraphPath` | New dataclasses with `to_display_string()` for `X -[similar_to 0.82]-> Y` output. |
| `traverse()` | Bounded BFS with `max_hops`, `budget`, `relation_types`, `node_types` filters. Returns `list[GraphPath]`. |
| `retrieve_with_paths()` | Dense seeds + graph expansion; returns `(node_id, score, GraphPath|None)` triples. |
| BriefBuilder wired | `BriefBuilder.build()` calls `self._retriever.retrieve_with_paths()`. `GenerationBrief.graph_paths` carries result. |
| `--show-retrieval` extended | CLI shows graph paths with typed hop chains. |
| Versioned persistence | `graphrag.json` includes `schema_version`, `model_id`, `embedding_dimension` header. |
| P2 tests | 28 new tests in `tests/test_p2_graph_structure.py`. All 313 tests pass. |

313 tests passing.

---

## Key source files

- src/poesia/memoria/records.py — `NodeType`, `RelationType` enums
- src/poesia/memoria/graphrag.py — `GraphHop`, `GraphPath`, `traverse()`, `retrieve_with_paths()`, versioned persistence
- src/poesia/memoria/embeddings.py — `text_type` param on `embed()` / `embed_one()`
- src/poesia/generation/brief_builder.py — `GenerationBrief.graph_paths`, BriefBuilder calls retriever
- src/poesia/cli.py — `--show-retrieval` shows graph paths
- tests/test_p2_graph_structure.py — 28 P2 tests

---

## What to do next: P3 (Make artifacts reproducible)

Authority: docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md section 12, P3

1. Compatibility check on load: compare stored `model_id`/`embedding_dimension` with active client — warn and refuse on mismatch.
2. Source fingerprints: hash ingested content to detect stale indexes.
3. Atomic write: temp file → rename (prevent corruption on crash).
4. Explicit `rebuild()` method.

Key files: src/poesia/memoria/graphrag.py

Do NOT start P4/P5 before P3.

---

## Known rough edges (not bugs)

- Groq soneto sometimes repeats: use --n-candidates 5+ for variety
- Metre not always exact: repair loop helps; phoneme constraints are P3+
- romance form has no default line count: deferred
- E5 query/passage quality improvement only visible with real sentence-transformers

---

## Document authority map

- What to build next: docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md section 12
- Phase history: docs/ROADMAP.md
- Kanban: memory-bank/tasks.md

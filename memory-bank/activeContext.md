# Active Context — PoesIA

_Last updated: 2026-07-27_

---

## Re-entry checklist

```bash
cd /home/angel/dev/poesia
conda activate poesia
python -m pytest tests/ --tb=no -q   # 327 passed
export GROQ_API_KEY=***REMOVED***
```

Quick sanity:
```bash
poesia write --theme "luna sobre el mar" --form haiku --language es --llm groq --n-candidates 3
```

---

## Current focus: finish P3 — source fingerprints

One item remains in P3 before moving to P4:

**Source fingerprints** — hash the ingested content so the index can detect
when source files have changed without a rebuild. Currently there is no way
to tell if `graphrag.json` is stale relative to the library it was built from.

Approach:
- Add a `content_fingerprint` field to the JSON header: a deterministic hash
  over the set of (record.id, embeddable_text) pairs ingested.
- Expose `is_stale(records)` on `GraphRAGRetriever`: returns `True` if the
  current records produce a different fingerprint than the stored one.
- Print a warning in the CLI when the index appears stale.
- Tests: fingerprint changes when records change; is stable on re-ingest of
  the same records; matches across save/load round-trips.

Key file: `src/poesia/memoria/graphrag.py`

---

## Key source files

| File | Responsibility |
|---|---|
| `src/poesia/memoria/graphrag.py` | GraphRAGRetriever: ingest, traverse, retrieve_with_paths, compatibility, rebuild, atomic save |
| `src/poesia/memoria/records.py` | NodeType, RelationType, FragmentRecord, InfluenceRecord, SeedRecord |
| `src/poesia/memoria/embeddings.py` | EmbeddingClient protocol, StubEmbeddingClient, SentenceTransformerClient (text_type) |
| `src/poesia/generation/brief_builder.py` | GenerationBrief (graph_paths), BriefBuilder wired to retriever |
| `src/poesia/cli.py` | --brief, --show-retrieval (graph paths), --interactive, --save |
| `src/poesia/memoria/library.py` | Markdown + SQLite poem library |

---

## Known rough edges

- Groq soneto sometimes repeats: use `--n-candidates 5+` for variety.
- Metre not always exact: repair loop helps; phoneme-level scan is P4+.
- `romance` form has no default line count — deferred.
- e5 query/passage quality difference only visible with real sentence-transformers.

---

## Document authority

| What | Where |
|---|---|
| RAG/LLM sequencing and DoD | `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` |
| Feature roadmap | `docs/ROADMAP.md` |
| Kanban | `memory-bank/tasks.md` |
| CLI usage | `USAGE_GUIDE.md` |
| Architecture rules | `docs/ARCHITECTURE.md` |

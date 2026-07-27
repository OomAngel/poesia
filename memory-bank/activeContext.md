# Active Context — PoesIA

_Last updated: 2026-07-27 (P3 source fingerprints DONE)_

---

## Re-entry checklist

```bash
cd /home/angel/dev/poesia
conda activate poesia
python -m pytest tests/ --tb=no -q   # 327 passed
export GROQ_API_KEY=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
```

Quick sanity:
```bash
poesia write --theme "luna sobre el mar" --form haiku --language es --llm groq --n-candidates 3
```

---

## Current focus: P4 — evaluation corpus & retrieval relevance

P3 is fully complete (350 tests passing). Moving to P4:

- [ ] P4: reviewed multilingual evaluation corpus (ES + EN minimum).
- [ ] P4: retrieval relevance evaluation on real fragments.
- [ ] P4: generation grounding evaluation (formal validity + context use).

Key files remain the same as P3.

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

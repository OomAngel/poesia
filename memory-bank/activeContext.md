# Active Context — PoesIA

_Last updated: 2026-07-28 (P4 complete — embedding profile frozen)_

---

## Re-entry checklist

```bash
cd /home/angel/dev/poesia
conda activate poesia
python -m pytest tests/ --tb=no -q   # 387 passed
export GROQ_API_KEY=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
```

Quick sanity:
```bash
poesia write --theme "luna sobre el mar" --form haiku --language es --llm groq --n-candidates 3
```

---

## Current focus: P5 — monitoring (deferred) / Ollama integration complete

P5 items 1-2 complete (privacy + lineage). Remaining:
- [x] Multilingual evaluation corpus (13 ES + 13 EN)
- [x] Retrieval relevance tests (self-retrieval, cross-lingual, graph paths)
- [x] Generation grounding tests (formal validity, scoring signals)
- [x] Embedding profile frozen to intfloat/multilingual-e5-small
- [x] P5.1: privacy confirmation with --yes skip
- [x] P5.2: provider/run lineage in saved frontmatter
- [x] P5.3: structured failure types, token/cost capture
- [x] OllamaClient: local LLM backend for offline generation

### Key files

| File | Responsibility |
|---|---|
| `tests/test_p4_evaluation_corpus.py` | Multilingual corpus verification (ES + EN >=10 each, frontmatter, shared themes) |
| `tests/test_p4_retrieval_relevance.py` | Self-retrieval, cross-lingual, graph paths, language filtering |
| `tests/test_p4_generation_grounding.py` | Brief building, formal validity, fragment fidelity scoring |
| `seeds/angel_fragments/14-26_*.md` | 13 English fragments thematically paired with existing ES |

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

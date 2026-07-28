# Embedding Profile — Frozen

**Status:** Frozen (2026-07-28)
**Model:** `intfloat/multilingual-e5-small`
**Dimension:** 384
**Previous default:** `intfloat/multilingual-e5-base` (768d)

---

## Rationale

Three candidate models were evaluated on the 26-fragment multilingual corpus
(13 ES + 13 EN):

| Model | Dim | MRR@5 | XL-MRR@5 | Cold(ms) | ms/frag | Index(KB) |
|-------|-----|-------|----------|----------|---------|-----------|
| intfloat/multilingual-e5-base | 768 | 1.0000 | 1.0000 | 5196 | 9.7 | 78.0 |
| intfloat/multilingual-e5-small | 384 | 1.0000 | 1.0000 | 5805 | 12.9 | 39.0 |
| sentence-transformers/all-MiniLM-L6-v2 | 384 | 1.0000 | 1.0000 | 2748 | 10.4 | 39.0 |

All three models achieved perfect self-retrieval and cross-lingual MRR@5 on
the current corpus of 26 distinct fragments.

**Decision:** `intfloat/multilingual-e5-small` was chosen because:

1. **Multilingual** (100+ languages) — essential for ES+EN poetry retrieval.
2. **384-dimension** — half the index size and faster retrieval than e5-base.
3. **Smaller download** (~290 MB vs ~560 MB for e5-base).
4. **Same retrieval quality** as e5-base on the current corpus.
5. The slight cold-start penalty (5.8s vs 5.2s) is a one-time cost.
6. The slight per-fragment speed difference (12.9ms vs 9.7ms) is negligible
   at our scale (26 fragments, bounded by LLM generation time).

## When to re-evaluate

Re-evaluate the embedding profile when:

- The corpus exceeds 500 fragments.
- A new multilingual embedding model (bge-m3, e5-large, etc.) is proven to
  improve cross-lingual MRR on a held-out poetry retrieval task.
- The storage format changes from JSON pickled vectors to a vector database.

## Migration

Changing the default model triggers `IndexCompatibilityError` on existing
indices. To migrate:

```bash
poesia memoria ingest-all
```

This rebuilds the index under the new model identity.

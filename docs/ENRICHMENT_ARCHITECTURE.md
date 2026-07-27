# Pre-Generation Enrichment Architecture

_Created: 2026-07-27 — extends `ARCHITECTURE.md` with the personal context layer._

## Vision Shift

The original architecture positioned PoesIA as primarily a **post-generation validator**:

```
LLM generates → PoesIA validates → Human selects
```

This document describes the expanded vision: PoesIA as a **pre-generation enrichment engine** that also validates:

```
Your inputs → PoesIA enriches → LLM generates (one dense call) → PoesIA validates → Human selects
```

The key insight: **front-load context to minimize LLM calls**.

## The Full Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: YOUR RAW INPUTS                                                   │
│  • Personal background docs (feelings, life moments, influences)            │
│  • Central topic/theme for this piece                                       │
│  • Specific verses, words, images in mind                                   │
│  • Desired tone/mood, desired form/metre                                    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: PRE-GENERATION ENRICHMENT (PoesIA, local, free/cheap)             │
│  MemorIA: Embed inputs → retrieve personal fragments + exemplar lines      │
│  Phonology: Expand word seeds → rhymes, synonyms, semantic neighbors        │
│  Brief Assembly: Structure all constraints into a "generation brief"        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: LLM GENERATION (one well-grounded call)                           │
│  Receives structured brief, not vague prompt. Your voice stays central.    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 4: POST-VALIDATION (PoesIA, local, free)                             │
│  Metre/rhyme/form compliance. Maybe one targeted repair call if needed.    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 5: HUMAN DECISION — Taste, final selection.                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## MemorIA Extended: The Personal Context Corpus

The Graph RAG layer is no longer just "exemplar poems." It's your **personal context corpus**:

### Node Types

| Type | Content | Source |
|------|---------|--------|
| `poem` | Your finished poems | Existing MemorIA library |
| `fragment` | Life moments, feelings, emotional states | Personal docs, journals |
| `seed` | Word/image/verse seeds collected | Explicit ingestion or session capture |
| `theme` | Recurring themes across your writing | Auto-extracted or manually tagged |
| `influence` | Poets/works that resonate with you | Explicit ingestion |

### Edge Types

| Edge | Meaning |
|------|---------|
| `similar_to` | Semantic similarity (cosine ≥ threshold) |
| `inspired_by` | Poem ← Influence relationship |
| `explores` | Poem/fragment → Theme relationship |
| `contains` | Poem → Seed (word/image used) |

### Retrieval Modes

1. **Context grounding**: Given theme + tone, retrieve personal fragments
2. **Exemplar finding**: Given form + mood, retrieve your past poems as style anchors
3. **Word expansion**: Given seed words, retrieve semantic neighbors + rhyme options
4. **Influence surfacing**: Given theme, retrieve relevant influences

## Implementation Phases

### Phase 3A: Core Graph RAG ✅
- [x] `GraphRAGRetriever` core (NetworkX, JSON persistence)
- [x] `retrieve()` with cosine similarity scoring
- [x] `neighbourhood()` for graph traversal

### Phase 3B: Embedding Layer ✅
- [x] `EmbeddingClient` Protocol + `SentenceTransformerClient` (e5-base)
- [x] `StubEmbeddingClient` for deterministic testing
- [x] `get_embedding_client()` factory
- [ ] Auto-embed on ingest (pending Phase 3E)

### Phase 3C: Extended Node Types ✅
- [x] `FragmentRecord` dataclass (life moments, feelings)
- [x] `SeedRecord` + `SeedExpansion` (11 expansion dimensions)
- [x] `InfluenceRecord` dataclass (poets/works)
- [x] `SeedExpander` (WordNet + rhyme + semantic + Datamuse)
- [x] First 10 personal fragments in `seeds/angel_fragments/`
- [x] Influence registry (24 poets) in `docs/INFLUENCE_REGISTRY.md`

### Phase 3D: Brief Assembly ✅
- [x] `BriefBuilder` class — assembles generation brief
- [x] `GenerationBrief.to_prompt()` — renders as LLM prompt
- [x] Verbosity levels: minimal/standard/maximal
- [x] Fragment retrieval via semantic similarity
- [x] Influence matching by tone overlap

### Phase 3E: Integration (current)
- [ ] Wire brief into `CandidateGenerator`
- [ ] CLI: `poesia write --theme X --tone Y --seeds "a,b" --form soneto`
- [ ] CLI: `poesia memoria add-fragment|add-seed|add-influence`
- [ ] Auto-embed on `GraphRAGRetriever.ingest()`
- [ ] Wire retrieval into GalerIA for style anchoring

See `INGESTION_SCHEMA.md` for record formats and `GENERATION_BRIEF.md` for brief structure.

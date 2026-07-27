# Roadmap

## Phase 0 — Scaffold ✅

- [x] Package layout: `phonology/`, `generation/`, `evaluation/`, `forms/`
- [x] Spanish + English phonology interfaces (rantanplan/silabeador,
      pronouncing/prosodic), lazy-imported, stub-safe
- [x] `StubLLMClient` + `ConstrainedLoop` control-flow skeleton
- [x] Form registry: soneto, romance (ES), Shakespearean sonnet, haiku (EN)
- [x] Four -IA feature modules scaffolded: `eufonia/`, `galeria/`, `memoria/`, `armonia/`
- [x] CLI wired: `poesia write|scan|eufonia|galeria|memoria|armonia`
- [x] Unit tests for phonology base types + form registry
- [x] `git init` + first local commit

## Phase 1 — Real generation loop ✅

- [x] `HostedLLMClient` (Gemini & OpenAI REST APIs)
- [x] `sentence-transformers` for `theme_score` / `novelty_score`
- [x] `EufonyAnalyzer.analyze` (rhyme scheme detection)
- [x] `MemorIA.Library` persisted to disk (Markdown + SQLite index)

## Phase 2 — Illustration, music, stylistic grounding ✅

- [x] `GalerIA`: `HostedImageBackend` (DALL-E 3 & Replicate SDXL)
- [x] `AucaComposer.compose_panel` / `compose_sheet` via Pillow
- [x] `ArmonIA`: `MidiScoreBackend` (pure Python prosodic MIDI)
- [x] `EspeakRecitationBackend` for TTS
- [x] `SpanishPhonology.rhyme_key` & `classify_stanza`

## Phase 3 — Graph RAG + Pre-Generation Enrichment (current)

### 3A: Core Graph RAG ✅
- [x] Storage backend decision: NetworkX (JSON persistence)
- [x] `GraphRAGRetriever.ingest` / `.retrieve` in `memoria/graphrag.py`

### 3B: Embedding Layer ✅
- [x] `EmbeddingClient` Protocol + `SentenceTransformerClient` (`e5-base`)
- [x] `StubEmbeddingClient` for testing (deterministic)
- [x] `get_embedding_client()` factory
- [ ] Auto-embed on ingest (wiring pending)

### 3C: Extended Node Types ✅ (see `INGESTION_SCHEMA.md`)
- [x] `FragmentRecord` — life moments, feelings, emotional states
- [x] `SeedRecord` + `SeedExpansion` — word/image clusters with 11 expansion dimensions
- [x] `InfluenceRecord` — poets/works that resonate
- [x] `SeedExpander` — WordNet + rhyme + semantic + Datamuse expansion
- [x] First 10 personal fragments in `seeds/angel_fragments/`
- [x] Influence registry (24 poets) in `docs/INFLUENCE_REGISTRY.md`
- [ ] Ingestion CLI: `poesia memoria add-fragment|add-seed|add-influence`

### 3D: Pre-Generation Enrichment ✅ (see `ENRICHMENT_ARCHITECTURE.md`)
- [x] `BriefBuilder` class — assembles generation brief from:
  - Form spec + tone/theme inputs
  - Retrieved fragments (semantic similarity)
  - Expanded seeds (rhymes, synonyms via WordNet/datamuse)
  - Influence anchors (matched by tone)
- [x] `GenerationBrief.to_prompt()` — renders brief as LLM prompt
- [x] Verbosity levels: minimal/standard/maximal

### 3E: Integration
- [ ] Wire brief into `CandidateGenerator`
- [ ] CLI: `poesia write --theme X --tone Y --seeds "a,b" --form soneto`
- [ ] Wire retrieval into `GalerIA` for illustration style anchoring

## Workflow Model

After Phase 3, the primary workflow becomes:

```
Your inputs → PoesIA enriches → LLM (one dense call) → PoesIA validates → You select
```

PoesIA front-loads context to minimize LLM calls and keep your voice central.
See `ENRICHMENT_ARCHITECTURE.md` for the full design.

## Explicit non-goals for now

- No web frontend until concrete need emerges — Python-only
- No C++ code — `llama.cpp`, eSpeak NG, OpenFst only if scale demands
- No neo4j — NetworkX + JSON sufficient for personal corpus size

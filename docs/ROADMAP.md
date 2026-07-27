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

### 3E: Integration ✅
- [x] Wire brief into `CandidateGenerator` (optional `brief` parameter)
- [x] Wire `BriefBuilder` into `ConstrainedLoop` (new constructor + run params)
- [x] CLI: `poesia write --theme X --tone Y --seeds "a,b" --brief-level standard --brief`
- [x] CLI: `poesia memoria add-fragment|add-seed|add-influence|list-fragments|list-influences`
- [x] Integration tests in `tests/test_integration_phase3e.py`
- [ ] Wire retrieval into `GalerIA` for illustration style anchoring (deferred to Phase 4)

## Workflow Model

After Phase 3, the primary workflow becomes:

```
Your inputs → PoesIA enriches → LLM (one dense call) → PoesIA validates → You select
```

PoesIA front-loads context to minimize LLM calls and keep your voice central.
See `ENRICHMENT_ARCHITECTURE.md` for the full design.

## Phase 4 — Polish & Real Generation ✅

### 4A: Real LLM Integration ✅
- [x] Wire `HostedLLMClient` to actual Gemini/OpenAI APIs
- [x] CLI `--llm gemini|openai|stub|auto` option
- [x] Environment variable config for API keys (GEMINI_API_KEY, OPENAI_API_KEY)
- [ ] End-to-end poem generation test (requires API key)

### 4B: Richer Influence Profiles ✅
- [x] `InfluenceRecord` already has movement, era, tone, forms, exemplars, resonance_notes
- [x] Parse full profiles from INFLUENCE_REGISTRY.md (movement, era, tone, exemplars)
- [x] Correct language detection from section headers (es/en/nl)
- [x] Clean markdown formatting (strip `**` markers)

### 4C: GalerIA Style Anchoring ✅
- [x] `style_anchoring.py` with movement→visual style mapping
- [x] `style_from_influences()` derives visual keywords from influences
- [x] CLI `galeria illustrate --style-from-influences --tone <tones>`

### 4D: Auto-embed on Ingest ✅
- [x] `GraphRAGRetriever.ingest()` accepts optional `embedding_client`
- [x] Auto-compute embeddings for records missing from embeddings dict
- [x] Semantic edges rebuilt automatically

### 4E: Literary Taxonomy Integration (deferred)
- [ ] Auto-tag influences by movement from taxonomy
- [ ] Retrieval by movement/era
- [ ] Brief includes movement context

## Phase 5 — Generation Quality + P0/P1 Hardening ✅ (2026-07-27)

### 5A: Real LLM provider — Groq ✅
- [x] `HostedLLMClient` Groq backend (`https://api.groq.com/openai/v1`, `GROQ_API_KEY`)
- [x] Default model `llama-3.3-70b-versatile`; auto-detection priority Gemini → Groq → OpenAI
- [x] Groq n>1 handled via sequential calls (Groq API does not support `n>1`)
- [x] `User-Agent: poesia/1.0` header (Cloudflare blocks Python-urllib default)
- [x] 2.1s inter-call delay for free-tier 30 RPM limit
- [x] `--llm groq` in CLI; 11 mock-based tests
- [x] Live end-to-end confirmed: haiku + soneto with `llama-3.3-70b-versatile`

### 5B: Directive prompts ✅
- [x] Prompt specifies exact syllable target per line
- [x] Numbered prior-lines block (1. / 2. / …) for clear context
- [x] Line number in task instruction ("Write line 3.")
- [x] "Output ONLY the single bare poetry line" output rule
- [x] Anti-repetition: "Do NOT begin the line with the same word as any prior line"

### 5C: Rhyme tracking + word banks ✅
- [x] `RhymeTracker` — maps form rhyme scheme to per-line commitments
- [x] Commits first rhyme key per letter group; tracks example word
- [x] `RhymeFetcher` — retrieves rhyming word candidates:
  - English: `pronouncing`/CMUdict (offline) → Datamuse `rel_rhy` (online)
  - Spanish: Datamuse → offline suffix match against ~200 frequency words
  - Correct paroxytone/oxytone stress rules for Spanish suffix extraction
- [x] Prompt rhyme instruction includes word bank: "Word bank: amor, calor, temblor, …"
- [x] "Use a DIFFERENT word, not X itself" constraint in prompt
- [x] 17 + 18 new tests (rhyme_fetcher + rhyme_tracker)

### 5D: P1 complete — end-to-end RAG journey ✅
- [x] `poesia memoria list` — real Library, `--form`/`--language`/`--limit` filters
- [x] `poesia memoria search` — SQLite substring match, real results
- [x] `--show-retrieval` — prints retrieved fragments + similarity scores + influences
- [x] `--interactive` — human picks each line from numbered scored candidates;
  supports Enter (top), number (choice), `t` (type own line); custom line rescanned
- [x] `LineSelector` callback type in `ConstrainedLoop.run()`
- [x] 9 new P1 tests

**Total tests after Phase 5: 285**

## Phase 6 — Next (P2: Graph structure)

- [ ] Typed graph nodes and relations (poem→influence `inspired_by`, poem→theme `explores`, etc.)
- [ ] Bounded graph expansion with explainable paths
- [ ] `--show-retrieval` extended to show graph path, not just cosine score
- [ ] Compare dense-only vs graph-enhanced context on same prompt

## Explicit non-goals for now

- No web frontend until concrete need emerges — Python-only
- No C++ code — `llama.cpp`, eSpeak NG, OpenFst only if scale demands
- No neo4j — NetworkX + JSON sufficient for personal corpus size

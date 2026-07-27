# Active Context — PoesIA

_Last updated: 2026-07-27 — Load-bearing gaps fixed._

## What We Just Did

### Session 2026-07-27 (Load-Bearing Gap Fixes)

**Fixed the two critical gaps that undercut the project's core claims:**

1. **Gap 1: Scorer now uses real semantic scoring**
   - `LineScorer` accepts `embedding_client` and `theme_text`
   - Computes `theme_score` (cosine similarity to theme)
   - Computes `novelty_score` (1 - max similarity to prior lines)
   - Applies `cliche_penalty` (Spanish/English cliché lists)
   - `ConstrainedLoop` passes embedding client to scorer

2. **Gap 2: Spanish sinalefa (vowel elision) now handled**
   - `_count_sinalefas()` detects cross-word vowel merging
   - `_final_stress_adjustment()` handles aguda/llana/esdrújula
   - **Verified**: "En tanto que de rosa y de azucena" → 11 syllables ✅
   - **Verified**: "Caminante no hay camino" → 8 syllables ✅

3. **Gap 3: CLI `--brief` tries real embeddings first**
   - Uses `get_embedding_client()` (sentence-transformers)
   - Falls back to stub only on exception
   - Shows informative message about which client is used

**Tests**: 128 passing (22 new tests for sinalefa + scorer)

### Earlier: Phase 4 Complete

### Session 2026-07-27 (Phase 3E Integration)

1. **CandidateGenerator extended** — Now accepts optional `brief: GenerationBrief` parameter
   - Uses `brief.to_prompt()` for rich prompts when brief is provided
   - Falls back to simple theme-based prompt for legacy compatibility

2. **ConstrainedLoop extended** — Full BriefBuilder integration
   - New constructor params: `brief_builder`, `embedding_client`, `fragments`, `influences`
   - New `run()` params: `tone`, `seeds`, `brief_level`
   - Builds brief automatically when builder is provided
   - `LoopResult` now includes the `brief` used for inspection

3. **CLI `write` command updated** — New options:
   - `--tone <comma-separated>` — Tone descriptors for influence matching
   - `--seeds <comma-separated>` — Seed words to expand
   - `--brief-level` — minimal/standard/maximal verbosity
   - `--brief` — Enable BriefBuilder (loads fragments + influences)

4. **CLI `memoria` ingestion commands added**:
   - `poesia memoria add-fragment <path>` — Add personal fragments
   - `poesia memoria add-seed <word>` — Expand seed with rhymes/synonyms
   - `poesia memoria add-influence <name> --tone <tones>` — Add influences
   - `poesia memoria list-fragments` — List all personal fragments
   - `poesia memoria list-influences` — List all influences

5. **Integration tests** — 7 new tests in `test_integration_phase3e.py`

**Tests**: 95 passing

## Current Focus

**Phase 3E: Complete** — All integration gaps addressed.

### What's Done

| Gap | Status |
|-----|--------|
| `CandidateGenerator` accepts `GenerationBrief` | ✅ |
| `ConstrainedLoop` uses BriefBuilder | ✅ |
| CLI `write` has `--tone/--seeds/--brief-level` | ✅ |
| CLI `memoria` has `add-fragment/add-seed/add-influence` | ✅ |

### Remaining (deferred to future phases)

| Gap | Notes |
|-----|-------|
| `GraphRAGRetriever` auto-embed on ingest | Future enhancement |
| GalerIA style anchoring from influences | Future Phase 4 |

## Next Steps

Phase 3 is complete. Next priorities:

1. **Test end-to-end with real LLM** — The brief integration is wired but StubLLMClient is still the default
2. **Improve influence parsing** — Current parser doesn't extract tone from INFLUENCE_REGISTRY.md
3. **Consider Phase 4** — Graph RAG enhancements, cross-language support

## Key Files

- `src/poesia/generation/candidate_generator.py` — ✅ Brief integration
- `src/poesia/generation/constrained_loop.py` — ✅ Brief wiring
- `src/poesia/cli.py` — ✅ New CLI options and commands
- `tests/test_integration_phase3e.py` — ✅ Integration tests



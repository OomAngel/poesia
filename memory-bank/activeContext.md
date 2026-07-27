# Active Context — PoesIA

_Last updated: 2026-07-27 — RAG/LLM hardening audit active._

## Current authority and correction

`docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` is the canonical implementation plan
for embeddings, RAG/GraphRAG, retrieval-informed generation, and hosted LLM lifecycle
work. Its audit supersedes earlier “complete” statements where those statements lack
the plan's acceptance evidence.

The most urgent open defect is the scalar/batch embedding mismatch in GraphRAG ingestion
and semantic scoring. The current graph and dense-fragment retrieval are also not yet one
integrated GraphRAG-to-generation journey. Do not describe either item as complete until
P0 and P1 of the hardening plan are satisfied.

## What We Just Did

### Session 2026-07-27 (Real Usage Testing - Found Critical Bugs)

**Tested actual poem generation** with `test_real_generation.py` and found:

1. ✅ **FIXED**: StubLLMClient was echoing full prompts instead of generating lines
   - Added Spanish/English templates for 5/7/11 syllables
   - Extracts theme word and infers target syllable count
   - Now generates plausible short poetic lines

2. 🔴 **ROOT CAUSE FOUND**: Metre scoring completely broken for haiku
   - Haiku has `syllables_per_line=0` (documented as "special-cased: 5-7-5")
   - **The special case is NOT implemented** anywhere in the code
   - ConstrainedLoop passes 0 to LineScorer → metre_score() returns 0.0 for all lines
   - **All haiku lines score 0.00 for metre, making metre constraint useless**
   - Fix required: ConstrainedLoop must track line position and pass 5/7/5 to scorer

3. Expected: Theme scoring is 0.00 without embedding client (by design)

4. Consequence: All candidates score identically (0.150) → random selection

**Created USAGE_ISSUES.md** to track all discovered problems with priority/status.

### Session 2026-07-27 (P0 RAG/LLM Hardening - Embedding Validation - Earlier)

**Completed P0 requirements from RAG/LLM hardening plan:**

1. ✅ **Embedding contract validation module** (`src/poesia/memoria/embedding_validation.py`)
   - `validate_embedding_vector()` — catches nested lists, NaN, inf, dimension mismatches
   - `validate_embedding_batch()` — validates batches with per-vector checks
   - `check_dimension_compatibility()` — ensures vectors can be compared
   - `EmbeddingValidationError` — explicit exception type for validation failures

2. ✅ **GraphRAGRetriever hardening** (`src/poesia/memoria/graphrag.py`)
   - Auto-embedding now validates vectors before storing
   - Pre-computed embeddings validated at ingest
   - Query embeddings validated at retrieval
   - Silent failures (`except: pass`) replaced with explicit errors
   - Critical P0 bug (scalar/batch confusion) would now be caught immediately

3. ✅ **LineScorer hardening** (`src/poesia/evaluation/scorer.py`)
   - Theme embedding validated at construction
   - Prior line embeddings validated before novelty scoring
   - Candidate embeddings validated during scoring
   - Silent failures replaced with explicit `ValueError`/`RuntimeError`

4. ✅ **Comprehensive test coverage** (26 new tests)
   - 19 validation tests (`test_embedding_validation.py`) — unit tests for validation logic
   - 7 P0 contract tests (`test_p0_embedding_contract.py`) — integration tests proving:
     * Malformed nested embeddings caught
     * Dimension mismatches caught
     * NaN/inf values caught
     * Invalid query embeddings caught
     * Auto-embedding failures exposed (not silenced)
     * Scorer validation at construction and scoring
     * Complete validation journey end-to-end

**Key improvement:** The critical P0 bug mentioned in the hardening plan (calling `embed(text)` 
instead of `embed_one(text)` which produces nested arrays) was already fixed in the code, but 
now we have **explicit validation** that would catch it immediately if reintroduced, plus all 
silent failures have been eliminated.

**Test status:** 213 passing (was 187)

### Session 2026-07-27 (Load-Bearing Gap Fixes - Earlier)

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

**RAG/LLM hardening P1:** complete the end-to-end journey with human-in-the-loop alternative selection.

### P1 Status Assessment (2026-07-27)

**What exists (partial P1):**
- ✅ Library loading (`--use-library` flag)
- ✅ Library poems converted to fragments for retrieval
- ✅ Retrieval context passed to ConstrainedLoop via BriefBuilder
- ✅ Generation brief built and used
- ✅ Provenance tracking and saving (`--save` flag)
- ✅ `LoopResult.scored_history` contains all alternatives per line

**What P1 requires but is missing:**
- ❌ Explicit retrieval visibility: show which context was retrieved
- ❌ Alternative presentation: display scored alternatives with breakdown
- ❌ Human selection: interactive choice among alternatives (not just auto-select best)
- ❌ Deliberate degraded mode: if embeddings fail, make it explicit, don't silent-fallback

**Next P1 steps:**
1. Add `--show-alternatives` flag to present top-N candidates per line with scores
2. Add `--interactive` flag for human line-by-line selection
3. Add `--show-retrieval` flag to display which fragments/poems were retrieved
4. Ensure degraded mode (no embeddings) is explicitly signaled, not silent

### Prior integration work that remains useful

| Gap | Status |
|-----|--------|
| `CandidateGenerator` accepts `GenerationBrief` | ✅ |
| `ConstrainedLoop` uses BriefBuilder | ✅ |
| CLI `write` has `--tone/--seeds/--brief-level` | ✅ |
| CLI `memoria` has `add-fragment/add-seed/add-influence` | ✅ |

### Current hardening priorities

| Priority | Required outcome |
|-----|-------|
| P0 | Correct scalar/batch embedding use, validate compatibility, expose failure, and prove semantic outcomes |
| P1 | Wire Library → ingestion → retrieval → brief → generation → human selection → provenance-preserving save |
| P2 | Make typed graph relations and bounded traversal materially affect generation context |

## Next Steps

Follow the ordered phases in `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md`. Do not move
directly to hosted-provider experimentation before local semantic correctness, the complete
user journey, and reviewed retrieval evaluation exist.

## Key Files

- `src/poesia/generation/candidate_generator.py` — ✅ Brief integration
- `src/poesia/generation/constrained_loop.py` — ✅ Brief wiring
- `src/poesia/cli.py` — ✅ New CLI options and commands
- `tests/test_integration_phase3e.py` — ✅ Integration tests


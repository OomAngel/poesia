# Usage Issues — PoesIA (2026-07-27, updated 2026-07-27)

All issues from initial real-generation testing. All resolved.

## 🔴 CRITICAL - Blocking Usage

### #1: Stub LLM returns full prompts, not poetic lines
**Status:** ✅ FIXED  
**Fix:** StubLLMClient now generates short plausible lines from templates keyed by syllable target and language. 5-syllable, 7-syllable, 10-syllable, 11-syllable templates for ES and EN.

---

## 🟡 HIGH - Scoring Broken

### #2: Metre scoring gives 0.00 for haiku (and returns 0.0 for all lines)
**Status:** ✅ FIXED  
**Impact:** Was blocking all metre-based selection for haiku  
**Evidence:** `test_real_generation.py` now shows varying metre scores (0.40, 0.71, 0.00)
**Root cause:** Haiku had `syllables_per_line=0` with no implementation of 5-7-5 pattern
**Fix applied:**
- Added `syllable_pattern: list[int]` to `FormSpec`
- Added `syllables_for_line(line_index)` method  
- Updated haiku to use `syllable_pattern=[5, 7, 5]`
- Modified `ConstrainedLoop` to create scorer per-line with correct target
- Added 5 new tests in `test_haiku_metre_scoring.py`
- All 218 tests pass

### #3: Theme scoring gives 0.00 (no embedding client)
**Status:** ✅ FIXED (explicit degraded mode)  
**Impact:** Was silent degradation, now explicit and clear  
**Evidence:** CLI now shows clear messaging about scoring mode
**Fix applied:**
- Added `semantic_mode_active` flag to track if embeddings loaded
- Enhanced messaging when sentence-transformers unavailable:
  - `⚠ Degraded mode: No sentence-transformers available`
  - Shows installation instructions: `pip install -e '.[nlp]'`
  - Displays error details
- Added scoring mode summary after generation:
  - Without embeddings: "Scoring mode: metre only (no semantic scoring)"
  - With embeddings: "Scoring mode: metre + theme + novelty"
- Green checkmark when semantic scoring enabled

### #4: Composite scores were nearly identical in degraded mode
**Status:** ✅ FIXED (weight normalization)  
**Impact:** Was poor differentiation in degraded mode, now excellent spread
**Evidence:** Scores now range from 0.333 to 0.810 instead of 0.150 to 0.364
**Root cause:** In degraded mode (no embeddings), only 45% of weight was used (metre 0.3 + novelty 0.15), leaving 55% unused (theme 0.25 + rhyme 0.2 + cliche 0.1)
**Fix applied:**
- Added `normalize_weights` parameter to `composite_score()` (default True)
- Automatically redistributes weights of inactive signals to active ones
- Example: with only metre+novelty active:
  - Old: metre=0.3, novelty=0.15 → scores 0.15-0.45
  - New: normalize to sum=1.0 → metre=0.667, novelty=0.333 → scores 0.0-1.0
- Added 6 comprehensive tests in `test_composite_score_normalization.py`
- Updated existing test to check both normalized and absolute modes
- All 224 tests pass

---

## 🟢 LOW - Future Enhancements

### #5: Need real LLM testing
**Status:** ✅ DONE — Groq Cloud wired (`--llm groq`, `GROQ_API_KEY`).  
Live tests confirmed: haiku and soneto end-to-end with `llama-3.3-70b-versatile`.

### #6: Alternative presentation in CLI
**Status:** ✅ FULLY DONE  
- `--show-alternatives N` — shows top-N scored candidates per line with colour-coded breakdowns
- `--interactive` — pauses per line, human picks by number or types own line
- `--show-retrieval` — shows which fragments/influences were retrieved before generation

---

## Resolution summary

| # | Issue | Status |
|---|-------|--------|
| 1 | Stub returns prompts | ✅ Fixed |
| 2 | Haiku metre scoring | ✅ Fixed |
| 3 | Silent degraded mode | ✅ Fixed |
| 4 | Identical scores in degraded mode | ✅ Fixed |
| 5 | Real LLM testing | ✅ Done (Groq) |
| 6 | Alternative presentation + interactive | ✅ Done |

This file is now historical. All issues resolved. See `docs/ROADMAP.md` for current state and `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` for next priorities (P2+).

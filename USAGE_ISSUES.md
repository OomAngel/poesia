# Usage Issues Found (2026-07-27)

Issues discovered from real generation testing with `test_real_generation.py`.

## 🔴 CRITICAL - Blocking Usage

### #1: Stub LLM returns full prompts, not poetic lines
**Status:** IN PROGRESS  
**Impact:** Can't test generation flow without real API  
**Found:** The stub client echoes the entire multi-line prompt (32 syllables) instead of generating short poetic lines (5-7 syllables for haiku)  
**Fix:** Make stub generate short, plausible Spanish/English lines based on theme

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
**Status:** Deferred (needs API key)  
**Impact:** Can't verify end-to-end generation quality  
**Action:** Get Gemini/OpenAI API key and test with `--llm gemini`

### #6: No alternative presentation in CLI
**Status:** P1 requirement  
**Impact:** User can't see or choose alternatives  
**Action:** Add `--show-alternatives` and `--interactive` flags

---

## Resolution Order

1. ✅ Fix stub client (#1) - DONE
2. ✅ Fix metre scoring (#2) - DONE  
3. ✅ Add explicit degraded mode (#3) - DONE
4. ✅ Fix composite score weighting (#4) - DONE
5. Test with real LLM (#5) - Deferred (needs API key)
6. Add alternative presentation (#6) - P1 (future work)

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
**Status:** ROOT CAUSE FOUND  
**Impact:** Metre constraint isn't working - all lines score 0.00 for metre  
**Evidence:** `test_real_generation.py` shows `metre=0.00` for all candidates  
**Root cause:** Haiku has `syllables_per_line=0` (marked as "special-cased: 5-7-5"), but the special case is **not implemented**.
- `FormSpec.syllables_per_line=0` for haiku
- `ConstrainedLoop` passes this to `LineScorer(target_syllable_count=0)`  
- `metre_score()` checks `if target_syllable_count <= 0: return 0.0`
- Result: all haiku lines score 0.00 for metre regardless of actual syllable count

**Fix needed:** ConstrainedLoop must track line position and pass correct target (5/7/5) to scorer for each haiku line

### #3: Theme scoring gives 0.00 (no embedding client)
**Status:** Expected (by design)  
**Impact:** Semantic relevance not scored without embeddings  
**Evidence:** `theme=0.00` for all candidates  
**Note:** Test runs without `embedding_client`, so this is expected. But should fall back gracefully and maybe warn user.

### #4: Composite scores are identical (0.150) for all candidates
**Status:** TODO  
**Impact:** Can't distinguish between candidates, random selection  
**Evidence:** All candidates score exactly 0.150, only `novelty=1.00` varies (doesn't affect total)  
**Root cause:** Likely related to #2 (metre broken) and #3 (theme missing) - need to check `composite_score()` weighting

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

1. ✅ Fix stub client (#1) - IN PROGRESS
2. Fix metre scoring (#2) - NEXT
3. Investigate composite_score weighting (#4)
4. Add graceful degradation for missing embeddings (#3)
5. Test with real LLM (#5)
6. Add alternative presentation (#6) - P1

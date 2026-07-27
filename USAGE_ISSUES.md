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

### #2: Metre scoring gives 0.00 for all candidates
**Status:** TODO  
**Impact:** Metre constraint isn't working - accepts 32-syllable prompts as valid 5-syllable lines  
**Evidence:** `test_real_generation.py` shows `metre=0.00` for all candidates, `syllables=32, valid=True` for haiku (target=5)  
**Root cause:** Unknown - need to check `metre_score()` function in `evaluation/metrics.py`

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

# Generation Quality — Status & Plan

Living tracker for poesia poem-quality work. Last updated 2026-08-31.

## Goal

Produce coherent, metrically-correct, fluent poems — not just scaffolding.

## What's landed (gaps closed)

| # | Item | How |
|---|---|---|
| 1 | Metre hard-gate | repair loop rejects off-metre lines; strict-improvement acceptance |
| 2 | Routing | groq-first default, sticky provider, `LLM_ROUTE` override |
| 3 | Fluency | `--polish` detects + repairs stiff lines |
| 4 | Coherence | `--draft` whole-poem draft-then-revise path |
| 5 | Draft auto-default | long rhymed forms (sonnets) draft by default |
| 6 | Hybrid slot | `--repair-llm` separate metre/rhyme repair model |
| 7 | Fine-tune prompt | aligned to training format + `repeat_penalty=1.15` |
| 8 | Rhyme-key hygiene | raw keys removed from all 4 LLM-facing prompts |
| 9 | Draft prompt | adds "no title/preamble" + syllable-count hint for general models |
| 10 | Draft length validation | `run_draft()` warns when the draft is shorter than the form requires, instead of silently shipping a fragment as "the poem" (commit `9b7b0a2`) |

## Fine-tune verdict (measured 2026-08-30, corrected 2026-08-31)

- fine-tune draft (raw, unrepaired), **3 themes**: **7/42 (16.7%)**
- groq draft (raw, unrepaired), **3 themes**: **13/40 (32.5%)** — groq wins ~2× on raw metre
- hybrid (groq draft + fine-tune repair via `--repair-llm llama_cpp`), **3 full-length trials**:
  "la luna" 11/14 (78.6%), "el mar" 5/14 (35.7%), "el tiempo" 5/14 (35.7%) — **aggregate 21/42
  (50%)**, statistically indistinguishable from the pure-groq line-by-line baseline (7–9/14,
  ~50–64% measured separately). The original single-sample 8/14 hybrid figure above was **not
  representative** — variance across themes is wide (35.7%–78.6%). Rhyme-key correctness was
  weak in every one of the 3 trials (the dominant defect class in every log, not injected-key
  leakage specifically — that leak was already fixed per gap #8).

→ **Fine-tune is still not ready** to be primary or repair, and the earlier "hybrid clearly
wins" read does not hold up under more than one sample. Keep it out of the default route.
Its value is *voice*, not metre.

## Open seams / gaps

| # | Gap | Status |
|---|---|---|
| 1 | Draft prompt syllable-count hint | ✅ done |
| 2 | Re-run full suite after parallel commits | ✅ done (0 fail / 0 err / 1 skip) |
| 3 | `benchmark_metre.py` tests line gen, not draft path | ✅ done — added `--draft` mode |
| 4 | Draft path drops `--interactive`/`--show-alternatives`/`--guest-words`/`--seeds`/`--brief` | by design (falls back to line-by-line) |
| 5 | `--repair-llm` only affects draft-path repair | ✅ done — now affects both paths |
| 6 | No form-aware routing (fine-tune removed entirely) | todo — re-add when fine-tune ready |
| 7 | `tone` silently dropped in draft prompt | ✅ done — restored (backend-aware) |
| 8 | `--repair-llm` unvalidated | ✅ done — `_resolve_llm_client` already fails fast |
| 9 | Fine-tune fate: re-train vs deprioritize | decision needed |
| 10 | Draft shorter than form's line count silently accepted | ✅ done — `run_draft()` now warns (`draft has N/M lines...`) |
| 11 | Rhyme-key correctness weak even after repair (hybrid path, all 3 trials) | ✅ fix landed (`b120de0`) — repair loop now enforces rhyme, not just metre, in both paths; warns when repair still fails after max attempts instead of shipping silently |
| 12 | Stray non-Spanish/English fragments leak into cleaned candidates (e.g. a bare `"e.g."`, a dangling `", y."`) seen in one "el mar" trial | not started — minor, one-off so far |
| 13 | Rhyme repair accepts a literal repeated word as a "resolved" rhyme (e.g. two A-rhyme lines both ending on "swell") — passes `rhyme_key()` trivially since it's the same word, but it's not a rhyme | ✅ fix landed — see below |

## Next actions (priority order)

1. ✅ Syllable-count hint in draft prompt.
2. ✅ Re-run full test suite (0 failures, 0 errors, 1 skip).
3. ✅ Extend `benchmark_metre.py` with a `--draft` mode.
4. ✅ Restore `tone` in the draft prompt (backend-aware).
5. ✅ Make `--repair-llm` affect line-by-line repair too.
6. ✅ Warn instead of silently shipping a short/degraded draft.
7. ✅ Rhyme-key repair correctness — root-caused and fixed 2026-08-31 (`b120de0`), see analysis
   below.
8. Decide fine-tune fate — re-train vs deprioritize.
9. Re-add form-aware routing once the fine-tune demonstrably beats groq.

### Root cause: rhyme-key repair (gap #11)

Two independent bugs, one in each repair path, plus one correct reference pattern already
in the file:

- **Draft path** (`_repair_draft_line`, `constrained_loop.py` ~L792-857): the retry loop's
  accept/`break` condition only re-checks metrical syllable count, never rhyme. When metre
  is already correct going in — the common case where rhyme is the *only* defect — the
  repair LLM is asked to fix the rhyme, but the loop exits after that single attempt whether
  or not the rhyme actually changed. This is why draft-path trials show wrong-rhyme-key
  warnings on most lines (see the three hybrid trial logs above: rhyme was the dominant
  defect class in all of them).
- **Line-by-line path** (`_repair_candidate`/`_needs_repair`, ~L417-465): rhyme isn't part
  of the repair trigger at all — `_needs_repair()` only checks validity, off-metre, and
  guest-word placement. Rhyme correctness is assumed to already be handled upstream by
  scoring/ranking the `n_candidates` batch and picking the best-scored one. If none of the
  sampled candidates happen to rhyme correctly, the best-scoring wrong-rhyme line ships
  **silently** — the fallback-acceptance warning block (~L466-476) only warns about metre
  and guest-word, never rhyme, so this failure mode currently produces no diagnostic at all.
- **Reference pattern, already correct**: `_polish_line()` (~L484-521), which runs after
  both repair steps to fix fluency, computes `rhyme_ok` after each rewrite and only accepts
  the rewrite `if metre_ok and rhyme_ok`, otherwise keeps the original candidate. The fix for
  both paths above is to adopt this same discipline — loop until metre *and* rhyme both hold
  (or attempts are exhausted) in the draft path, and add rhyme-incorrectness to the
  line-by-line path's repair trigger with an honest warning when it can't be resolved.

**Post-fix 3-theme re-run (2026-08-31), same themes as the original trial** (`poesia write
--draft --llm groq --repair-llm llama_cpp --verbose`):

| Theme | Metre correct | Rhyme-key warnings |
|---|---|---|
| la luna | 4/13 (30.8%) | 6 lines |
| el mar | 6/14 (42.9%) | 9 lines |
| el tiempo | 9/14 (64.3%) | 7 lines |
| **Aggregate** | **19/41 (46.3%)** | **22/41 lines (53.7%)** |

Pre-fix aggregate was 21/42 (50%). **Metre accuracy is statistically flat** (46.3% vs 50%, well
within the trial-to-trial variance already documented) — the fix was never expected to move
this number, since it targets rhyme enforcement, not metre. `b120de0` does exactly what it
should: every rhyme failure that survives repair is now honestly reported instead of silently
shipped.

**Root cause correction (2026-08-31):** the "capability ceiling" framing above was wrong, or at
least incomplete. Checked `seeds/poetry_corpus/training_data_structured/sonetos_train.jsonl`
directly: all 500 training examples are one shape — `"Write a soneto in Spanish.\nRhyme
scheme: X.\nTheme: Y."` → full poem. **Zero** are line-level edit/repair examples. But
`LlamaCppLoRAClient.repair()` sends `'Fix this poetic line: {defect}\nLine: "{line}"\nOutput
ONLY the corrected line.'` — a task shape the model has never once seen in training. This is a
prompt/task-format mismatch, not evidence the model is bad at rhyme.

Proof: re-ran "la luna" through the *actual default* path (`--draft --llm groq`, no
`--repair-llm` override, so repair goes through groq too — what most users would actually run)
— **11/14 (78.6%) lines metrically correct**, matching the original pre-fix "la luna" baseline
and dramatically beating the 4/13 (30.8%) seen with `--repair-llm llama_cpp`. General-purpose
instruct models (groq) can follow an arbitrary "fix this line" instruction because that's
exactly what they're trained for; the narrow qwen3b fine-tune cannot, because it was never shown
that task once.

**Revised verdict:** `--repair-llm llama_cpp` should not be recommended/used as-is — it's not
"the fine-tune isn't good enough," it's "we're asking it to do something outside its training
distribution entirely." Either exclude it from the repair role until retrained on repair-style
examples, or drop the `--repair-llm llama_cpp` option pending that. The original "fine-tune
isn't ready as *primary generator*" verdict (measured via `--llm llama_cpp`, a task it *was*
trained for) still stands on its own evidence and is unaffected by this correction.

### Root cause: identical-word "rhyme" (gap #13)

Found live: a `poesia write --form sonnet_shakespearean --language en` run produced a
quatrain whose A-rhyme pair both ended on the literal word "swell" — mechanically valid
(`rhyme_key()` on a word against itself always matches) but not a rhyme at all. No existing
check caught this: `RhymeTracker` only stores each group's target consonant key and an example
word for prompting; `_off_rhyme()` (both repair paths) and `_polish_line`/`_polish_draft_line`
only ever compared consonant keys, never the actual words.

Fix: `_off_rhyme()` now also takes an `example_word` (the word already committed for that rhyme
group, from `RhymeTracker.example_word_for_line()`, `None` on a group's opening line) and flags
a candidate whose last word matches it case-insensitively, regardless of key match. Threaded
through `_repair_candidate`, `_polish_line`, `_repair_draft_line`, `_polish_draft_line`, and both
`run()`/`run_draft()` call sites. The repair prompt (`_repair_defect_description`) now tells the
LLM explicitly not to reuse that word, and the warning emitted when repair still can't fix it
(`_rhyme_repair_warning()`) says "repeats the word X" instead of the generic "wrong rhyme key" —
the rhyme *sound* may be fine; the defect is that it isn't a new word. Regression tests in
`tests/test_generation_rhyme_repair.py`.

## MLOps / data engineering (added 2026-08-30, updated 2026-08-31)

- ✅ `benchmark_metre.py` logs each cell to MLflow (params: backend/form/mode/theme; metric: `metre_accuracy`; artifact: `samples.txt`). Tracking URI = `DATABASE_URL` or `sqlite:///mlruns/mlflow.db` (`file:./mlruns` was removed by MLflow 3.x and silently no-op'd — fixed 2026-08-31, regression test added: `tests/test_mlflow_wiring.py`).
- ✅ `dvc.yaml` gained a `benchmark` stage (deps: script + core generation modules; no outs — results go to MLflow).
- ✅ `models/poetry-lora-qwen3b/qwen3b-poetry-Q4_K_M.gguf` is DVC-versioned (`.dvc` pointer committed; data in `.dvc/cache`). `dvc status models/poetry-lora-qwen3b.dvc` confirmed up to date 2026-08-31.
- ✅ 2026-08-31: re-ran `benchmark_metre.py --backends groq,llama_cpp --forms soneto:es --draft` now that MLflow logging actually works — groq 45% (5/11) vs. llama_cpp/qwen3b fine-tune 14% (2/14), confirmed queryable in `mlruns/mlflow.db` (`Default` experiment, runs `benchmark-metre-groq-soneto:es` / `benchmark-metre-llama_cpp-soneto:es`). Matches the fine-tune verdict above — groq still ahead on metre.
- ⚠️ New blocker (found 2026-08-31): `evaluate_adapter_mlflow.py` is hardcoded to `LoRAClient` (transformers + bitsandbytes 4-bit, requires CUDA). This machine's GPU (Quadro M1000M, compute capability 5.0) is below the installed PyTorch's minimum (sm_75); `poesia.device.cuda_usable()` returns `False`, so the script fails fast for **all 9 trained adapters** — not just some. Only `poetry-lora-qwen3b` has a GGUF export usable via the `llama_cpp` fallback, and the eval script doesn't route through it. Evaluating the other 8 adapters (`v2`, `v2-fixed`, `dpo-expanded`, `composite`, `multiform`, `3b`, `distilled`, `smoke-test-adapter`) needs either cloud/compatible GPU access or a GGUF export + llama_cpp eval path per adapter — out of scope until prioritized.
- ⚠️ Follow-up (lower priority): `.gitignore`'s `models/*.dvc` pattern only un-ignores top-level `.dvc` files, not nested ones (e.g. a hypothetical per-file `models/poetry-lora-qwen3b/foo.dvc` would still be ignored) — not currently biting anything since `poetry-lora-qwen3b.dvc` tracks the whole directory as one dir-output, but worth narrowing if per-file `.dvc` pointers are ever added under `models/`.

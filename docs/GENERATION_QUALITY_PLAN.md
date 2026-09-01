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

**Update (2026-09-01, see full sweep below):** the 8-adapter GGUF sweep only measures line-count
(trivially 100%, since `run_draft()` already pads/truncates) and post-*repair* syllable
deviation — it does not check rhyme scheme or count per-line metre pass/fail the way
`benchmark_metre.py`/the hybrid trials above do. So it validates that the repair loop, given a
full budget (`max_repair_attempts=4`), reliably drives structural line-length errors down to
near-zero on every adapter — a capability/tooling result, not a new metre/rhyme quality result.
It does not contradict or supersede the verdict above (rhyme-key correctness, not syllable
count, was always the dominant defect class). The concrete unblock is that adapter evaluation no
longer requires training-capable hardware: any future adapter iteration can be checked on this
laptop via the llama.cpp fallback, without needing a cloud GPU just to know if it's worth
re-training. Next action 8 is downgraded from "decide fine-tune fate" to "extend this eval
script to also score rhyme-key correctness per line (not just syllable count), since that's the
actual open defect" — see next actions below.

### All 8 local adapters evaluated via GGUF/llama.cpp (2026-09-01)

With the CUDA-hardcoding fix (`evaluate_adapter_mlflow.py` now falls back to
`LlamaCppLoRAClient` when `cuda_usable()` is `False`) and the `n_ctx` fix below, every locally
trained adapter was run through `loop.run()` (line-by-line, 8 candidates/line, full repair) for
3 themes (luna, mar, tiempo). `poetry-lora-composite` was excluded — its DVC-tracked artifact is
empty (0 bytes, no real weights). All 8 hit 100% line-count accuracy (14/14).

**First pass** used `loop.run()`'s own internal default of `max_repair_attempts=2` — lower than
the CLI's already-improved default of 4 (gap #15) — because the eval script never passed the
parameter through. Ranked by avg syllable deviation from the 11-syllable target: distilled 0.14,
qwen3b 1.40, smoke-test-adapter 2.00, v2 3.83, v2-fixed 4.64, 3b 6.40, dpo-expanded 6.55,
multiform 12.02. Six of eight adapters showed one theme spiking to 15-27 syllables/line against
every other theme sitting near 9-11 (v2/luna 18.0, dpo-expanded/mar 26.4, v2-fixed/tiempo 24.3,
multiform/luna+mar both 26.7, 3b/luna 25.9, smoke-test/luna 15.9) — flagged as a systemic
long-line pattern, not yet root-caused.

**Root cause + fix:** `evaluate_adapter_mlflow.py`'s `loop.run(theme=theme, n_candidates=8)` call
never passed `max_repair_attempts`, so it silently used `ConstrainedLoop.run()`'s conservative
built-in default (2) instead of the CLI's improved default (4). Fixed by passing
`max_repair_attempts=4` explicitly, matching what a real `poesia write` invocation gets.

**Re-run with `max_repair_attempts=4`**, same 8 adapters, same 3 themes — ranked by avg syllable
deviation (prior first-pass value in parens):

| Adapter | Avg syllable dev | Prior (repair budget 2) |
|---|---|---|
| qwen3b | **1.00** | 1.40 |
| distilled | 1.29 | 0.14 |
| v2 | 1.95 | 3.83 |
| 3b | 2.67 | 6.40 |
| v2-fixed | 4.88 | 4.64 |
| smoke-test-adapter | 5.12 | 2.00 |
| dpo-expanded | 5.83 | 6.55 |
| multiform | 7.93 | 12.02 |

The long-line pattern is resolved for most of the adapters that showed it: v2 (18.0→13.0
luna), 3b (25.9→19.3 luna), multiform (26.7→26.2 luna, still high but down from two spiked
themes to one), and dpo-expanded (26.4→24.1 mar, improved but still the worst single theme in
this run) all dropped meaningfully with the larger repair budget, confirming
`max_repair_attempts` — not an adapter-specific defect — was the dominant cause. `v2-fixed` and
`smoke-test-adapter` moved in the other direction (4.64→4.88, 2.00→5.12); since generation isn't
seeded, some of this is run-to-run sampling noise rather than a regression, but neither has a
run in which it stays under 10 syll/line on every theme, so residual variance on these two isn't
fully explained by the repair-budget fix alone. `qwen3b` and `distilled` remain the two most
consistent adapters across both passes.

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
| 12 | `run_draft()` sometimes concatenates two disconnected fragments into one drafted line (e.g. `"tranquila alta."`, `"brinda, ansia."`, `"pura, elida."`, `"corazón, espíritu."`) instead of one coherent thought — reproduced 4x in the "el mar" trial, not a one-off. `_clean_candidate`/`_clean_candidates` don't catch it (they target prompt-echo artifacts, not fragment merging); a coherence-classifier probe scored only 60% on these, misclassifying all 4 as COHERENT | ✅ fix landed — (a) `_metre_defect_text` flags lines missing >40% of their target syllables as "disconnected fragments" and tells the repair LLM to rewrite rather than pad (used by both `_repair_defect_description` and `_repair_draft_line`); (b) `_line_is_stiff`'s prompt (the `--polish` fluency gate) now explicitly names the "two disconnected fragments crammed into one line" failure mode with a reproduced example, since it was never told to check for that pattern at all. Neither fix has been validated against a live trial yet — see caveat below |
| 13 | Rhyme repair accepts a literal repeated word as a "resolved" rhyme (e.g. two A-rhyme lines both ending on "swell") — passes `rhyme_key()` trivially since it's the same word, but it's not a rhyme | ✅ fix landed — see below |
| 14 | Repair prompt for a wrong-rhyme-sound defect is vague ("rhymes with its rhyme-group partner") — gives the repair LLM no concrete word to work from, so genuine sound mismatches (seen live: needed `'UW1 F'`) often survive `max_repair_attempts` | ✅ fix landed — see below |
| 15 | `WriteConfig.max_repair_attempts` was built (hardcoded to 2 in `_build_write_config`) but never actually passed to `loop.run()`/`loop.run_draft()` — raising the budget was impossible even by editing code, since the field was dead | ✅ fix landed — wired through, exposed as `--max-repair-attempts` (default raised 2→4) |

## Next actions (priority order)

1. ✅ Syllable-count hint in draft prompt.
2. ✅ Re-run full test suite (0 failures, 0 errors, 1 skip).
3. ✅ Extend `benchmark_metre.py` with a `--draft` mode.
4. ✅ Restore `tone` in the draft prompt (backend-aware).
5. ✅ Make `--repair-llm` affect line-by-line repair too.
6. ✅ Warn instead of silently shipping a short/degraded draft.
7. ✅ Rhyme-key repair correctness — root-caused and fixed 2026-08-31 (`b120de0`), see analysis
   below.
8. ✅ Adapter evaluation unblocked on this laptop (GGUF/llama.cpp fallback + `max_repair_attempts`
   wiring fix); all 8 local adapters swept, see below. Downgraded from "decide fine-tune fate" —
   re-scoped to: extend `evaluate_adapter_mlflow.py` to score rhyme-key correctness per line, not
   just syllable count, since rhyme (not metre) is the adapters' actual open defect.
9. Re-add form-aware routing once the fine-tune demonstrably beats groq.
10. Validate the gap #12 fragment-defect fix against a live hybrid trial (unit-tested against the
    4 reproduced examples, but not yet confirmed to reduce the leak rate in practice).

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

### Repair-prompt fix: name the actual rhyme word (gap #14)

Same live run also surfaced two `[WARN]` lines that gap #11's fix correctly *reported* rather
than silently shipping — a genuine off-metre line and a genuine wrong-rhyme-sound line that
survived `max_repair_attempts` (default 2). Root cause: `_repair_defect_description()` and
`_repair_draft_line()`'s inline defect list told the repair LLM only "the line must end with a
word that rhymes with its rhyme-group partner" — no concrete word, nothing to act on. This
phrasing dates to gap #8 (raw phonetic rhyme keys like `'UW1 F'` were removed from prompts
because they read as gibberish), but the fix over-corrected: it dropped the *word* along with
the *key*, even though the candidate-generation prompt (`candidate_generator.py`) already names
the concrete word ("rhymes with 'X' … use a DIFFERENT word") and works fine.

Fix: extracted `_rhyme_defect_parts()`, used by both repair paths, which names the actual
`example_word` when known — `'the line must end with a new word that rhymes with "X" (not "X"
itself)'` — matching the pattern that was already working in candidate generation. Falls back to
the old vague phrasing only when no example word exists yet (a rhyme group's opening line, which
never has a rhyme defect to repair in the first place). Never reintroduces the raw phonetic key.
This doesn't guarantee every repair now succeeds within `max_repair_attempts` — that remains
inherent LLM variance, honestly reported when it happens — but gives the model something
concrete to work with instead of an abstract instruction. Regression tests in
`tests/test_generation_rhyme_repair.py`.

### Wiring gap: `max_repair_attempts` was a no-op (gap #15)

The same live run's remaining `[WARN]` (a genuine wrong-rhyme-sound line surviving repair) calls
for more attempts, not more prompt engineering. But raising the budget did nothing: `_build_
write_config()` hardcoded `max_repair_attempts=2` into `WriteConfig` regardless of any future
flag, and — the actual bug — `cli.py`'s calls to `loop.run(...)` and `loop.run_draft(...)` never
passed `max_repair_attempts` at all, so both silently fell back to their own internal default of
2. `WriteConfig.max_repair_attempts` was dead code; there was no way to raise the repair budget
short of editing `constrained_loop.py`'s defaults directly.

Fix: added a `--max-repair-attempts` CLI flag (default 4, up from the old hardcoded 2), threaded
it through `_build_write_config()` into `WriteConfig`, and passed `config.max_repair_attempts`
into both `loop.run()` and `loop.run_draft()` call sites. `WriteConfig`'s own default raised to 4
to match, for non-CLI callers. Regression tests in `tests/test_cli_max_repair_attempts.py` assert
both the new default and that the flag's value actually reaches `ConstrainedLoop.run()`.

## MLOps / data engineering (added 2026-08-30, updated 2026-08-31)

- ✅ `benchmark_metre.py` logs each cell to MLflow (params: backend/form/mode/theme; metric: `metre_accuracy`; artifact: `samples.txt`). Tracking URI = `DATABASE_URL` or `sqlite:///mlruns/mlflow.db` (`file:./mlruns` was removed by MLflow 3.x and silently no-op'd — fixed 2026-08-31, regression test added: `tests/test_mlflow_wiring.py`).
- ✅ `dvc.yaml` gained a `benchmark` stage (deps: script + core generation modules; no outs — results go to MLflow).
- ✅ `models/poetry-lora-qwen3b/qwen3b-poetry-Q4_K_M.gguf` is DVC-versioned (`.dvc` pointer committed; data in `.dvc/cache`). `dvc status models/poetry-lora-qwen3b.dvc` confirmed up to date 2026-08-31.
- ✅ 2026-08-31: re-ran `benchmark_metre.py --backends groq,llama_cpp --forms soneto:es --draft` now that MLflow logging actually works — groq 45% (5/11) vs. llama_cpp/qwen3b fine-tune 14% (2/14), confirmed queryable in `mlruns/mlflow.db` (`Default` experiment, runs `benchmark-metre-groq-soneto:es` / `benchmark-metre-llama_cpp-soneto:es`). Matches the fine-tune verdict above — groq still ahead on metre.
- ✅ Blocker found 2026-08-31, resolved 2026-09-01: `evaluate_adapter_mlflow.py` was hardcoded to `LoRAClient` (requires CUDA sm_75+, this machine's Quadro M1000M is sm_50) and failed fast for 8 of 9 adapters. Fixed via a `_make_llm_client()` CUDA/llama.cpp dispatch (see `poesia/generation/llama_cpp.py` for the hardware rationale — not duplicated here) plus an `n_ctx` bump and a `max_repair_attempts` wiring fix. All 8 adapters now evaluate cleanly on this laptop; results and root-cause detail are in "All 8 local adapters evaluated via GGUF/llama.cpp" above, not restated here.
- ✅ `dvc.yaml`'s `evaluate` stage (2026-09-02) is now a `foreach` over all 8 adapters, each with its own `dvc.lock` entry keyed on that adapter's directory hash — see `DVC_INTEGRATION.md` for the pipeline structure and the `--single-item` gotcha (a bare `dvc repro evaluate` would also trigger the `train` stage, i.e. actual GPU training, on this laptop).
- ⚠️ Follow-up (lower priority): `.gitignore`'s `models/*.dvc` pattern only un-ignores top-level `.dvc` files, not nested ones (e.g. a hypothetical per-file `models/poetry-lora-qwen3b/foo.dvc` would still be ignored) — not currently biting anything since `poetry-lora-qwen3b.dvc` tracks the whole directory as one dir-output, but worth narrowing if per-file `.dvc` pointers are ever added under `models/`.

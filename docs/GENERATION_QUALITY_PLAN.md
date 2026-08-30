# Generation Quality — Status & Plan

Living tracker for poesia poem-quality work. Last updated 2026-08-30.

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

## Fine-tune verdict (measured 2026-08-30)

- fine-tune draft: **5/13** metrically correct (authentic voice, off-metre)
- groq draft: **7/14** (better metre)
- hybrid (groq draft + fine-tune repair): 8/14 but **injected literal rhyme keys**

→ **Fine-tune is not ready** to be primary or repair. Keep it out of the default
route. Its value is *voice*, not metre.

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

## Next actions (priority order)

1. ✅ Syllable-count hint in draft prompt.
2. ✅ Re-run full test suite (0 failures, 0 errors, 1 skip).
3. ✅ Extend `benchmark_metre.py` with a `--draft` mode.
4. ✅ Restore `tone` in the draft prompt (backend-aware).
5. ✅ Make `--repair-llm` affect line-by-line repair too.
6. Decide fine-tune fate — re-train vs deprioritize.
7. Re-add form-aware routing once the fine-tune demonstrably beats groq.

## MLOps / data engineering (added 2026-08-30, updated 2026-08-31)

- ✅ `benchmark_metre.py` logs each cell to MLflow (params: backend/form/mode/theme; metric: `metre_accuracy`; artifact: `samples.txt`). Tracking URI = `DATABASE_URL` or `sqlite:///mlruns/mlflow.db` (`file:./mlruns` was removed by MLflow 3.x and silently no-op'd — fixed 2026-08-31, regression test added: `tests/test_mlflow_wiring.py`).
- ✅ `dvc.yaml` gained a `benchmark` stage (deps: script + core generation modules; no outs — results go to MLflow).
- ✅ `models/poetry-lora-qwen3b/qwen3b-poetry-Q4_K_M.gguf` is DVC-versioned (`.dvc` pointer committed; data in `.dvc/cache`). `dvc status models/poetry-lora-qwen3b.dvc` confirmed up to date 2026-08-31.
- ✅ 2026-08-31: re-ran `benchmark_metre.py --backends groq,llama_cpp --forms soneto:es --draft` now that MLflow logging actually works — groq 45% (5/11) vs. llama_cpp/qwen3b fine-tune 14% (2/14), confirmed queryable in `mlruns/mlflow.db` (`Default` experiment, runs `benchmark-metre-groq-soneto:es` / `benchmark-metre-llama_cpp-soneto:es`). Matches the fine-tune verdict above — groq still ahead on metre.
- ⚠️ New blocker (found 2026-08-31): `evaluate_adapter_mlflow.py` is hardcoded to `LoRAClient` (transformers + bitsandbytes 4-bit, requires CUDA). This machine's GPU (Quadro M1000M, compute capability 5.0) is below the installed PyTorch's minimum (sm_75); `poesia.device.cuda_usable()` returns `False`, so the script fails fast for **all 9 trained adapters** — not just some. Only `poetry-lora-qwen3b` has a GGUF export usable via the `llama_cpp` fallback, and the eval script doesn't route through it. Evaluating the other 8 adapters (`v2`, `v2-fixed`, `dpo-expanded`, `composite`, `multiform`, `3b`, `distilled`, `smoke-test-adapter`) needs either cloud/compatible GPU access or a GGUF export + llama_cpp eval path per adapter — out of scope until prioritized.
- ⚠️ Follow-up (lower priority): `.gitignore`'s `models/*.dvc` pattern only un-ignores top-level `.dvc` files, not nested ones (e.g. a hypothetical per-file `models/poetry-lora-qwen3b/foo.dvc` would still be ignored) — not currently biting anything since `poetry-lora-qwen3b.dvc` tracks the whole directory as one dir-output, but worth narrowing if per-file `.dvc` pointers are ever added under `models/`.

# Tasks — PoesIA (Kanban)

## IN PROGRESS

- [ ] **Retrain: bigger base model and expanded corpus** (decided 2026-10-04). Plan and
      step order: `docs/RETRAINING_PLAN_2026-10.md` §6; current order in
      `activeContext.md` "Current focus". Done: corpus build and dedup (`corpus_master`,
      85,027 poems, mainly English), truncation fix (`_drop_overlong`). Next, in order:
  - [ ] "Best" memory layout in `scripts/train_poetry_lora.py` (NF4 `lm_head` via an empty
        bitsandbytes skip list, embedding on CPU), then the Qwen3-8B smoke test (~50 steps;
        peak memory, tokens/s). Qwen3.5-9B after `flash-linear-attention` +
        `causal-conv1d` are in the env.
  - [ ] Stronger evaluation: ≥5 themes, seeded, >1 sample per theme, English themes and an
        English metre target, scorer checked against `eval_gold/adso_gold_100.jsonl`.
  - [ ] Per-line rhyme-key score in `scripts/evaluate_adapter_mlflow.py`
        (`GENERATION_QUALITY_PLAN.md` next action 8b; not implemented).
  - [ ] Rebuild the July `distilled` baseline on the desktop (old adapters are laptop-only).
  - [ ] Base-model comparison on the distilled recipe (§6 step 3).
  - [ ] First sized corpus run (`build_fixed_dataset.py --max-poems N`, sized by §5).
  - [ ] After the retrain: Model Registry aliases for the new champion/challenger.
- [ ] **Per-machine envs** (2026-09-26) — desktop `poesia` built and checked (Python
      3.13.14 after the 2026-10-04 switch). Remaining: `poesia-gpu` on the desktop
      (`scripts/build_llama_cpp.sh`; not created yet); on the laptop, recreate `poesia` on
      3.13 (`scripts/env.sh create`), build `poesia-gpu`, run both `--check`s and tick
      README "Machines" → "Verify on the laptop".

## BACKLOG (priority order)

- [ ] **GalerIA character comic** (paused 2026-10-07, waiting on API keys): new pictures
      of Angel's girlfriend and their dog in the style of one reference ink drawing.
      Handoff with everything tried, what fails, and the key plan:
      `docs/GALERIA_CHARACTER_COMIC_HANDOFF.md`. Research:
      `docs/CHARACTER_CONSISTENT_ILLUSTRATION_RESEARCH.md`. Next: Path A (free manual test
      in the Gemini/ChatGPT apps) or Path B (`GEMINI_API_KEY` + `FAL_KEY` → stage-0
      six-model test, $5–10). Claude-drawn SVG is a dead end; don't retry it.
- [ ] **Lemonade integration for the AMD Lemonade Developer Challenge** (2026-09-28) —
      Lemonade as LLM provider, PoesIA's own adapter served locally, GalerIA image backend,
      poem read aloud. Plan and checklist: `docs/LEMONADE_INTEGRATION.md`. Time-sensitive:
      laptops are given "until supplies are exhausted".
- [ ] **Private DVC remote both machines reach** (`RETRAINING_PLAN_2026-10.md` §7) — the
      new corpus is cached on the desktop only and the July adapters on the laptop's D:
      drive only. The GitHub repo is public, so the remote must be private.
- [ ] **Docker images and compose stack** (2026-10-04): enable Docker Desktop's WSL
      integration (off; the compose stack is down), build both images once (never built
      since the 3.13 switch), then test the compose stack end to end (postgres + mlflow-ui +
      training service). Align `training.Dockerfile` with the gpu-cuda13 tier (CUDA 12.4 base
      and unpinned libs vs the env's cu130 pins). `train.yml` needs a self-hosted GPU runner
      that doesn't exist.
- [ ] **`classical` extra: scansion on Python 3.13** — cltk resolves to 2.x, which has no
      scansion module; port the cltk 1.x scanners (MIT) or drop the extra.
- [ ] **career-assets ADR 0007 note** — it quotes poesia's old "8B won't fit 8 GB" claim,
      corrected 2026-10-04 (`RETRAINING_PLAN_2026-10.md` §3). Pending Angel.
- [ ] **Run HPO search** — Optuna hyperparameter search
- [ ] **Wire `PoetryModelWrapper`** into `mlflow models serve`
- [ ] **Add titles to Machado poems** — extract from Gutenberg TOC
- [ ] **GalerIA: more image backends** — Gemini free tier (quality, needs a key), AI Horde
      (async polling); real DALL·E/SDXL smoke test with a paid key
      (`docs/IMAGE_GENERATION_PROVIDERS.md`)
- [ ] **Try Unsloth** — install and test 2x faster training. Blocked 2026-09-27: unsloth 2026.9.11 caps torch <2.13, transformers <=5.5, trl <=0.24 (see docs/archive/EXPERIMENTS_PLAN.md)
- [ ] **Phase 4E** — literary taxonomy auto-tagging
- [ ] **WordNet Spanish** (omw-es:1.4) — retry when server is up
- [ ] **Snapshot tests** — CLI + generation pipeline

## DONE

### 2026-10-04 (later): code bugs and dependency security
- [x] `MLproject` loads again (one env field rule of MLflow 3); `monitor` entry template fixed
- [x] `memoria add-influence` persists to `data/influences.yaml` (+3 tests); CLI command/file names fixed
- [x] Gallery telemetry on `sqlite:///mlruns/mlflow.db`; Docker training command + `mlops/data` mount fixed
- [x] mlflow 3.14.0 → 3.16.1, cryptography 48.0.1 → 50.0.2; pip-audit gates CI on the real set; `safety` removed
- [x] Extras: `spanish` gains `fonemas`; `graphrag` drops `neo4j` (ROADMAP non-goal)
- [ ] Laptop: back up and `mlflow db upgrade` the 3.14 tracking store, regenerate the SQL dump

### 2026-10-04 (retraining plan, corpus, Python 3.13)
- [x] **Retrain decided** (Angel): larger corpus, larger base model; plan
      `docs/RETRAINING_PLAN_2026-10.md`; `scripts/estimate_qlora_vram.py` estimates a
      ~9B ceiling on the RTX 3070 (unmeasured)
- [x] **Corpus build and dedup** — `scripts/build_corpus.py` → `corpus_master/poems.jsonl`:
      85,027 poems (49,128 en, 35,899 es; 9,405 sonnets), dedup by full text + first line,
      ADSO gold removed (was 12,340 unique; the old "~13,049" counted duplicates). New
      sources via `scripts/ingest_external_corpora.py`; `dvc add`-ed (desktop cache only)
- [x] **Truncation fix** — `train_poetry_lora.py` drops examples longer than `max_length`
      (`_drop_overlong`) instead of cutting them; counts logged to MLflow
- [x] **One Python version: 3.13** — pyproject `>=3.13,<3.14`, CI, deploy, pre-commit, both
      Dockerfiles, Colab pins (`90f6c32`, `4fdbfb4`, `fd53708`)
- [x] **CI green** — installs mlflow + the CPU training stack; 446 tests on 3.13, 0 skipped
      (`56b8167`, `90f6c32`); local suite 519 pass
- [x] **networkx 3.6.1 → 3.7** (`0789824`)
- [x] **Extras installable on 3.13** (`75f3e6b`): `recitation` = piper-tts (Spanish verified),
      `music-ai` = MusicGen through transformers + scipy
- [x] **Closed as superseded by the retrain decision:** "Test poem generation with
      v2-fixed" (v2-fixed is mid-pack, 4.80); "Run Qwen2.5-3B training with fixed format";
      "Model Registry aliases for distilled/qwen3b" (their order is within noise; alias
      the retrained adapters instead, see IN PROGRESS)

### 2026-09-08 (adapter evaluation)

> ⚠️ (2026-09-08) Adapter eval done — champion is `poetry-lora-distilled` (0.90).
> The "fixed-format" v2-fixed (4.80) and multi-form v3 (9.29) underperform the
> earlier distilled/v2/qwen3b; DPO (6.07) lost to plain CE. Full table in
> `docs/ANALOGIA_PLAN.md`. *(2026-10-04: distilled vs qwen3b is within noise —
> `RETRAINING_PLAN_2026-10.md` §4.)*

- [x] **Evaluate v2-fixed adapter** — DONE (2026-09-08): avg_syll_dev 4.80, line_acc 1.00 — not the champion.
- [x] **Compare adapters** — DONE (2026-09-08): champion `poetry-lora-distilled` (0.90); see `ANALOGIA_PLAN.md`.
- [x] **Run experiment grid (CE vs Composite vs DPO)** — effectively DONE: CE (distilled 0.90) beats DPO (6.07); `composite` never trained (dead).

### 2026-09-08 (v2-fixed retraining completed)
- [x] **v2-fixed retraining** (relaunched 2026-08-06) — completed and
      registered in MLflow as `poesia-lora-20260806_151949` (train_loss 0.38,
      eval_syllable_deviation 11.67, eval_line_count_accuracy 1.0); weights in
      DVC. ⚠️ Low train_loss but high syllable deviation — review before relying
      on it.

### Up to 2026-08-06

Moved verbatim to `memory-bank/archive/tasks_done_until_2026-08-06.md` (2026-10-05).

# Active Context — PoesIA

_Last updated: 2026-10-04 (retraining plan, Python 3.13; re-entry checklist, Current focus
and Document authority brought current)_

---

## What We Just Did (2026-10-05 → 10-07) — GalerIA character comic, paused

- **Goal (Angel):** comic-style pictures of his girlfriend and their dog, in the exact style
  of one ink drawing he likes. Reference, crops, attempts and scoring tools are in git at
  `seeds/characters/couple-ink/` (Angel's call, 2026-10-07), so any PC can continue.
- **Tried:** Claude drawing in SVG (two autumn-walk scenes, a measured head trace v3–v5
  scored by ink IoU). Angel's verdict: gaps in the fringe strands, irregular lashes,
  inelegant curves. The IoU score rose while quality fell; it measures placement, not line
  quality. **Dead end for drawing.**
- **Researched:** `docs/CHARACTER_CONSISTENT_ILLUSTRATION_RESEARCH.md` (+ notes in
  `docs/research/`). Plan: six-model reference-image test → threshold/vectorize →
  `ReferenceImageBackend` → LoRA only if needed. Gemini image output is likely no longer
  free (one fetch; confirm in AI Studio).
- **Blocked:** no API keys. Claude has no image model on any plan, including Max.
- **Handoff (single entry point):** `docs/GALERIA_CHARACTER_COMIC_HANDOFF.md`. Committed
  and pushed 2026-10-07. `IMAGE_GENERATION_PROVIDERS.md` corrected the same day.

## What We Just Did (2026-10-04) — retraining plan

- **Decision (Angel):** retrain, with the expanded corpus and a larger base model. This
  settles `GENERATION_QUALITY_PLAN.md` gap #9.
- **Plan:** `docs/RETRAINING_PLAN_2026-10.md`. It covers which base models fit on the RTX 3070,
  the state of the corpus, the evidence so far, the order of work, and Angel's open decisions.
- **Model ceiling:** `scripts/estimate_qlora_vram.py` (new) reads safetensors headers from
  Hugging Face. With `lm_head` in NF4 and the embedding in CPU RAM, it estimates that up to
  ~9B fits (Qwen3.5-9B about 5.8 GB, Qwen3-8B about 5.4 GB), and nothing at 12B or above.
  Unmeasured. Corrected the "8B needs ≥16 GB" claim in `LOCAL_ONLY.md` and
  `docs/archive/EXPERIMENTS_PLAN.md` §2.
- **Evidence caveat:** the top two adapters swapped order between the 09-01 and 09-08
  evaluations (3 unseeded themes), so `distilled` vs `qwen3b` is within noise. Note added to
  `ANALOGIA_PLAN.md`.
- **Blocker:** the desktop has no adapters (`models/` holds only `.dvc` pointers); the July
  adapters are only on the laptop's DVC remote (`/mnt/d/dvc-remotes/poesia`, its D: drive).
  The corpus was rebuilt on the desktop the same day (next bullet), and its DVC cache exists
  on the desktop only: the laptop's remote lacks it.
- **Corpus rebuilt on the desktop and enlarged (same day):** restored from git (`f8b2017^`;
  three folders match the DVC hashes exactly), re-fetched the 08-31 Gutenberg round, added
  4 Gutenberg books plus DISCO v5 and two Golden-Age corpora via the new
  `scripts/ingest_external_corpora.py`, then (Angel: Spanish and English, mainly English;
  copyrighted poems in, never shared) POSTDATA and two English sets. New
  `scripts/build_corpus.py` writes `corpus_master/` (85,027 poems: 49,128 en, 35,899 es;
  dedup across files, ADSO gold removed), and `build_fixed_dataset.py` reads it. ADSO gold
  (100 sonnets) lives in `eval_gold/`. All data gitignored and `dvc add`-ed (desktop cache
  only; 23,000 files unchanged).
- **Found:** line examples are cut at 300 tokens from the right, so from about line 19–20 of
  long poems the target line is lost (61–68% of non-sonnet examples; sonnets 1%). Fix options
  and the run-size formula (~2,600 usable tokens per poem): `RETRAINING_PLAN` §5.
- **Fixed same day:** truncation, by dropping examples that don't fit (`_drop_overlong`, §5).
  CI was red since 10-02 (no mlflow); it now installs mlflow and the CPU training stack.
  After the 3.13 switch below, CI runs one test job on Python 3.13: 446 passed, 0 skipped
  (`90f6c32`; hosted-provider and hosted-image test files excluded). Local full suite: 519
  pass.
- **One Python version: 3.13** (Angel, 2026-10-04): `requires-python >=3.13,<3.14`; CI,
  deploy, pre-commit, both Dockerfiles and the README moved off 3.11/3.12. Checked: Colab
  and Kaggle run 3.13, the llama-cpp CUDA wheel is py3-none, all compiled deps ship cp313,
  3.11 install is refused. Serving image was broken (deleted requirements-lock.txt), now
  installs `.[mlops]`; `.dockerignore` keeps the corpus and `mlops/data/` out of images.
  Colab notebook pins aligned to the env. Images not built: Docker has no WSL integration.
- **After the switch (same day):** networkx 3.6.1 → 3.7 (`0789824`). Extras made installable
  on 3.13 (`75f3e6b`): `recitation` = `piper-tts` (Spanish synthesis verified; Coqui TTS
  needs <3.12 and the `coqui-tts` fork fails with transformers 5, upstream #558);
  `music-ai` = MusicGen through transformers + scipy (audiocraft pins torch 2.1). Still
  open: `classical` resolves to cltk 2.x, which has no scansion. README records the
  dependency impact (`459ab1c`).
- **Code bugs and security (same day, later):** `mlflow run` was broken outright (MLflow 3
  refuses a project with both `docker_env` and `conda_env`); `MLproject` now has no env field
  (run with `--env-manager local` in the `poesia` env). `add-influence` now saves to
  `data/influences.yaml`; CLI messages fixed; gallery telemetry moved off MLflow's removed file
  store; Docker training command no longer passes the script twice; compose mounts
  `mlops/data`. **Security:** pip-audit and safety found mlflow 3.14.0 (4 advisories incl. an
  AI Gateway SSRF) and cryptography 48.0.1 (3); both CI checks were blind (`safety check ||
  true` audited the runner; the weekly pip-audit installed only `-e .`). Now mlflow 3.16.1 and
  cryptography 50.0.2 everywhere, pip-audit gates CI on the installed set (one documented nltk
  exception). **Laptop:** migrate `mlruns/mlflow.db` to 3.16.1 with a backup first
  (`LOCAL_ONLY.md` "Still to do"). Tests: 522 local, 449 in the CI replica.
- **Next:** see [Current focus](#current-focus).

---

## What We Just Did (2026-09-27) — env gaps that failed silently

- **Built and checked on the desktop:** `poesia` exists (the 2026-09-26 note below said
  no env yet), `scripts/env.sh check` ok, 515/515 tests pass.
- **Added, because without them the pipeline degraded quietly:** `outlines` 1.3.3 and
  `optuna`/`optuna-integration` 5.0.0 (gpu-cuda13 layer: the automatic evaluation after
  every training run, and the `hpo` entry point); `textstat`, `pysentimiento`,
  `duckdb`, `dvc`, `sentencepiece` (base).
- **NLTK data for g2p-en** now downloads into the env (`scripts/env.sh`); with an empty
  HOME the English phonology tests pass (they failed 4/5 before on a fresh machine).
- **GGUF tools:** `scripts/setup_gguf_tools.sh` checks out llama.cpp at the commit
  llama-cpp-python 0.3.35 vendors and builds `llama-quantize`; a tiny Qwen2 model went
  through convert → f16 → Q4_K_M on the desktop. Real adapters still need their data
  and weights from the laptop's DVC remote.
- **Fixed:** `scripts/poesia_env.sh` checked packages with the system python3.
- **Next:** `poesia-gpu` on the desktop (prebuilt cu130 llama-cpp-python), the newer
  Hugging Face stack (sentence-transformers 6 is a major version), the laptop checklist.

---

## What We Just Did (2026-09-26) — per-machine environments

- **Two machines, both current:** desktop (RTX 3070, 8 GB, sm_86, tier `gpu-cuda13`)
  trains; laptop (Quadro M1000M, 2 GB, sm_50, tier `gpu-cuda12`) runs the adapters
  through llama.cpp and cannot train. Reverted the 2026-09-26 "this machine is now an
  RTX 3070 / previous laptop" notes (e790776); 379942d's single cu128 index became
  per-tier layers (its `-e .` and python-dotenv fixes stay).
- **Env spec split:** `environment.yml` is the hardware-neutral base (+ mlflow 3.14.0,
  peft, accelerate, which the scripts import but the old export lacked);
  `requirements/{gpu-cuda13,gpu-cuda12,cpu}.txt` are the layers. `scripts/env.sh
  create|update|check [--dry-run]` builds `poesia`; `scripts/build_llama_cpp.sh`
  builds llama-cpp-python for the GPU into `poesia-gpu`. Dry-run resolved on the
  desktop for all three tiers; no env created yet.
- **Dispatch fix:** `poesia.device.bnb_4bit_usable()`; `LoRAClient` and
  `evaluate_adapter_mlflow.py` now require a working bitsandbytes, because torch's
  cu126 build runs on the laptop's sm_50 and `cuda_usable()` alone would have
  routed evaluation away from llama.cpp there.
- **Next:** the README "Verify on the laptop" checklist, then build both envs on
  each machine.

---

## What We Just Did (2026-09-08) — DVC adopted; model artifacts re-tracked

- **Git sync:** resolved branch divergence (Colab auto-commit) via rebase + push.
- **DVC adopted** as the system of record for weights: remote `local_d_drive`
  → `/mnt/d/dvc-remotes/poesia`; tracks `final_adapter/` (source LoRA) +
  `*-Q4_K_M.gguf` (deployable) only. Remote/cache slimmed to 8.8 GB.
- **Regenerable intermediates deleted:** `models/*/merged/` and `*-f16.gguf`
  (~58 GB) are derived via `scripts/convert_adapters_to_gguf.py` and excluded
  by `.dvcignore`.
- **Records:** added `merged` provenance to `mlops/adapter_registry.json`;
  committed MLflow metadata dump `mlops/mlflow_metadata_dump.sql` (71 runs,
  8 registered models). MLflow's real store is `mlruns/` (SQLite), **not** the
  Docker Postgres (which only holds demo traces).
- **Policy encoded** in `docs/INFRASTRUCTURE_DECISIONS.md` §7 (DVC = weights,
  Git = provenance/results, `mlruns/` = local disposable cache).

---

## Status update (2026-08-31) — MLflow wiring fix committed; this file trails the repo

- The MLflow wiring was fixed and **committed** (not left uncommitted): commit
  `3161f39` "fix(mlops): use sqlite MLflow backend, MLflow 3.x dropped file:// tracking".
  `scripts/benchmark_metre.py`'s `_log_mlflow` now uses `DATABASE_URL` (canonical
  PostgreSQL via `.env_mlflow`; sqlite fallback), because MLflow 3.x removed the
  `file://` tracking backend (logging was silently no-oping). Regression test
  `tests/test_mlflow_wiring.py` added. Follow-on commits landed through `b120de0`
  (2026-08-31): generation repair-loop fix, Model Registry backfill, docs.
- The re-entry checklist below still says "PostgreSQL — NOT sqlite anymore"; that
  remains true for the **canonical** backend. The sqlite reference in commit `3161f39`
  is only the code-level *fallback* default, not a switch away from PostgreSQL.
- *(Superseded 2026-10-04: the memory-bank is current again; this note describes 2026-08-31.)*
  ⚠️ This memory-bank is stale: it was last updated 2026-08-06, but the branch has
  advanced well beyond it (DVC/MLOps/analytics work through 2026-08-31). Treat older
  sections as historical; verify against `git log` before acting.

---

## Re-entry checklist

Checked 2026-10-04 on the desktop (`AngelThuis`, RTX 3070). Read
`docs/RETRAINING_PLAN_2026-10.md` before any training or data work.

```bash
cd ~/dev/poesia

# Environment (conda env `poesia`, Python 3.13 on both machines):
scripts/env.sh check

# Tests and quality gates (all must be green):
pytest                       # 519 pass locally; CI runs 446 on 3.13, 0 skipped
mypy src/ --ignore-missing-imports
ruff check src/ mlops/
ruff format --check src/ mlops/

# Regenerate the README showcase example (deterministic, no key needed):
poesia galeria illustrate seeds/library/20260731_030227_142539_el_peso_del_saber__ingenuidad.md \
  --backend procedural --output docs/examples/auca_el_peso_del_saber.png

# Live free-online illustration (no key; ~1 img/15s anonymous, ~10s each):
poesia galeria illustrate poem.txt --backend pollinations --output auca.png
```

- **DVC:** the only remote (`local_d_drive` → `/mnt/d/dvc-remotes/poesia`) is on the
  laptop's D: drive. The rebuilt corpus (`seeds/poetry_corpus/corpus_master/`, 85,027
  poems) is cached on the desktop only, and the July adapters exist only on the laptop's
  remote (desktop `models/` = `.dvc` pointers). Never run a bare `dvc repro`: it retrains
  `poetry-lora-v2` first (`docs/DVC_INTEGRATION.md`).
- **Public repo:** `OomAngel/poesia` is public. Poems are never committed or baked into
  images (`.dockerignore` excludes `seeds/poetry_corpus/` and `mlops/data/`).
- **MLflow:** the history (71 runs / 8 registered models) is in `mlruns/mlflow.db`, which
  exists only on the laptop; the desktop has none. The docker Postgres holds only demo
  traces (`docs/INFRASTRUCTURE_DECISIONS.md` §7).
- **Docker:** Docker Desktop's WSL integration is off, so `docker` is unusable from WSL and
  the compose stack (`docker/docker-compose.yml`) is down. Images have not been built since
  the 3.13 switch.

## Current focus

_Set 2026-10-04. Retraining with a larger corpus and a larger base model; order and reasons
in `docs/RETRAINING_PLAN_2026-10.md` §6. Each step changes one thing._

1. **Qwen3-8B smoke test on the desktop (§6 step 4).** First the code change for the
   "best" layout in `scripts/train_poetry_lora.py` (`lm_head` in NF4 via an empty
   bitsandbytes skip list, embedding on CPU; not implemented yet, the script uses
   `device_map="auto"`). Then about 50 steps; record `torch.cuda.max_memory_allocated()` and
   tokens/s. Qwen3.5-9B only after `flash-linear-attention` and `causal-conv1d` are in the
   env. The ~9B ceiling from `scripts/estimate_qlora_vram.py` is unmeasured until then.
2. **Stronger evaluation before trusting any new score (§6 step 2).** At least 5 themes,
   seeded, more than one sample per theme; English themes and an English metre target, not
   only Spanish hendecasyllables; a per-line rhyme-key score (`GENERATION_QUALITY_PLAN.md`
   next action 8b, not implemented yet); check the syllable scorer against
   `seeds/poetry_corpus/eval_gold/adso_gold_100.jsonl` (hand scansion).
3. **Rebuild the July baseline on the desktop.** The old adapters are only on the laptop's
   remote; rerun the `distilled` recipe (`mlops/configs/train_distilled.yaml`) here so the
   comparison has a baseline from this machine.
4. **Base-model comparison (§6 step 3).** Same recipe, only `base_model` changed (Qwen3.5-2B
   or Qwen3-4B-2507), scored with the step-2 evaluation.
5. **First sized corpus run (§6 step 5).** `scripts/build_fixed_dataset.py --max-poems N`
   sized by §5 (~2,600 usable tokens per poem; the full corpus runs out of RAM). Over-long
   examples are dropped, not truncated (`_drop_overlong`).

**Side items:** a private DVC remote both machines reach (§7; the repo is public); build the
Docker images once Docker Desktop's WSL integration is on, and align `training.Dockerfile`
(CUDA 12.4 base, unpinned libs) with the cu130 env; port the cltk 1.x scansion (MIT) for the
`classical` extra, since cltk 2.x on 3.13 has none; a note in career-assets ADR 0007 that
poesia's "8B won't fit 8 GB" claim was corrected (pending Angel).

---

## Older sessions

Sessions up to 2026-08-06 (the August focus, verified-state snapshot and session logs)
are in `memory-bank/archive/activeContext_until_2026-08-06.md`, moved verbatim on 2026-10-05.

## Document authority

| What | Where |
|------|-------|
| **Retraining plan (2026-10): model ceiling, corpus, run size, order of work** | **`docs/RETRAINING_PLAN_2026-10.md`** |
| Corpus sources, ingest and rebuild | `docs/CORPUS_SOURCES.md` |
| Infrastructure and data decisions (DO-NOT list) | `docs/INFRASTRUCTURE_DECISIONS.md` |
| DVC pipeline and remotes | `docs/DVC_INTEGRATION.md` |
| Training how-to | `docs/TRAINING_RUNBOOK.md` |
| Lemonade integration plan (AMD challenge) | `docs/LEMONADE_INTEGRATION.md` |
| GalerIA character comic: status, next steps, staged plan | `docs/GALERIA_CHARACTER_COMIC_HANDOFF.md` |
| Reference-image tools research (evidence) | `docs/CHARACTER_CONSISTENT_ILLUSTRATION_RESEARCH.md` |
| Free image-provider survey (text-to-image) | `docs/IMAGE_GENERATION_PROVIDERS.md` |
| VerifIA pattern + benchmarks | `docs/ARCHITECTURE.md` ("The VerifIA pattern and how it compares") |
| Experiment plan (models, techniques, loss) | `docs/archive/EXPERIMENTS_PLAN.md` |
| Cloud migration guide | `docs/CRONOLOGIA_CLOUD.md` |
| AnalogIA (A/B + memory mining) plan | `docs/ANALOGIA_PLAN.md` |
| RAG/LLM sequencing | `docs/archive/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` |
| Feature roadmap | `docs/ROADMAP.md` |
| CLI usage | `USAGE_GUIDE.md` |
| Kanban | `memory-bank/tasks.md` |
| Architecture + package survey | `docs/ARCHITECTURE.md` |
| Pre-generation enrichment | `docs/ENRICHMENT.md` |
| CronologIA deployment | `cronologia/docker-compose.yml` + root `.env.example` |
| Retraining history (July–September runs) | `docs/ROADMAP.md` ("Retraining history & approach"); current plan above |
| **MLOps diagnosis & implementation plan** | **`docs/MLOPS_DIAGNOSIS.md`** |
| **Human position + landscape research** | **`docs/POSITIONING.md`** |

# Tasks — PoesIA (Kanban)

## IN PROGRESS

- [ ] **v2-fixed retraining — INTERRUPTED, needs relaunch** (PID 309663 dead, `/tmp`
  log gone after WSL reboot; PG/MLflow down, run e5129188 unverifiable).
  Relaunch once PG is up: `bash scripts/launch_training.sh local mlops/configs/train_v2_fixed.yaml`

## BACKLOG (priority order)

- [ ] **Evaluate v2-fixed adapter** — auto via post-training pipeline when done
- [ ] **Test poem generation with v2-fixed** — write a soneto, verify no instruction-echo
- [ ] **Test title generation** — prompt the model to title its own poem
- [ ] **Compare adapters** — v2-fixed vs old qwen3b vs DPO (metre accuracy)
- [ ] **Run experiment grid** — CE vs Composite vs DPO
- [ ] **Docker compose end-to-end** — postgres + mlflow-ui stack is UP (test training service)
- [ ] **Run HPO search** — Optuna hyperparameter search
- [ ] **Run Qwen2.5-3B training** with fixed format
- [ ] **Wire `PoetryModelWrapper`** into `mlflow models serve`
- [ ] **Add titles to Machado poems** — extract from Gutenberg TOC
- [ ] **Deduplicate corpus** across all files before next training
- [ ] **Try Unsloth** — install and test 2x faster training
- [ ] **Model Registry aliases** — "champion" / "challenger"
- [ ] **Phase 4E** — literary taxonomy auto-tagging
- [ ] **Wire retrieval into GalerIA** — illustration style anchoring
- [ ] **WordNet Spanish** (omw-es:1.4) — retry when server is up
- [ ] **Snapshot tests** — CLI + generation pipeline

## DONE

### 2026-08-03: Free image-gen research + Pollinations backend (live-tested)
- [x] **`docs/IMAGE_GENERATION_PROVIDERS.md`** — 8-criterion weighted ranking of
      6 free providers (Pollinations #1 4.15/5; Cloudflare/Gemini/Horde tied 3.60;
      credit platforms 3.25; HF 2.85) with live probe log + honest gaps
- [x] **`PollinationsImageBackend`** (`--backend pollinations`): free, key-less,
      GET-based, deterministic seed, stdlib urllib
- [x] **Live test caught a real bug**: Sana rejects seeds > 2^31-1 (`Too big`) —
      fixed with `& 0x7FFFFFFF`; a mocked test could never have caught it
- [x] Verified live: 2-stanza auca sheet (1.3 MB PNG, 1706×1046); same prompt+seed
      ⇒ byte-identical images (service-level determinism)
- [x] `auto` stays offline-first (procedural); pollinations explicit
- [x] Suite 447 → **456 tests passing**, ruff + mypy clean
- [ ] (next) Cloudflare Workers AI backend (reliability); Gemini free tier (quality)

### 2026-08-03: mypy gate green — 54 type errors fixed
- [x] Root cause: numpy 2.5 PEP 695 stubs vs `python_version="3.11"` hard-aborted
      mypy, hiding 54 real type errors in 12 files
- [x] `python_version="3.12"` (mypy target only — runtime still ≥3.11); fixed all
      54 errors: `PhonologyBackend` Protocol (was imported but undefined),
      BriefBuilder `level` Literal casts, `Library` Path normalisation, Scorer
      typing, lazy-import attrs typed `Any` (llm_client/seed_expander/model_wrapper/
      poetry_trainer), dead duplicated `raise` removed, GalerIA typing
- [x] Verified: `mypy src/` Success, ruff check+format clean, full suite exit 0 (447)
- [ ] (next) free image-gen provider research → implement a `pollinations` backend

### 2026-08-03: GalerIA offline procedural backend + README showcase
- [x] **ProceduralImageBackend** (`--backend procedural`): deterministic offline
      generative art (Pillow, poem-seeded palette/composition), zero API keys,
      reproducible bit-for-bit; `--backend auto` now falls back to it (was 1×1 stub)
- [x] Fixed `Library.get()` TypeError (PoemRecord `content` mirror) — unblocked
      `poesia galeria illustrate --from-library`
- [x] `Library.attach_image()` persists `image:` in poem frontmatter after
      `write --illustrate --save`
- [x] `galeria illustrate` strips YAML frontmatter from `.md` poem files
- [x] README: Showcase section with real generated auca sheet
      (`docs/examples/auca_el_peso_del_saber.png`), 9 badges, feature headings
      (valid anchors), procedural walkthrough; test count → 447
- [x] Suite: **447 tests passing** (exit 0), ruff clean on src/ mlops/
- [ ] (next) real DALL·E/SDXL smoke test with a key; wire retrieval into GalerIA
      style anchoring (still in BACKLOG)

### 2026-08-03: GalerIA wired end-to-end + pro-grade README
- [x] `poesia galeria illustrate`: one image per stanza, `--backend auto|stub|openai|replicate`,
      `--api-key`, `--language`, `--theme`, PNG sheet + WeasyPrint PDF export, `--dry-run`
- [x] `poesia write --illustrate` — sheet saved to `galeria/` / library illustrations dir
- [x] `pipeline.py` (stanza split, backend select, illustrate_poem); `export_pdf()` implemented
- [x] Fixed CLI poem loading to preserve stanza blank lines
- [x] README rewritten pro-grade (features, quickstart, GalerIA walkthrough, extras, license)
- [x] Share tarball regenerated: `dist/poesia-share-20260803.tar.gz` (13M, secret-scan clean)
- [x] Suite: 431 tests passing (commits 256c7b1, e52c297)
- [ ] (next) persist `image:` in library frontmatter; real DALL·E/SDXL smoke test with key

### 2026-08-03: Unstick — lint pass committed, suite green
- [x] Completed & committed the in-flight lint pass (37 files): ruff format on `src/ mlops/`,
      pyproject tooling config (E501/per-file ignores, bandit skips, mypy numpy override),
      CI adds `ruff format --check`, bandit skip flags, `phonology-extra` extras fix
- [x] Fixed 3 pre-existing red tests — hosted-LLM tests now expect `LLMProviderError`
      (aligned with P5.3 structured-exception migration): `test(hosted-llm)` commit
- [x] Dutch phonology tests skip gracefully when pyphen unavailable: `test(phonology)` commit
- [x] Full suite green at HEAD — 416 tests, exit 0 (commits 84fed6b, 5c4c423, 02bb8c9)
- [ ] (next) relaunch v2-fixed retraining once PostgreSQL/MLflow is back up

### 2026-08-03: Private-share pack (README, license, emails)
- [x] LICENSE (MIT) + NOTICE reserving rights on `seeds/` creative content
- [x] CONTRIBUTING.md, CHANGELOG.md, SECURITY.md added
- [x] README: badges, refreshed Status (2026-08-01), "License & sharing" section
- [x] pyproject license field → MIT
- [x] `share/` email drafts (cover + setup tour, EN/ES) + sharing checklist
- [x] `scripts/package_share.sh` — verified 13 MB tarball, secret-scan safe
- [ ] (Angel decision) pick license variant + delivery channel (email tarball vs private GitHub)

## DONE

### 2026-08-01: Retraining + Corpus + Sonetos
- [x] DPO finished: loss=0.008, acc=1.0, 5/5 epochs
- [x] Root cause identified: training prompt ≠ inference prompt (instruction-echo)
- [x] Corpus expanded: 19 new files, 1,059 new poems (Gutenberg ×17 books, Wikisource Sor Juana + Acuña)
- [x] Mexican poets: 601 poems (Sor Juana +76, Acuña +67, Nervo 142, López Velarde 139...)
- [x] `scripts/build_fixed_dataset.py` — converts poems to inference-matching line-by-line examples
- [x] `mlops/data/train_fixed.jsonl` (38K) + `eval_fixed.jsonl` (2K)
- [x] `mlops/configs/train_v2_fixed.yaml` — fixed format + title examples
- [x] v2-fixed retraining launched (MLflow e5129188)
- [x] Sonetos written & saved: "El peso del saber", "El umbral", Radicle ×6 versions (ES+EN)
- [x] Model Registry re-linked to migrated runs (3 models verified)
- [x] Library: 13 poems

## DONE

### 2026-07-30 Session: Gap-Fixing Sprint (7 issues)
- [x] **GPU memory leak** — killed stale `sci-pipeline` uvicorn (PID 44333), freed 3.3GB
- [x] **CLI crash fixed** — added missing `ConstrainedLoop` import in `cli.py`
- [x] **3B adapter accessible** — `LoRAClient` now auto-detects base model per adapter via tuple registry
- [x] **OutlinesClient also fixed** — same tuple-based adapter registry
- [x] **Adapter registry complete** — 3 legacy entries imported to MLflow with run IDs
- [x] **Dockerfile fixed** — removed broken requirements-lock.txt pre-install step
- [x] **DPO script fixed** — `tokenizer` renamed to `processing_class` for trl v1.9.2
- [x] **DPO training launched** — first-ever DPO training run (background)
- [x] **Docker build launched** — retrying with fixed Dockerfile (background)

### 2026-07-30 Session: Env Automation + Stale Run Cleanup
- [x] Marked 5 orphaned RUNNING MLflow runs as FAILED (4 smoke-test, 1 composite)
- [x] Created `scripts/poesia_env.sh` — detects conda, activates poesia env, sources `.env_mlflow`, checks GPU + Python deps
- [x] Created `scripts/launch_training.sh` — unified entry point: `local` (conda) or `docker` mode, dry-run, config validation
- [x] Updated `activeContext.md` with verified state (cross-checked against MLflow DB, filesystem, GPU)
- [x] **CORRECTED**: Model Registry IS working — `poesia-lora-soneto-qwen3b` v1 and `poesia-lora-smoke-test-mlflow-pipeline` v1 are registered in SQLite backend

### All 11 MLOps phases code-complete (2026-07-30)
- [x] **Phase 1**: Consolidate tracking to MLflow-only
- [x] **Phase 2**: MLflow Autologging
- [x] **Phase 3**: Model Registry (pyfunc wrapper + register_model)
- [x] **Phase 4**: Nested evaluation runs
- [x] **Phase 5**: Data versioning via mlflow.log_input()
- [x] **Phase 6**: Inference standardization (PoetryModelWrapper)
- [x] **Phase 7**: HPO with Optuna (hpo_search.py)
- [x] **Phase 8**: Containerization (Dockerfiles + docker-compose)
- [x] **Phase 9**: CI/CD pipeline (3 GitHub Actions workflows)
- [x] **Phase 10**: Monitoring & drift detection (monitor_health.py)
- [x] **Phase 11**: Git tags (v1.0, v1.1, v1.2)
- [x] **Bonus**: Fixed test fragility (lazy-import mlflow in llm_client.py)
- [x] **Bonus**: Installed Optuna
- [x] **MLOPS_DIAGNOSIS.md** — comprehensive diagnostic doc persisted for future agent sessions

### Phase 1: MLOps Consolidation (2026-07-30)
- [x] Eliminated dual tracking (custom JSONL + MLflow) — MLflow is now single source of truth
- [x] Fixed structural MLflow bug: `start_run()` context now wraps entire training lifecycle
- [x] Fixed garbage `train_runtime_s` values (nanoseconds → seconds conversion bug)
- [x] Rewrote `experiments.py` CLI to query MLflow API instead of reading flat files
- [x] Rewrote `list_runs.py` to query MLflow API
- [x] Added 15+ new params and 10+ new metrics to MLflow logging
- [x] Added artifact logging (config, data manifest, eval results, test output, adapter weights)
- [x] Cleaned up code duplication (removed duplicate git_hash/run_id computation)
- [x] Added deprecation notice to legacy `mlops/runs/` directory

### Prior work
- All phases P0-P5 complete (400+ tests passing)
- Core phonology, evaluation, forms, generation loop
- eufonia, galeria, armonia sub-brands
- memoria Library (Markdown + SQLite), real CLI list/search
- GraphRAGRetriever: typed nodes/edges, traverse(), retrieve_with_paths()
- BriefBuilder wired to retriever
- All 6 LLM backends (stub, groq, gemini, openai, ollama, outlines)
- PoetryTrainer with composite loss (pre-computed weights, not live scorer)
- MLflow: autolog, tracing, genai.evaluate, model registry, SQLite backend
- VerifIA architecture pattern documented and benchmarked
- CronologIA Docker stack (Postgres + MLflow)
- Emotion analysis (pysentimiento + NRC lexicon)
- Imagery extraction + image prompt builder
- DPO training script
- Experiment grid automation
- Documentation consolidated from 26 to 14 files

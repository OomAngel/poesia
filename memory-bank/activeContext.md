# Active Context — PoesIA

_Last updated: 2026-08-03 (Session: unstick — lint pass + LLMProviderError test fixes, suite green)_

---

## Re-entry checklist

```bash
cd /home/angel/dev/poesia

# Launch training (activates env + sources .env_mlflow automatically):
bash scripts/launch_training.sh local mlops/configs/train_smoke.yaml --dry-run

# Check v2-fixed retraining progress:
tail -f /tmp/train_v2_fixed.log

# Quick MLflow sanity (PostgreSQL — NOT sqlite anymore):
source scripts/poesia_env.sh --source 2>/dev/null
/home/angel/miniconda3/envs/poesia/bin/python -c "
import mlflow; mlflow.set_tracking_uri('postgresql://mlflow:mlflow@localhost:5432/mlflow');
from mlflow.tracking import MlflowClient; c = MlflowClient();
for e in c.search_experiments():
    runs = c.search_runs([e.experiment_id])
    statuses = {}
    for r in runs: statuses[r.info.status] = statuses.get(r.info.status, 0) + 1
    print(f'{e.name:30s} {statuses}')" 2>/dev/null

# MLflow UI (Docker): http://localhost:5000
# PostgreSQL: mlflow:mlflow@localhost:5432/mlflow
```

## Current focus

**Working tree is GREEN (2026-08-03, 431 tests)** — lint pass + test fixes committed,
then **GalerIA wired end-to-end** and a **pro-grade README** written. Repo is
share-ready: `dist/poesia-share-20260803.tar.gz` regenerated.

GalerIA status:
- ✅ `poesia galeria illustrate` — one image per stanza, `--backend auto|stub|openai|replicate`,
  `--api-key`, `--language`, `--theme`, PNG sheet + WeasyPrint PDF export, `--dry-run`
- ✅ `poesia write --illustrate` — sheet saved to `galeria/` (or `~/.poesia/poems/illustrations/<id>.png` when saved)
- ⏭️ Next: persist `image:` path in library frontmatter; Wire retrieval into GalerIA
  (style anchoring from retrieval — partially done via influences); real DALL·E/SDXL
  smoke test with a key

⚠️ **v2-fixed retraining INTERRUPTED** — PID 309663 no longer running, `/tmp/train_v2_fixed.log`
gone (WSL reboot cleared `/tmp`). PostgreSQL/MLflow is DOWN (port 5432 refused; Docker not
available in this WSL distro), so run e5129188's final state is unverifiable.
**Needs relaunch once PG is up**:
`bash scripts/launch_training.sh local mlops/configs/train_v2_fixed.yaml`

The training plan itself (when relaunched):
- 38K line-by-line examples matching the inference prompt EXACTLY
- 1 epoch ≈ 4,750 steps ≈ ~2h on RTX 2000 Ada
- Adds title-generation examples (983 in full dataset)
- Post-training pipeline auto-runs: evaluate → register → migrate to PG

### What led here (session timeline)
1. DPO finished: loss=0.008, acc=1.0 — but adapters still echoed instructions
2. Root cause: training prompt format ≠ inference prompt format
3. Corpus expanded: **19 new files, 1,059 new poems** (Gutenberg + Wikisource)
4. Fixed-format dataset builder: `scripts/build_fixed_dataset.py` → `mlops/data/train_fixed.jsonl` (38K) + eval (2K)
5. Mexican poets: 601 poems (Sor Juana +76, Acuña +67, Nervo 142, López Velarde 139, Gutiérrez Nájera 52, Sabines 38, Paz 32...)
6. Hand-written sonetos: "El peso del saber", "El umbral", 6 RadicleCrops versions (ES×4 + EN×1 + fresh ES×1)

### Library state: 13 poems (El peso del saber, El umbral, Radicle ×6, + 5 earlier)

## Verified State (cross-checked against filesystem + MLflow DB + GPU)

### ✅ ACTUALLY Working
| Component | Status | Evidence |
|-----------|--------|----------|
| MLflow tracking | ✅ | 20+ runs across 8 experiments |
| Training script (MLflow-only) | ✅ | Full lifecycle in `start_run()`, no JSONL |
| Model Registry | ✅ | 2 models + 3 legacy imported |
| Autologging | ✅ | `mlflow.transformers.autolog()` |
| Data versioning | ✅ | `mlflow.log_input()` |
| Evaluation (nested runs) | ✅ | `--parent-run-id` support |
| LoRAClient 3B support | ✅ | Auto-detects base model per adapter |
| OutlinesClient 3B support | ✅ | Same tuple-based adapter registry |
| MLflowModelClient | ✅ | New backend: `--llm mlflow` |
| Adapter registry | ✅ | 5/5 entries with full mlflow_run_id |
| Docker image | ✅ | `poesia-train:latest` (4.39GB) |
| DPO training | 🏃 | 2100/5625 steps, ~55min remaining |
| CLI (stub + lora + 9 backends) | ✅ | 9 registered backends |
| Tests | ✅ | 16/16 key tests pass |

### 🟡 Still To Validate / Requires Action
- **`PoetryModelWrapper.predict()`** — now wired via `MLflowModelClient` CLI backend
- **Docker compose** — image built, end-to-end stack (postgres + mlflow-ui + training) not tested
- **GitHub Actions** — workflows exist, need GitHub repo + secrets
- **Experiment grid** — CE vs Composite vs DPO comparison (blocked on DPO finishing)

### 🏃 Current Background Jobs
| Job | PID | Progress | Log |
|-----|-----|----------|-----|
| DPO training | 90646 | ~2100/5625 steps (~37%) | `tail -f /tmp/dpo_training.log` |
| Docker image | — | ✅ Built: `poesia-train:latest` | — |

## Known Issues — Inference Quality

Both fine-tuned adapters (qwen3b CE and DPO) produce instruction-echo instead of poetry lines.
Root cause: training data prompt format differs from inference prompt format.
- **Immediate fix applied**: Post-processing in `LoRAClient.generate()` strips instruction lines, keeps longest valid poetry line
- **Permanent fix**: Retrain with properly formatted data (see `docs/LITERARY_TAXONOMY.md`)

## Retraining Plan — Adequate Titles & Fix Inference

### Data Format Fix
Current training data format:
```
prompt: "Write line 1. Exactly 11 syllables. End with..."
completion: "verso real"
```
Problem: model learns to output the constraint instructions.

Fixed format:
```
prompt: "You are a poet. Write a single Spanish hendecasyllable verse about: {theme}\nPrior lines: {lines}\nWrite line {n}."
completion: "verso real"
```
This matches the inference prompt structure. Add `"Output ONLY the single verse line."` to BOTH training and inference.

### Title Generation
Add a `title` field to training data. Train or prompt:
- CE adapter: include title in the prompt format
- DPO adapter: include title completion as part of the reward
- Post-generation: use a hosted LLM (Groq/Gemini) to generate titles based on poem content

### Next Training Config
1. Fix training data format → `mlops/configs/train_v2_fixed.yaml`
2. Train on 1000 sonetos with corrected prompt format
3. Add title to training data → evaluate title quality
4. Run DPO on corrected data
5. Evaluate: poem quality (subjective) + metre accuracy + title relevance
| 5 | **Adapter registry incomplete** — 3 legacy entries missing `mlflow_run_id` and `mlflow_model_name` | Imported into `legacy-training-imports` experiment, registry now has 5/5 entries with full provenance |
| 6 | **Docker build broken** (requirements-lock.txt has host absolute paths + Python 3.13 pins) | Removed `-e /home/angel/dev/poesia` from lock file, rewrote Dockerfile to skip lock file and install from pyproject.toml directly |
| 7 | **DPO script broken** (trl v1.9.2 renamed `tokenizer` → `processing_class`) | Fixed `DPOTrainer(tokenizer=...)` → `processing_class=tokenizer` |

### 🏃 Currently Running (background)

| Job | PID | Started | Status |
|-----|-----|---------|--------|
| Docker build (retry) | 67159 | 2026-07-31 00:48 | Building — check `/tmp/docker_build3.log` |
| DPO training | 64704 | 2026-07-31 00:46 | Loading model — check `/tmp/dpo_training.log` |

## What We Just Did (this sub-session)

### Phase 10: Monitoring & Drift Detection 📈 (DONE)
- `scripts/monitor_health.py` — evaluates latest production model, compares to historical baseline, detects drift
- Two alert levels: threshold breach (hard limit exceeded) and statistical drift (>2σ from historical mean)
- Logs to `poesia-monitoring` MLflow experiment; exit code 1 on threshold breach
- Supports `--dry-run`, `--model-uri`, custom thresholds, configurable lookback window
- Scheduled weekly run added to CI/CD (`cron: 0 6 * * 1`)
- Resolves model automatically: Production → Staging → latest run

### Test Fragility Fix 🧪 (DONE)
- `src/poesia/generation/llm_client.py` now lazy-imports `mlflow` via `try/except ImportError`
- When mlflow is absent, `@mlflow.trace()` becomes a no-op decorator
- The 9 tests that errored without mlflow will now pass cleanly

### Full File Inventory After This Session
```
NEW  docker/training.Dockerfile
NEW  docker/serving.Dockerfile
NEW  docker/docker-compose.yml
NEW  docker/.dockerignore
NEW  .github/workflows/ci.yml
NEW  .github/workflows/train.yml
NEW  .github/workflows/deploy.yml
NEW  src/poesia/training/model_wrapper.py
NEW  scripts/hpo_search.py
NEW  scripts/monitor_health.py
NEW  docs/MLOPS_DIAGNOSIS.md
NEW  mlops/configs/train_ruli.yaml
NEW  mlops/runs/README.md
MOD  scripts/train_poetry_lora.py
MOD  scripts/evaluate_adapter_mlflow.py
MOD  src/poesia/generation/llm_client.py
MOD  mlops/experiments.py
MOD  mlops/list_runs.py
```

## What We Just Did (2026-08-03: Private-share pack — README, license, emails)

Prepared the repo to be shared with a single contact by email:

- **License**: MIT (`LICENSE`) + `NOTICE` reserving rights on original creative
  content (`seeds/angel_fragments/`, `seeds/library/`); pyproject updated from
  "Proprietary - personal project" to MIT.
- **Proper-repo files**: `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`, README
  badges + refreshed Status (2026-08-01) + new "License & sharing" section.
- **Share kit**: `share/EMAIL_01_COVER.md` (EN+ES), `share/EMAIL_02_SETUP_TOUR.md`,
  `share/SHARING_CHECKLIST.md`, and `scripts/package_share.sh` → verified
  `dist/poesia-share-*.tar.gz` (13 MB, fits in one email; secret-scan abort).

**Open decisions for Angel**: (1) license variant — MIT+NOTICE (implemented),
plain MIT, or All-Rights-Reserved; (2) delivery channel — email tarball ✅ vs
private GitHub repo ⚠️ (needs explicit instruction per AGENTS.md).

## What We Just Did (2026-08-03: GalerIA wired end-to-end + pro-grade README)

**GalerIA produces images that go with the poems:**
- New `src/poesia/galeria/pipeline.py`: stanza splitting (blank-line + chunking),
  backend selection (`auto|stub|openai|replicate`), `illustrate_poem()` →
  one `AucaPanel` per stanza with imagery-derived prompts.
- `auca.py` `export_pdf()` implemented (WeasyPrint, lazy import, actionable error).
- CLI `galeria illustrate`: real backends + `--api-key`/`--language`/`--theme`,
  PNG sheet output (`.pdf` by extension), `--dry-run` shows per-panel prompts,
  MLflow best-effort logging. **Fixed**: poem loading now preserves interior blank
  lines so stanzas split correctly.
- `poesia write --illustrate`: generates a sheet next to the poem (offline stub by
  default via `auto`).
- 15 new tests (`tests/test_galeria_pipeline.py`); suite now 431, green.

**Pro-grade README**: rewritten from scratch — hero pitch, features, extras table,
quickstart with real commands, GalerIA walkthrough, architecture, language support,
development, status, license. Test-count badge updated.

**Share-ready**: `dist/poesia-share-20260803.tar.gz` regenerated (13M, secret-scan clean).

Commits: `256c7b1` feat(galeria) · `e52c297` docs(readme).

## What We Just Did (2026-08-03: Unstick — lint pass + structured-exception tests)

Resumed a session that had stalled with 41 uncommitted files and a red test suite:

1. **Diagnosed the stuck state**: 38-file lint pass (ruff format on `src/ mlops/`, bandit
   skips, mypy numpy override, CI updates) was complete but uncommitted; the suite was red
   because `HostedLLMClient` raises `LLMProviderError` (since P5.3, commit 33c3724) while
   3 mock tests still expected `RuntimeError`.
2. **Fixed the red tests** (commits `84fed6b`, `5c4c423`): hosted-LLM tests now expect
   `LLMProviderError` (matching `test_ollama_client`/`test_generation_llm_client`, which
   were already migrated); Dutch phonology tests skip gracefully without pyphen.
3. **Committed the lint pass** (commit `02bb8c9`, 37 files) — `ruff check`/`format` clean
   on `src/ mlops/`, matching the CI gates added in the same commit.
4. **Verified green**: full suite 416 tests, exit code 0 (run detached via `setsid`).

Environment notes: PostgreSQL/MLflow DOWN, Docker not available in this WSL distro,
v2-fixed retraining interrupted (see Current focus).

## What We Just Did (Phase 1: MLOps Consolidation)

### 1. Eliminated Dual Tracking 🏗️
- **Removed** all custom JSONL/JSON writes (`experiments.jsonl`, `{run_id}.json`) from `train_poetry_lora.py`
- **Rewrote** `experiments.py` CLI to query MLflow API instead of reading flat files
- **Rewrote** `list_runs.py` to query MLflow API
- Added deprecation notice at `mlops/runs/README.md`

### 2. Fixed the Structural MLflow Bug 🐛
The `mlflow.start_run()` context previously wrapped ONLY the param-logging section (lines 131-150) and **closed before training began**. All training, evaluation, and testing happened outside the MLflow run — that's why every historical run had params but ZERO metrics.

**Fixed**: The entire training lifecycle (params → training → save adapter → evaluate → test) now runs inside a single `with mlflow.start_run()` block.

### 3. Fixed Garbage Metrics 💩
`train_runtime_s` was storing nanosecond values as seconds (e.g., `8.07e15`). Replaced with `time.time()`-based `train_duration_seconds`.

### 4. Log More Params & Metrics to MLflow 🔧
Added 15+ new params (lr_scheduler, warmup_steps, weight_decay, quantization, loss_fn, lora_target_modules, data_sources, data_forms, etc.) and 10+ new metrics (eval_syllable_deviation, eval_line_count_accuracy, per-theme metrics, train_duration_seconds).

Also now logs: config YAML as artifact, data manifest as artifact, eval results as artifact, test generation as artifact, adapter weights via `log_artifacts()`.

### 5. Cleaned Up Duplication
Removed duplicate `git_hash` and `run_id` computation (was happening twice in the same function). Extracted shared helpers `_resolve_tracking_uri()` and `_capture_git_commit()`. Removed unused `import hashlib`.

### Available to run

| Command | What | Time |
|---------|------|------|
| `python scripts/train_poetry_lora.py mlops/configs/train_ruli.yaml` | Ruli-3B (Spanish-native) training | ~2h |
| `python scripts/train_poetry_lora.py mlops/configs/train_composite.yaml` | Composite loss on 500 scored sonetos | ~2h |
| `python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml` | DPO preference learning | ~1h |
| `python scripts/run_experiment_grid.py --grid loss_compare` | Compare CE vs Composite vs DPO | ~5h |

## Document authority

| What | Where |
|------|-------|
| VerifIA pattern + benchmarks | `docs/ARQUITECTURA.md` |
| Experiment plan (models, techniques, loss) | `docs/EXPERIMENTS_PLAN.md` |
| Cloud migration guide | `docs/CRONOLOGIA_CLOUD.md` |
| AnalogIA (A/B + memory mining) plan | `docs/ANALOGIA_PLAN.md` |
| RAG/LLM sequencing | `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` |
| Feature roadmap | `docs/ROADMAP.md` |
| CLI usage | `USAGE_GUIDE.md` |
| Kanban | `memory-bank/tasks.md` |
| Architecture + package survey | `docs/ARCHITECTURE.md` |
| Pre-generation enrichment | `docs/ENRICHMENT.md` |
| CronologIA deployment | `cronologia/docker-compose.yml` + `.env.example` |
| Retraining history | `docs/ROADMAP.md` (Retraining section) |
| **MLOps diagnosis & implementation plan** | **`docs/MLOPS_DIAGNOSIS.md`** |

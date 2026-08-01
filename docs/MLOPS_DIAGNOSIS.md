# PoesIA MLOps — Diagnostic & Implementation Roadmap

> **Status:** Active · **Last updated:** 2026-07-31 · **Authority:** Canonical MLOps reference
>
> This document records the comprehensive MLOps diagnosis performed 2026-07-30,
> the 11-phase implementation plan derived from it, and the model/technique
> inventory (tried vs. planned). It exists so that AI coding agents can operate
> autonomously on MLOps work without rediscovering these findings each session.

---

## 1. Diagnosis (17 gaps found)

### 🔴 Critical (blocking good MLOps) — All Resolved

| # | Gap | Detail | Resolution |
|---|-----|--------|------------|
| 1 | **Dual unsynchronized tracking** | Data written to MLflow *and* custom JSONL/JSON files | ✅ **Phase 1**: Removed JSONL writes. MLflow is single source of truth. Full lifecycle in `start_run()`. |
| 2 | **No Model Registry** | `mlruns/models/` empty. Only hand-written `adapter_registry.json`. | ✅ **Phase 3**: `mlflow.pyfunc.log_model(registered_model_name=...)` wired. 2 models registered (`poesia-lora-soneto-qwen3b` v1, `poesia-lora-smoke-test-mlflow-pipeline` v1). 3 legacy entries imported. |
| 3 | **Evaluation has no provenance** | Evaluation runs independent, no link to training run. | ✅ **Phase 4**: `evaluate_adapter_mlflow.py` accepts `--parent-run-id`. |
| 4 | **Metrics are half-logged** | Eval metrics only in JSONL, not MLflow. | ✅ **Phases 1+4**: All metrics go to MLflow. Eval metrics logged in same run. |
| 5 | **Artifact tracking absent** | `mlflow.log_artifact()` never called. Adapters orphaned. | ✅ **Phase 1+3**: Config, data manifest, eval results, adapter weights all logged as artifacts. |

### 🟡 Structural weaknesses — All Resolved (code), Some Need Validation

| # | Gap | Detail | Resolution |
|---|-----|--------|------------|
| 6 | **No MLflow autologging** | `mlflow.transformers.autolog()` not used. | ✅ **Phase 2**: `mlflow.transformers.autolog()` added to training script. |
| 7 | **Data versioning fragile** | SHA256 hashes exist but not in MLflow. | ✅ **Phase 5**: `mlflow.log_input()` called in training script. |
| 8 | **No CI/CD pipeline** | No `.github/` directory. | ✅ **Phase 9**: 3 GitHub Actions workflows created (ci, train, deploy). Need GitHub repo + secrets to activate. |
| 9 | **No HPO infrastructure** | `run_experiment_grid.py` only, no Optuna. | ✅ **Phase 7**: `scripts/hpo_search.py` with Optuna. |
| 10 | **No serving standardization** | LoRA adapters loaded via hardcoded paths. | ✅ **Phase 6**: `PoetryModelWrapper` as `mlflow.pyfunc.PythonModel`. New `MLflowModelClient` CLI backend (`--llm mlflow`). |
| 11 | **Not containerized** | No Dockerfile for training/serving. | ✅ **Phase 8**: `docker/training.Dockerfile`, `docker/serving.Dockerfile`, `docker/docker-compose.yml`. Image built: `poesia-train:latest` (4.39GB). |
| 12 | **No environment locking** | `environment.yml` incomplete. `requirements-lock.txt` has host-specific paths. | 🟡 Partially resolved: `requirements-lock.txt` cleaned of host paths. Dockerfile installs from pyproject.toml. Still needs `conda-lock` for full reproducibility. |
| 13 | **No monitoring/drift detection** | No quality degradation detection. | ✅ **Phase 10**: `scripts/monitor_health.py` with threshold breach + statistical drift. Schedule only activates on GitHub. |
| 14 | **Generation traces not linked to models** | MLflow Traces disconnected from adapters. | 🟡 Unchanged. Traces logged but not linked to model registry. |
| 15 | **No git tags or releases** | Zero git tags. | ✅ **Phase 11**: 3 annotated tags created (v1.0, v1.1, v1.2). |
| 16 | **Test fragility** | 9 tests error when mlflow absent. | ✅ **Phase 1 bonus**: `llm_client.py` lazy-imports mlflow. Tests pass without it. |
| 17 | **Experiment metadata schema ad-hoc** | JSONL schema inconsistent. | ✅ **Phase 1**: JSONL eliminated entirely. MLflow enforces consistent schema. |

---

## 2. Implementation Plan (11 phases)

Ordered by impact/dependency — each phase unblocks the next.

| Phase | Name | Effort | Impact | Dependencies | Status |
|-------|------|--------|--------|-------------|--------|
| **1** | **Consolidate tracking to MLflow-only** 🏗️ | Medium | Critical | None | ✅ **DONE** |
| 2 | Add MLflow Autologging 📊 | Small | High | Phase 1 | ✅ **DONE** |
| 3 | Log artifacts & register models 📦 | Medium | High | Phase 1-2 | ✅ **DONE** |
| 4 | Nest evaluation as child runs 🪆 | Small | Medium | Phase 1 | ✅ **DONE** |
| 5 | Data versioning in MLflow 🗂️ | Small | Medium | Phase 1 | ✅ **DONE** |
| 6 | Inference standardization 🚀 | Medium | Medium | Phase 3 | ✅ **DONE** |
| 7 | Hyperparameter optimization ⚙️ | Large | Medium | Phase 1-2 | ✅ **DONE** |
| 8 | Containerization & reproducibility 🐳 | Medium | Medium | None | ✅ **DONE** |
| 9 | CI/CD pipeline 🔄 | Large | Medium | Phase 6, 8 | ✅ **DONE** |
| 10 | Monitoring & observability 📈 | Medium | Low | Phase 3 | ✅ **DONE** |
| 11 | Git tags & release management 🏷️ | Small | Small | None | ✅ **DONE** |

### Phase 1 detail (completed 2026-07-30)

- Removed all `experiments.jsonl` and `{run_id}.json` writes from `train_poetry_lora.py`
- Fixed structural bug: `mlflow.start_run()` context now wraps entire training lifecycle
- Fixed garbage `train_runtime_s` (nanoseconds stored as seconds)
- Rewrote `mlops/experiments.py` CLI to query MLflow API
- Rewrote `mlops/list_runs.py` to query MLflow API
- Added 15+ new params & 10+ new metrics to MLflow logging
- Added artifact logging (config, data manifest, eval results, adapter weights)
- Cleaned up code duplication, added deprecation notice at `mlops/runs/README.md`

---

## 3. Model & Technique Inventory

### 3.1 LLM Models — Actually Tried

| Model | Use | Status |
|-------|-----|--------|
| `Qwen/Qwen2.5-1.5B-Instruct` | Fine-tuned (4 adapters) + Outlines inference | ✅ **Default, proven** |
| `gemini-2.5-flash` | Hosted generation backend | ✅ **Works** |
| `gpt-4o-mini` | Hosted generation backend | ✅ **Works** |
| Groq default (mixtral/llama3) | Hosted generation + distillation | ✅ **Works** |
| `gemma2:2b` | Local inference via Ollama | ✅ **Works** |

### 3.2 LLM Models — Documented "To Try" (never used)

| Model | Priority | Barrier |
|-------|----------|---------|
| **Qwen2.5-3B** (upgrade path) | ★★★★ | Config ready at `mlops/configs/train_qwen3b.yaml` |
| **Llama 3.2 3B** | ★★★ | None — one line in YAML config |
| **Gemma 2 2B** (fine-tune, not just inference) | ★★ | None — one line in YAML config |
| ~~**Ruli-3B**~~ | ❌ | **Does not exist on HuggingFace** — replaced by Qwen2.5-3B |
| **Llama 3.1 8B** | ★ | Impractical — won't fit 8GB VRAM |

### 3.3 Embedding Models — Actually Tried

| Model | Dims | Result |
|-------|------|--------|
| `intfloat/multilingual-e5-base` | 768 | Replaced after comparative eval |
| `intfloat/multilingual-e5-small` | 384 | **Won** — frozen canonical |
| `all-MiniLM-L6-v2` | 384 | Trialed, not selected |

### 3.4 Training Techniques — Actually Completed

| Technique | Config | Run ID |
|-----------|--------|--------|
| QLoRA r=16, CE loss, sonetos | `train_v1.yaml` | `20260728_231807` |
| QLoRA r=32, CE loss, multiform | `train_multiform.yaml` | `20260729_123255` |
| QLoRA r=32, CE loss, distilled data | `train_distilled.yaml` | `20260729_144938` |
| QLoRA r=16, composite loss, scored data | `train_composite.yaml` | `20260729_220002` (killed) |

### 3.5 Training Techniques — Documented "To Try" (never run)

| Technique | Config/Status | Why Not Done |
|-----------|--------------|-------------|
| **DPO** | `train_poetry_dpo.py` + `dpo_v1.yaml` exist | Never executed |
| **Unsloth** | Not installed | Not prioritized yet |
| **LoRA r=64** | One-line config change | Not prioritized yet |
| **LoRA all linear layers** | Add gate_proj, up_proj, down_proj | Not tested |
| **Multi-teacher distillation** | Ensemble Groq + Gemini outputs | Not implemented |
| **DSPy prompt optimization** | Not implemented | Not prioritized |
| **Knowledge distillation** | Not implemented | Not prioritized |
| **Synthetic data augmentation** | Not implemented | Not prioritized |

---

## 4. Current State & Next Work

### ✅ All 11 Phases Complete

All MLOps phases have been coded and most have been validated:
- **Phases 1-7, 11**: Code-complete AND validated (training runs executed, MLflow DB verified)
- **Phase 8**: Docker image built (`poesia-train:latest`, 4.39GB)
- **Phase 9**: GitHub Actions workflows exist — need GitHub repo + secrets to activate
- **Phase 10**: `monitor_health.py` exists — schedule only activates on GitHub

### 🏃 Currently Running

- **DPO training** — first-ever run, using `scripts/train_poetry_dpo.py` with `mlops/configs/dpo_v1.yaml`. ~2100/5625 steps (~37%), estimated ~55min remaining.

### 🎯 Next Execution Steps (priority order)

1. **Evaluate DPO adapter** — compare metrics vs CE baseline after training finishes
2. **Run experiment grid** — CE vs Composite vs DPO comparison
3. **Run Qwen2.5-3B training** — now that `LoRAClient` supports 3B, train with full MLOps pipeline
4. **Docker compose up** — verify postgres + mlflow-ui + training stack end-to-end
5. **Wire `PoetryModelWrapper`** into `mlflow models serve` for production inference
6. **HPO search** — Optuna hyperparameter search
7. **Unsloth** — install and test 2x faster training

---

## 5. External Review (2026-07-31)

> Cross-repository assessment performed during an mlops-lite evaluation (2026-07-31).
> These observations supplement — they do not replace — the Phase 1-11 plan above.

### 5.1 Strengths confirmed externally

| Dimension | Observation |
|-----------|-------------|
| **MLflow tracking integration** | Real, working MLflow integration with params/metrics per run — ahead of many hobbyist MLOps setups. The `experiments.py` query layer that replaces the legacy JSONL is the right consolidation direction. |
| **CI/CD completeness** | Three workflows (`ci.yml`, `train.yml`, `deploy.yml`) covering lint, test, security, GPU training, and model promotion — this is the most complete CI/CD among the three repos assessed. |
| **MLproject entry points** | Having `mlflow run . -e train` / `evaluate` / `dpo` / `hpo` / `pipeline` means the training pipeline is self-documenting and environment-agnostic. |
| **Docker containers** | Both `training.Dockerfile` and `serving.Dockerfile` exist and are wired into CI — containerization is ahead of the typical Phase 4-5 maturity level in this class of project. |
| **Adapter registry** | `adapter_registry.json` + MLflow model versions provides two layers of artifact tracking (file-system path + MLflow registry). |

### 5.2 Gaps visible from outside (beyond the internal 17)

These are observations an external reviewer would notice that aren't captured in the internal Phase 1-11 gaps:

1. **`.gitignore` excludes `mlruns/` but includes `models/` — inconsistent.** `models/` contains trained LoRA adapters (488 MB) that are checked into git history. Either `models/` should be gitignored with `dvc`/Git LFS, or `mlruns/` should be tracked for the same reason. Currently `models/` is tracked (large binaries) and `mlruns/` is not (small SQLite DB + metadata) — the opposite of what makes sense.

2. **`environment.yml` still references a local machine prefix** (`prefix: /home/angel/miniconda3/envs/poesia`). This is harmless for the current user but breaks `conda env create -f environment.yml` for anyone else. The prefix should be stripped (conda ignores it when creating a new env, but it's a readability signal that the env hasn't been exported for sharing).

3. **Dual CLI surfaces.** `poesia` (typer CLI via `pyproject.toml` scripts) and the ad-hoc `scripts/` invocation patterns coexist. Newcomers won't know which to use. The `poesia` CLI is discoverable (`poesia --help`); the scripts are not (`scripts/train_poetry_lora.py` requires reading the file). Consider migrating all training/eval workflows to the `poesia` CLI or `mlflow run` entry points.

4. **`train.yml` uses a self-hosted GPU runner** that isn't documented anywhere. If this runner goes down or changes, the entire CI training pipeline silently breaks. Document the runner's setup (or accept that GHA-based training is inherently fragile).

5. **No pre-commit hooks.** The CI catches issues after push, but there's no local gating. Adding a minimal `.pre-commit-config.yaml` (ruff, trailing-whitespace, check-yaml) would shift quality checking left.

### 5.3 Comparison context

Assessed alongside:
- **mlops-lite** (deep 5-tier design, zero operational infrastructure)
- **research-tools** (excellent pre-commit/CI engineering discipline, not an ML training repo)
- **career-assets** (highest engineering rigor: 20+ pre-commit hooks, strict mypy, import-linter, opengrep, complexity ratchet, sqlfluff, mutation testing)

PoesIA has the **most complete MLOps stack** among your repos, but the **least rigorous local quality gating** (no pre-commit, no mypy coverage of training scripts). The 17 internal gaps are the right list; the 5 above are the blind spots an external reviewer would notice immediately.

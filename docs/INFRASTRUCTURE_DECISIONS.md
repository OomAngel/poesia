# Infrastructure & Data Decisions — PoesIA

> **Status:** Authoritative. Read this **before** touching any infrastructure,
> data store, or model artifact. Last reviewed 2026-09-08 (DVC adopted + model-artifact policy revised — see §7).

## 1. The premise (read this first)

PoesIA is **today** a single-user Python CLI. It has a **long-term** intent to
become a multi-user **web / Android** product, but that product is **not yet
started** — there is no web/API code, no multi-user database, and no serving
backend in the repo.

This distinction is the root of every past misdiagnosis:

- Advice that assumes *"personal toy forever"* wrongly recommends **deleting**
  infrastructure (postgres, MLflow, model files).
- Advice that assumes *"the product already exists"* wrongly recommends
  **building** product infrastructure now (app DB, web backend).

The correct posture is a **staged transition**: keep what is cheap and already
working, and defer product-only infrastructure until the product build actually
starts.

## 2. Current state (verified 2026-09-08)

| Component | State |
|---|---|
| Application | Single-user Python CLI (`poesia write|scan|workshop|galeria|memoria|armonia`) |
| Web / API | **None** — no FastAPI/Flask/uvicorn in `src/` or `pyproject.toml`; only *outbound* LLM calls |
| Poem library (MemorIA) | Local Markdown + **SQLite** index (`~/.poesia/poems/`, `library.db`) |
| Experiment tracking | **MLflow** (docker `postgres` + `mlflow-ui` is the canonical backend; the actual 71 runs / 8 models live in local SQLite `mlruns/mlflow.db` — see §7) |
| Model artifacts | `models/` (~9 GB): `final_adapter/` + `*-Q4_K_M.gguf` tracked in DVC; `merged/` + `*-f16.gguf` regenerable, deleted (see §7) |
| DVC | **Adopted** (2026-09-08): remote `local_d_drive` → `/mnt/d/dvc-remotes/poesia`; tracks source + deployable only |
| Serving | `serving.Dockerfile` = `mlflow models serve` sketch only (not an app backend) |
| Local MLflow history | `mlruns/mlflow.db` (SQLite): 71 runs / 13 experiments, 8 registered models; dumped to `mlops/mlflow_metadata_dump.sql` in git |

## 3. Decisions

### Keep (do not remove)

- **PostgreSQL + MLflow (docker-compose).** Working and cheap. Keep for
  experiment tracking. Do **not** collapse MLflow back to SQLite.
- **DVC + remote (adopted 2026-09-08).** DVC is the system of record for model
  weights: it tracks `final_adapter/` (source LoRA) + `*-Q4_K_M.gguf`
  (deployable GGUF), pushed to `local_d_drive` → `/mnt/d/dvc-remotes/poesia`.
- **Model artifacts (source + deployable).** Keep the non-regenerable / deployable
  assets:
  - `final_adapter/` — the trained LoRA adapter (source of truth; not regenerable without retraining).
  - `*-Q4_K_M.gguf` — the deployable quantized GGUF (what llama.cpp serves).
- **The local SQLite MLflow history** (`mlruns/mlflow.db`) — training provenance
  (also dumped to `mlops/mlflow_metadata_dump.sql` in git).
- **`dvc.yaml`** — documents the data→model lineage.

### Defer (product-build work — not now)

- **SQLite → PostgreSQL migration for MemorIA.** Do this when the multi-user
  web/Android backend is built, not while the app is a CLI.
- **Web/API backend** (FastAPI or similar) and **model serving for users**.

### Fix (storage, not deletion)

- Done 2026-09-08: model weights are now backed up via the DVC remote. The
  regenerable intermediates (`merged/`, `*-f16.gguf`) are intentionally
  **not** stored — see §7.

## 4. Guardrails (DO NOT)

1. Do **not** delete PostgreSQL, the docker-compose stack, or collapse MLflow to SQLite.
2. Do **not** delete the source or deployable artifacts (`final_adapter/`,
   `*-Q4_K_M.gguf`), the trained adapters, or the MLflow history. The
   regenerable intermediates (`merged/`, `*-f16.gguf`) may be deleted and
   regenerated via `scripts/convert_adapters_to_gguf.py` (see §7).
3. Do **not** delete the local MLflow history (`mlruns/mlflow.db`) or the trained adapters.
4. Do **not** rip out the DVC skeleton, the training/serving Dockerfiles, or the `MLproject`.
5. Do **not** "clean up" infrastructure as if poesia were a finished personal toy.
6. Do **not** build product infrastructure (app DB, web backend, serving) as if
   the product already exists. It is a staged transition — see §5.

## 5. Triggers (when deferred items become active)

Start the deferred work only when the product build begins, evidenced by any of:

- A decision to build the web / Android frontend.
- A requirement for multiple users / concurrent access to the poem library.
- Corpus growth that makes git-only data tracking insufficient.

Until one of these fires, keep the current state and do not add or remove
infrastructure.

## 6. Why this document exists

A prior agent session repeatedly flip-flopped between "delete the heavy
infrastructure" and "build the full product infrastructure now" because the
product-vs-personal premise was never established before advising. This document
pins the premise, the current state, and the decisions so that does not recur.

## 7. Data/model system-of-record (adopted 2026-09-08)

Division of labor — one system of record per artifact type:

- **DVC** = versioning + backup of model weights: `final_adapter/` (source LoRA)
  and `*-Q4_K_M.gguf` (deployable GGUF), pushed to
  `local_d_drive` → `/mnt/d/dvc-remotes/poesia`.
- **Git** = provenance + results: `mlops/adapter_registry.json`, configs,
  scripts, docs, and the MLflow metadata dump `mlops/mlflow_metadata_dump.sql`.
- **MLflow** = experiment tracking (runs/params/metrics) + model registry.
  Metadata lives in `mlruns/mlflow.db` (SQLite, local) — **not** in the Docker
  Postgres (that DB only holds MLflow's own demo traces). `mlruns/` is a local,
  disposable artifact cache (gitignored, not DVC-tracked): its model copies are
  redundant with DVC, and its eval artifacts are regenerable via
  `scripts/evaluate_adapter_mlflow.py`.
- **Regenerable intermediates** — `models/*/merged/` and `models/*/*-f16.gguf`
  are derived (merge → convert → quantize), excluded via `.dvcignore`, deleted
  locally, and rebuilt on demand by `scripts/convert_adapters_to_gguf.py`
  (base model cached; llama.cpp tooling present).

Rule of thumb: a new **source-of-truth** artifact (adapter weights or a new
deployable) goes to DVC; a new **derived** artifact is regenerated, not stored.

This reverses the pre-2026-09-08 decisions in this document ("do not delete/trim
model artifacts", "defer DVC adoption") — a deliberate, user-directed change.

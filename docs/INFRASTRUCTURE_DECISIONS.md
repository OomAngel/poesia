# Infrastructure & Data Decisions — PoesIA

> **Status:** Authoritative. Read this **before** touching any infrastructure,
> data store, or model artifact. Last reviewed 2026-08-29.

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

## 2. Current state (verified 2026-08-29)

| Component | State |
|---|---|
| Application | Single-user Python CLI (`poesia write|scan|workshop|galeria|memoria|armonia`) |
| Web / API | **None** — no FastAPI/Flask/uvicorn in `src/` or `pyproject.toml`; only *outbound* LLM calls |
| Poem library (MemorIA) | Local Markdown + **SQLite** index (`~/.poesia/poems/`, `library.db`) |
| Experiment tracking | **MLflow** with a **PostgreSQL** backend (docker-compose: `postgres` + `mlflow-ui`) |
| Model artifacts | `models/` (~20 GB), **gitignored, local-only** (0 tracked files) |
| DVC | Installed in the `poesia` env (3.67.1); `dvc.yaml` is a skeleton; **no remote configured** |
| Serving | `serving.Dockerfile` = `mlflow models serve` sketch only (not an app backend) |
| Local MLflow history | `mlruns/mlflow.db` (SQLite): 30 runs / 11 experiments, 2026-07-29 → 2026-08-01 |

## 3. Decisions

### Keep (do not remove)

- **PostgreSQL + MLflow (docker-compose).** Working and cheap. Keep for
  experiment tracking. Do **not** collapse MLflow back to SQLite.
- **Model artifacts in `models/`.** These are serving/edge assets, not junk:
  - `poetry-lora-qwen3b/merged/` (12 GB) — merged fp16 model for server-side serving.
  - `qwen3b-poetry-f16.gguf` (5.8 GB) — fp16 GGUF for high-quality local inference.
  - `qwen3b-poetry-Q4_K_M.gguf` (1.8 GB) — 4-bit GGUF for low-RAM/mobile/edge.
  - `final_adapter/` (40 MB) — the trained LoRA adapter.
- **The local SQLite MLflow history** (`mlruns/mlflow.db`) — training provenance.
- **`dvc.yaml` skeleton** — documents the intended data→model lineage.

### Defer (product-build work — not now)

- **DVC adoption** (remote + `dvc repro` wiring). Needed once the corpus grows
  and models are iterated for a served product. The tool decision (DVC vs Git
  LFS + manifest vs model registry + object storage) is made **then**, not now.
- **SQLite → PostgreSQL migration for MemorIA.** Do this when the multi-user
  web/Android backend is built, not while the app is a CLI.
- **Web/API backend** (FastAPI or similar) and **model serving for users**.

### Fix (storage, not deletion)

- `models/` is gitignored and backed up nowhere. Put it on durable storage
  (D: drive or object storage). This is a **backup** task, not a deletion task.

## 4. Guardrails (DO NOT)

1. Do **not** delete PostgreSQL, the docker-compose stack, or collapse MLflow to SQLite.
2. Do **not** delete, trim, or gitignore-away the model artifacts in `models/`
   (`merged/`, `*-f16.gguf`, `*-Q4_K_M.gguf`, `final_adapter/`).
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

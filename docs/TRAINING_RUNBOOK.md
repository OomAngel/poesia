# PoesIA — Training Runbook

> **Machines** (full table and env commands: `README.md` "Machines"): the desktop
> (RTX 3070, 8 GB, Ampere sm_86) trains; the laptop (Quadro M1000M, 2 GB, Maxwell sm_50)
> cannot train. The laptop **evaluates and runs** already-trained adapters through a
> llama.cpp build for sm_50 (GGUF backend) — see `docs/DVC_INTEGRATION.md` and
> `docs/GENERATION_QUALITY_PLAN.md`. The 2026-08-31 version of this runbook recorded that
> no training GPU was available; that is why the
> [Online training](#online-training-no-local-gpu-needed) section exists (fuller cross-repo
> writeup: `company-intelligence/docs/FREE_COMPUTE_EXPLOITATION.md`).

## TL;DR

- Training **has already been done** — the LoRA adapters are checked into
  `models/` (table below). Don't retrain from scratch without a reason.
- 4-bit QLoRA of the 1.5B and 3B base models needs a GPU with **≥ 8 GB VRAM**
  (see `docs/EXPERIMENTS_PLAN.md` §2). 2 GB is not enough.
- On the desktop, reproduce any adapter with one command:

  ```bash
  scripts/launch_training.sh local mlops/configs/<config>.yaml
  ```

  or via Docker (`scripts/launch_training.sh docker …`) or MLflow
  (`mlflow run . -e <entry>`).

## Hardware requirement

| Machine | GPU | VRAM | Can train? |
|---|---|---|---|
| desktop | RTX 3070 (Ampere, sm_86) | 8 GB | ✅ yes — tier `gpu-cuda13`: torch 2.14.0+cu130 + bitsandbytes 0.50.2 (no adapter trained in its current WSL install yet, 2026-09-26) |
| laptop | Quadro M1000M (Maxwell, sm_50) | 2 GB | ❌ no — 2 GB, and bitsandbytes' CUDA builds need compute capability ≥ 6.0 |

The existing adapters were trained on an 8 GB GPU, 2026-07-28 to 08-07
(`mlops/adapter_registry.json`); 1.5B and 3B 4-bit QLoRA fit in 8 GB. Without the desktop, see
[Online training](#online-training-no-local-gpu-needed).

The `training` docker-compose service already requests the GPU
(`driver: nvidia, capabilities: [gpu]`); the conda path uses the `poesia` environment,
which `scripts/env.sh create` builds with the training stack on the desktop.

## Existing adapters (`models/`)

| Adapter | Config | Base model |
|---|---|---|
| `poetry-lora-qwen3b` | `mlops/configs/train_qwen3b.yaml` | Qwen2.5-3B-Instruct |
| `poetry-lora-v2-fixed` | `mlops/configs/train_v2_fixed.yaml` | Qwen2.5-1.5B-Instruct |
| `poetry-lora-v2` | `mlops/configs/train_v1.yaml` | Qwen2.5-1.5B-Instruct |
| `poetry-lora-dpo-expanded` | `mlops/configs/dpo_v1.yaml` | Qwen2.5-1.5B-Instruct |
| `poetry-lora-composite` | `mlops/configs/train_composite.yaml` | Qwen2.5-1.5B-Instruct |
| `poetry-lora-distilled` | `mlops/configs/train_distilled.yaml` | Qwen2.5-1.5B-Instruct |
| `poetry-lora-multiform` | `mlops/configs/train_multiform.yaml` | Qwen2.5-1.5B-Instruct |
| `smoke-test-adapter` | `mlops/configs/train_smoke.yaml` | Qwen2.5-1.5B-Instruct |
| `poetry-lora-3b` | (early 3B attempt, pre-config) | — |

## How to train (desktop)

### 0. Prerequisites

- A Windows NVIDIA driver that supports CUDA 13 for the cu130 wheels (the desktop's
  617.14 supports up to 13.4). WSL uses the Windows driver; training needs no CUDA toolkit.
- Either the `poesia` conda env built by `scripts/env.sh create` (recommended) or Docker
  with the NVIDIA runtime enabled.

### 1. Conda (local GPU)

```bash
cd poesia            # clone this repo first if not already present
scripts/env.sh create     # or: scripts/env.sh update (tier gpu-cuda13 on the desktop)
scripts/env.sh check      # must report bitsandbytes 4-bit ok
source scripts/poesia_env.sh
scripts/launch_training.sh local mlops/configs/train_qwen3b.yaml
```

### 2. Docker

```bash
scripts/launch_training.sh docker mlops/configs/train_qwen3b.yaml
# equivalent, raw:
docker compose -f docker/docker-compose.yml run training \
  python scripts/train_poetry_lora.py mlops/configs/train_qwen3b.yaml
```

### 3. MLflow

```bash
mlflow run . -e train-qwen3b
mlflow run . -e dpo
mlflow run . -e hpo -P n_trials=20
```

### 4. DPO

```bash
scripts/launch_training.sh dpo    # uses mlops/configs/dpo_v1.yaml
```

## Online training (no local GPU needed)

When the desktop is not at hand (the laptop cannot train), training has to run in the
cloud. **Groq is
inference-only** — it cannot fine-tune — so use one of the following instead.
Full cross-repo detail, dated sources, and a per-repo compute mapping live in
`company-intelligence/docs/FREE_COMPUTE_EXPLOITATION.md`; this table is the
poesia-specific summary of it.

| Option | What it is | Cost / limits |
|---|---|---|
| **Google Colab** (primary free option) | T4, 16 GB — fine for 1.5B QLoRA; 3B in 4-bit is tight | free; ~12h session cap, ~90min idle timeout |
| Kaggle | Notebook GPU, similar shape to Colab | free; 30h/week GPU quota |
| Lightning AI Studio | Free monthly GPU credits | free tier, amount unverified |
| Cloud GPU rental (RunPod / Lambda / Vast.ai) | Rent an A100/4090/3090 by the hour, clone the repo, run `scripts/launch_training.sh local …` or `docker` there | ~$0.3–2/hr; a Qwen2.5-1.5B/3B QLoRA run is a few hours |
| Hosted fine-tuning (Together AI / Fireworks / HF AutoTrain) | Upload `seeds/poetry_corpus/`, they fine-tune a base model, download the adapter into `models/` | pay-per-job |
| GCP / AWS burst credits | $300 (GCP) / equivalent (AWS) new-account credit, or always-free micro instances | 90-day burst, or free but CPU-only (no GPU) |
| HF Spaces / ZeroGPU | Shared Blackwell-class hardware | **inference/demo only — cannot run training jobs**; 5min/day free quota |
| Oracle Cloud Always Free | Ampere A1 Flex (~2 OCPU/12GB RAM) + 2× AMD micro | **no GPU** — CPU-only; useful for hosting/orchestration, not training |

On a GPU-backed remote machine (Colab, Kaggle, rented instance) the command is
identical to the local path: `scripts/launch_training.sh local
mlops/configs/<config>.yaml`. Output adapters land in `models/` and need to be
copied back to the dev machine. On Colab specifically, MLflow's local-Postgres
backend isn't reachable from the notebook — route `mlflow` at a SQLite file on
mounted Drive for the run, then import/merge it into the real tracking store
afterward rather than trying to point Colab at a local Postgres server.

**Surviving a Colab disconnect:** `output_dir` must point at a path on
mounted Drive (not the ephemeral local disk), since `TrainingArguments`
already checkpoints every `save_steps` — a killed/disconnected session loses
nothing past the last checkpoint. Re-run with
`python scripts/train_poetry_lora.py mlops/configs/<config>.yaml
--resume-from-checkpoint` to pick up from the newest checkpoint in
`output_dir` instead of restarting from scratch.

## After training

- `scripts/post_training_pipeline.sh` — evaluation + model-registry registration.
- `scripts/evaluate_adapter_mlflow.py --adapter <dir> --parent-run-id <id>`.
- `scripts/run_experiment_grid.py` — compare adapters side by side.

## Related

- `docs/EXPERIMENTS_PLAN.md` — base-model & technique matrix.
- `docs/MLOPS_DIAGNOSIS.md` — phase status and next execution steps.
- `scripts/launch_training.sh` — the unified launcher (local/docker/dpo).
- `MLproject` — `mlflow run` entry points.

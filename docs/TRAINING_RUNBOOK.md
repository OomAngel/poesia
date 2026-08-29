# PoesIA — Training Runbook

> **Where training happens:** on the GPU workstation, **not** on the development
> laptop. The laptop GPU is a Quadro M1000M (2 GB, Maxwell) and cannot train the
> models. Use the RTX 3070 Ti (8 GB) or the previous RTX 2000 Ada (8 GB).

## TL;DR

- Training **has already been done** — the LoRA adapters are checked into
  `models/` (table below). Don't retrain from scratch without a reason.
- 4-bit QLoRA of the 1.5B and 3B base models needs a GPU with **≥ 8 GB VRAM**
  (see `docs/EXPERIMENTS_PLAN.md` §2). 2 GB is not enough.
- On the GPU machine, reproduce any adapter with one command:

  ```bash
  scripts/launch_training.sh local mlops/configs/<config>.yaml
  ```

  or via Docker (`scripts/launch_training.sh docker …`) or MLflow
  (`mlflow run . -e <entry>`).

## Hardware requirement

| Machine | GPU | VRAM | Can train? |
|---|---|---|---|
| Dev laptop | Quadro M1000M (Maxwell, sm_50) | 2 GB | ❌ no |
| GPU workstation | RTX 3070 Ti (Ampere, sm_86) | 8 GB | ✅ 1.5B & 3B, 4-bit QLoRA |
| (previous) | RTX 2000 Ada | 8 GB | ✅ same |

The `training` docker-compose service already requests the GPU
(`driver: nvidia, capabilities: [gpu]`); the conda path uses the `poesia-gpu`
environment.

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

## How to train on the GPU workstation

### 0. Prerequisites

- NVIDIA driver + CUDA (the 3070 Ti needs a driver ≥ 525 for the cu121 wheels).
- Either the `poesia-gpu` conda env (recommended) or Docker with the NVIDIA
  runtime enabled.

### 1. Conda (local GPU)

```bash
cd poesia            # clone this repo first if not already present
conda env create -f environment.yml -n poesia-gpu   # or reuse the existing env
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

If neither the dev laptop nor a local GPU workstation is available, training can
run in the cloud. **Groq is inference-only** — it cannot fine-tune — so use one
of the following instead.

| Option | What it is | Cost |
|---|---|---|
| Cloud GPU rental (RunPod / Lambda / Vast.ai) | Rent an A100/4090/3090 by the hour, clone the repo, run `scripts/launch_training.sh local …` or `docker` there | ~$0.3–2/hr; a Qwen2.5-1.5B/3B QLoRA run is a few hours |
| Hosted fine-tuning (Together AI / Fireworks / HF AutoTrain) | Upload `seeds/poetry_corpus/`, they fine-tune a base model, download the adapter into `models/` | pay-per-job |
| Free GPU tiers (Google Colab T4, Kaggle) | 16 GB T4 — fine for 1.5B QLoRA; 3B in 4-bit is tight | free, session-limited |

On the remote machine the command is identical to the local path:
`scripts/launch_training.sh local mlops/configs/<config>.yaml`. Output adapters
land in `models/` and are copied back to the dev machine.

## After training

- `scripts/post_training_pipeline.sh` — evaluation + model-registry registration.
- `scripts/evaluate_adapter_mlflow.py --adapter <dir> --parent-run-id <id>`.
- `scripts/run_experiment_grid.py` — compare adapters side by side.

## Related

- `docs/EXPERIMENTS_PLAN.md` — base-model & technique matrix.
- `docs/MLOPS_DIAGNOSIS.md` — phase status and next execution steps.
- `scripts/launch_training.sh` — the unified launcher (local/docker/dpo).
- `MLproject` — `mlflow run` entry points.

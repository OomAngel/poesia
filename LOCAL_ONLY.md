# What a clone of this repository does not contain

Checked 2026-09-23. `git clone` brings every tracked file. What is listed here exists only
on the machine where it was made, deliberately. Before trusting this list, re-run
`git status --ignored --short`. Claude Code chats and memory are covered by
`~/dotfiles/claude/README.md`; the cross-repository picture is
`workspace-governance/WORKSTATION_TRANSITION.md`.

| Path | Size | Why it is not in git | On another machine |
|---|---|---|---|
| `models/*` (LoRA adapters) | ≈9.5 GB | Model weights, DVC-tracked; remote in sync on 2026-09-23. | `dvc pull` — the remote is `/mnt/d/dvc-remotes/poesia`, on this PC's D: drive. |
| `seeds/poetry_corpus/training_data*`, `repair_examples`, `sonetos_curated` | ≈42 MB | DVC-tracked corpus. | `dvc pull`. |
| `mlruns/`, `mlops/data/`, `dist/`, `galeria/`, `data/insights/*.parquet`, `screenshots/` | ≈1 GB | Generated: MLflow runs, derived datasets (`scripts/build_fixed_dataset.py`), builds. | Regenerated; MLflow history does not come back. |
| `.env`, `.env_mlflow` | small | Secrets. Encrypted copy is tracked in `secrets/` | `sops -d --output-type dotenv secrets/poesia.env.sops.yaml` — one file holds both; split `DATABASE_URL`/MLflow lines into `.env_mlflow`. Needs the age key; see below. |
| `.claude/` | small | Per-machine Claude Code permission settings. | Recreated as you approve tools. |

## Secrets on another machine

The encrypted copy in `secrets/` travels with the clone. To open it, the new machine needs
**one file**: the age key at `~/.config/sops/age/keys.txt`, the same key for every repository.
Copy it from this PC through the password manager, never through git; or use the recovery
key kept in OneDrive (`Personal documents/SOPS-age-recovery-key.txt`), which is the second
recipient on every file. When you change a plaintext `.env`, re-encrypt it before leaving the
PC, or the other machine gets the old values.

## Replicating from pointers, and training on a bigger GPU

**Pointers are enough only if what they point to is reachable.** A `.dvc` file or a
`dvc.lock` entry holds a content hash and size, not the data. `dvc pull` fetches the
content from the DVC remote, and this repository's only remote is `local_d_drive` =
`/mnt/d/dvc-remotes/poesia`, a folder on this PC's D: drive. On another PC every pointer
resolves to nothing until the remote is reachable there: carry the drive, or add a
network remote (`dvc remote add` with S3-compatible storage; the workspace already has
Cloudflare R2 credentials in `cielch-color-research/secrets/`) and `dvc push` once from
here. On 2026-09-23 `dvc status -c` reported cache and remote in sync, including
`models/poetry-lora-v2/`, which is the `train` stage's output in `dvc.lock` rather than a
standalone `.dvc` file.

What regenerates rather than needs pulling: `merged/` and `*-f16.gguf` are excluded by
`.dvcignore` and rebuilt by `scripts/convert_adapters_to_gguf.py`. What does not: each
`final_adapter/` is the trained source (`docs/INFRASTRUCTURE_DECISIONS.md` §7) — retraining
from the same config produces a comparable adapter, not the identical one.

**None of these adapters were trained on this laptop.** Its Quadro M1000M (2 GB, Maxwell
sm_50) cannot train; it only *evaluates* adapters through llama.cpp. Training ran on an
8 GB GPU (RTX 3070 Ti workstation; see `docs/TRAINING_RUNBOOK.md`), which is what capped
the base models at Qwen2.5-1.5B/3B with 4-bit QLoRA — `docs/EXPERIMENTS_PLAN.md` marks
Llama 3.1 8B "won't fit 8 GB". On a more capable GPU, the runbook's one command reproduces
any adapter (`scripts/launch_training.sh local mlops/configs/<config>.yaml`), and the
EXPERIMENTS_PLAN candidates ranked impractical become the next experiment. Do not run a
bare `dvc repro`: it retrains `poetry-lora-v2` first (`docs/DVC_INTEGRATION.md`).

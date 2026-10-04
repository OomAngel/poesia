# What a clone of this repository does not contain

Checked 2026-09-23. `git clone` brings every tracked file. What is listed here exists only
on the machine where it was made, deliberately. Before trusting this list, re-run
`git status --ignored --short`. Claude Code chats and memory are covered by
`claude/README.md` in the dotfiles repo (`~/dotfiles` on the laptop, `~/dev/dotfiles` on the desktop); the cross-repository picture is
`workspace-governance/WORKSTATION_TRANSITION.md`.

| Path | Size | Why it is not in git | On another machine |
|---|---|---|---|
| `models/*` (LoRA adapters) | ≈9.5 GB | Model weights, DVC-tracked; remote in sync on 2026-09-23 (laptop). | `dvc pull` — the remote is `/mnt/d/dvc-remotes/poesia`, on the laptop's D: drive; the desktop has no such folder (checked 2026-09-26). |
| `seeds/poetry_corpus/training_data*`, `repair_examples`, `sonetos_curated` | ≈42 MB | DVC-tracked corpus. | `dvc pull`. |
| `mlruns/`, `mlops/data/`, `dist/`, `galeria/`, `data/insights/*.parquet`, `screenshots/` | ≈1 GB | Generated: MLflow runs, derived datasets (`scripts/build_fixed_dataset.py`), builds. | Regenerated; MLflow history does not come back. |
| `seeds/poetry_corpus/external/`, `eval_gold/` | ≈235 MB | Downloaded research corpora and the ADSO gold set (2026-10-04). Gitignored, not yet in DVC. | Re-download per `docs/CORPUS_SOURCES.md`. |
| `.env`, `.env_mlflow` | small | Secrets. Encrypted copy is tracked in `secrets/` | `sops -d --output-type dotenv secrets/poesia.env.sops.yaml` — one file holds both; split `DATABASE_URL`/MLflow lines into `.env_mlflow`. Needs the age key; see below. |
| `.claude/` | small | Per-machine Claude Code permission settings. | Recreated as you approve tools. |

## Secrets on another machine

The encrypted copy in `secrets/` travels with the clone. To open it, the new machine needs
**one file**: the age key at `~/.config/sops/age/keys.txt`, the same key for every repository.
Copy it from a machine that has it through the password manager, never through git; or use
the recovery key kept in OneDrive (`Personal documents/SOPS-age-recovery-key.txt`), which is
the second recipient on every file. When you change a plaintext `.env`, re-encrypt it before leaving the
PC, or the other machine gets the old values.

## Replicating from pointers, and training on a bigger GPU

**Pointers are enough only if what they point to is reachable.** A `.dvc` file or a
`dvc.lock` entry holds a content hash and size, not the data. `dvc pull` fetches the
content from the DVC remote, and this repository's only remote is `local_d_drive` =
`/mnt/d/dvc-remotes/poesia`, a folder on the laptop's D: drive (the desktop has none,
checked 2026-09-26). On any other PC every pointer resolves to nothing until the remote is
reachable there: carry the drive, or add a network remote (`dvc remote add` with
S3-compatible storage; the workspace already has Cloudflare R2 credentials in
`cielch-color-research/secrets/`) and `dvc push` once from the laptop. On 2026-09-23 (on the
laptop) `dvc status -c` reported cache and remote in sync, including
`models/poetry-lora-v2/`, which is the `train` stage's output in `dvc.lock` rather than a
standalone `.dvc` file.

What regenerates rather than needs pulling: `merged/` and `*-f16.gguf` are excluded by
`.dvcignore` and rebuilt by `scripts/convert_adapters_to_gguf.py`. What does not: each
`final_adapter/` is the trained source (`docs/INFRASTRUCTURE_DECISIONS.md` §7) — retraining
from the same config produces a comparable adapter, not the identical one.

**Where the adapters were trained, and where they run.** They were trained on an 8 GB GPU
(2026-07-28 to 08-07, `mlops/adapter_registry.json`), which is what capped the base models
at Qwen2.5-1.5B/3B with 4-bit QLoRA — `docs/EXPERIMENTS_PLAN.md` marks Llama 3.1 8B "won't
fit 8 GB". Of the two machines (`README.md` "Machines"), the desktop (RTX 3070, 8 GB, sm_86)
is the one that trains; the laptop (Quadro M1000M, 2 GB, Maxwell sm_50) cannot train and
runs the adapters through a llama.cpp build for sm_50, which is where they were evaluated
and where generation and sampling were tuned. On a more capable GPU, the runbook's one
command reproduces any adapter (`scripts/launch_training.sh local
mlops/configs/<config>.yaml`), and the EXPERIMENTS_PLAN candidates ranked impractical become
the next experiment. Do not run a bare `dvc repro`: it retrains `poetry-lora-v2` first
(`docs/DVC_INTEGRATION.md`).

## Still to do (verified 2026-10-02)

- Same DVC decision as `orchard_twins`: storage is still only `/mnt/d/dvc-remotes/poesia`, in sync with the laptop cache (checked 2026-10-02). The adapters reach the desktop only via the drive or a network remote.
- Calibrate the "better model" expectation: the desktop `AngelThuis` is an RTX 3070 with **8 GB** (`workspace-governance/machines/AngelThuis.json`), the same VRAM class that trained the existing adapters. It can retrain any of them locally. Corrected 2026-10-04: "needs ≥16 GB for 8B" holds only for the default QLoRA layout (embedding and `lm_head` in bf16). With `lm_head` in NF4 and the embedding in CPU RAM, models up to ~9B (Qwen3.5-9B, Qwen3-8B) are estimated to fit in about 6 GB. This is unmeasured until the smoke run in `docs/RETRAINING_PLAN_2026-10.md` §6 step 4. Rerun the estimate with `scripts/estimate_qlora_vram.py`.
- 2026-10-04 desktop: the corpus was rebuilt without the remote (`docs/CORPUS_SOURCES.md` "Rebuilding the corpus"); `dvc add` updated the pointers, but the new data is cached only on the desktop: the laptop's remote doesn't have it. The adapters are still laptop-only (`models/` is 36 KB).
- On each new machine, confirm the age key works: `sops -d secrets/<file>.sops.yaml >/dev/null && echo ok`. Not verifiable from the laptop.

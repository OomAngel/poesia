# What a clone of this repository does not contain

Checked 2026-09-23. `git clone` brings every tracked file. What is listed here exists only
on the machine where it was made, deliberately. Before trusting this list, re-run
`git status --ignored --short`. Claude Code chats and memory are covered by
`claude/README.md` in the dotfiles repo (`~/dotfiles` on the laptop, `~/dev/dotfiles` on the desktop); the cross-repository picture is
`workspace-governance/WORKSTATION_TRANSITION.md`.

| Path | Size | Why it is not in git | On another machine |
|---|---|---|---|
| `models/*` (LoRA adapters) | ≈9.5 GB | Model weights, DVC-tracked; remote in sync on 2026-09-23 (laptop). | `dvc pull` — the remote is `/mnt/d/dvc-remotes/poesia`, on the laptop's D: drive; the desktop has no such folder (checked 2026-09-26). |
| `seeds/poetry_corpus/corpus_master`, `training_data*`, `repair_examples`, `sonetos_curated`, `external`, `eval_gold` | ≈700 MB (corpus_master 163 MB, training_data_structured 178 MB, external 346 MB; 2026-10-04) | DVC-tracked corpus, never in git: the repository is public and the corpus includes copyrighted texts. `external/` holds the downloaded research corpora, `eval_gold/` the ADSO gold set. | `dvc pull`, except that the 2026-10-04 data is cached on the desktop only (below); or rebuild per `docs/CORPUS_SOURCES.md`. |
| `data/distill/*` (line data v3-v5 and holdouts, `blind-pages/`, `blind-key-*.json`, `blind-keys.json`), `models/line-v5-peft/` | 69 MB + 169 MB (2026-10-17) | DVC-tracked (`data/distill.dvc`, `models/line-v5-peft.dvc`); the blind keys must not be seen before Angel's ratings are in. | **Only on the desktop's D: drive**, `D:\dvc-remotes\poesia` (240 MB, line data only, in sync 2026-10-17 on AngelThuis). The laptop's D: remote is a different folder (adapters and corpus); the laptop cannot `dvc pull` these until the desktop's folder is copied over or both machines get a shared remote. The v3 and v4 adapter weights were not kept. |
| Full history of `quality-layer`, `calaveritas` and their merge (working notes, research notes, service decisions) | small | **Unified 2026-10-17 (Angel):** the code is in this repo's `hack-apertus`/`main` (`44a27ca`, one code-only commit); the full history, working notes included, is in the private repo `OomAngel/poesia-private` (`main`). | Notes and research about the Calaveritas service go to the private repo, not here. The old local branches are contained in private `main`. |
| `~/kaggle-results-2026-10-17/` (outside the repo) | small | Output of the Kaggle 4-bit replicate runs, fetched by a detached script on the desktop. | Stays on the desktop; re-fetch with `kaggle kernels output angelmarquezaguilar/poesia-line-adapter-eval` only while no newer version was pushed. |
| `mlruns/`, `mlops/data/`, `dist/`, `galeria/`, `data/insights/*.parquet`, `screenshots/` | ≈1 GB | Generated: MLflow runs, derived datasets (`scripts/build_fixed_dataset.py`), builds. | Regenerated; MLflow history does not come back. |
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
`cielch-color-research/secrets/`) and `dvc push` from both machines: the adapters from the laptop, the 2026-10-04 corpus from
the desktop. On 2026-09-23 (on the
laptop) `dvc status -c` reported cache and remote in sync, including
`models/poetry-lora-v2/`, which is the `train` stage's output in `dvc.lock` rather than a
standalone `.dvc` file.

What regenerates rather than needs pulling: `merged/` and `*-f16.gguf` are excluded by
`.dvcignore` and rebuilt by `scripts/convert_adapters_to_gguf.py`. What does not: each
`final_adapter/` is the trained source (`docs/INFRASTRUCTURE_DECISIONS.md` §7) — retraining
from the same config produces a comparable adapter, not the identical one.

**Where the adapters were trained, and where they run.** They were trained on an 8 GB RTX 2000 Ada,
a machine no longer in use (2026-07-28 to 08-07, `mlops/adapter_registry.json`), which is what capped the base models
at Qwen2.5-1.5B/3B with 4-bit QLoRA — `docs/archive/EXPERIMENTS_PLAN.md` marks Llama 3.1 8B "won't
fit 8 GB". Of the two machines (`README.md` "Machines"), the desktop (RTX 3070, 8 GB, sm_86)
is the one that trains; the laptop (Quadro M1000M, 2 GB, Maxwell sm_50) cannot train and
runs the adapters through a llama.cpp build for sm_50, which is where they were evaluated
and where generation and sampling were tuned. The runbook's one command reproduces any
adapter (`scripts/launch_training.sh local mlops/configs/<config>.yaml`). Retraining with a
larger corpus and a larger base model was decided on 2026-10-04:
`docs/RETRAINING_PLAN_2026-10.md`. Do not run a bare `dvc repro`: it retrains `poetry-lora-v2` first
(`docs/DVC_INTEGRATION.md`).

## Still to do (verified 2026-10-02)

- **Laptop, MLflow 3.14.0 → 3.16.1 (security fixes, 2026-10-04):** after updating the
  laptop env, back up the store first (`cp mlruns/mlflow.db mlruns/mlflow.db.3.14.bak`),
  then `mlflow db upgrade sqlite:///mlruns/mlflow.db`, check the run count is unchanged
  (71), and regenerate `mlops/mlflow_metadata_dump.sql` from the upgraded store.

- Same DVC decision as `orchard_twins`: storage is still only `/mnt/d/dvc-remotes/poesia`. It was in sync with the laptop cache on 2026-10-02, but lacks the corpus the desktop added on 2026-10-04 (below). The adapters reach the desktop only via the drive or a network remote.
- Calibrate the "better model" expectation: the desktop `AngelThuis` is an RTX 3070 with **8 GB** (`workspace-governance/machines/AngelThuis.json`), the same VRAM class that trained the existing adapters. It can retrain any of them locally. Corrected 2026-10-04: "needs ≥16 GB for 8B" holds only for the default QLoRA layout (embedding and `lm_head` in bf16). With `lm_head` in NF4 and the embedding in CPU RAM, models up to ~9B (Qwen3.5-9B, Qwen3-8B) are estimated to fit in about 6 GB. This is unmeasured until the smoke run in `docs/RETRAINING_PLAN_2026-10.md` §6 step 4. Rerun the estimate with `scripts/estimate_qlora_vram.py`.
- 2026-10-04 desktop: the corpus was rebuilt without the remote (`docs/CORPUS_SOURCES.md` "Rebuilding the corpus"); `dvc add` updated the pointers, but the new data is cached only on the desktop: the laptop's remote doesn't have it. The adapters are still laptop-only (`models/` is 36 KB).
- On each new machine, confirm the age key works: `sops -d secrets/<file>.sops.yaml >/dev/null && echo ok`. Not verifiable from the laptop.

# What a clone of this repository does not contain

Checked 2026-09-23. `git clone` brings every tracked file. What is listed here exists only
on the machine where it was made, deliberately. Before trusting this list, re-run
`git status --ignored --short`. Claude Code chats and memory are covered by
`~/dotfiles/claude/README.md`; the cross-repository picture is
`workspace-governance/WORKSTATION_TRANSITION.md`.

| Path | Size | Why it is not in git | On another machine |
|---|---|---|---|
| `models/*` (LoRA adapters) | ≈9.5 GB | Model weights, DVC-tracked; remote in sync on 2026-09-23. | `dvc pull` — the remote is `/mnt/d/dvc-remotes/poesia`, on this PC's D: drive. |
| `models/poetry-lora-v2/` | 1.1 GB | Has **no** `.dvc` pointer, unlike its siblings, so DVC does not carry it. | Exists only on this disk; `dvc add` it or accept losing it. |
| `seeds/poetry_corpus/training_data*`, `repair_examples`, `sonetos_curated` | ≈42 MB | DVC-tracked corpus. | `dvc pull`. |
| `mlruns/`, `mlops/data/`, `dist/`, `galeria/`, `data/insights/*.parquet`, `screenshots/` | ≈1 GB | Generated: MLflow runs, derived datasets (`scripts/build_fixed_dataset.py`), builds. | Regenerated; MLflow history does not come back. |
| `.env`, `.env_mlflow` | small | Secrets. | Password manager. |
| `.claude/` | small | Per-machine Claude Code permission settings. | Recreated as you approve tools. |

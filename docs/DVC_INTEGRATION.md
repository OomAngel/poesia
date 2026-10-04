# DVC integration — data-to-training lineage

> **Status:** `evaluate` stage adopted and driven via `dvc repro` (2026-09-02) · `distill`/`train`
> still skeleton-only — never run under DVC on the laptop, where `evaluate` runs and which cannot
> train (see `TRAINING_RUNBOOK.md`) · **Added:** 2026-08-10
>
> **Status 2026-10-04:** the poetry corpus is DVC-tracked too (never in git since `f8b2017`);
> `corpus_master` was `dvc add`ed on the desktop and is cached there only, not pushed. The
> only remote is on the laptop's D: drive, which the desktop can't reach; a remote both
> machines reach is open (`RETRAINING_PLAN_2026-10.md` §7). The desktop now trains, but the
> 2026-10 retraining runs outside DVC (see the gotcha below).

## Why

`docs/MLOPS_DIAGNOSIS.md` documents PoesIA's MLflow setup as the most
complete MLOps stack among this repo's siblings, covering training-to-
deployment: autologging, model registry, serving. It does not cover
data-to-training: the `distill -> train -> eval` chain (`MLproject`'s
`pipeline` entry point) always re-runs every stage, and (before `f8b2017`)
growing training datasets under `seeds/poetry_corpus/` sat in plain git
with no dependency-aware versioning.

The split, confirmed against real-world documented practice (DVC + MLflow
is a named combination, not an invented one -- see e.g. AWS's
SageMaker+DVC+MLflow lineage writeup and Walmart Global Tech's
model-and-data-versioning post): **DVC owns data-to-training lineage,
MLflow owns training-to-deployment lineage, the git commit ties them
together.** This is additive to the existing MLflow setup, not a
replacement -- `mlflow run` / the `poesia` CLI keep working exactly as
they do today.

## What exists now

- `dvc init` run (`.dvc/`, `.dvcignore` -- git-integrated, not `--no-scm`).
- `dvc.yaml`: four stages mirroring `MLproject`'s real `pipeline` entry
  point (`distill -> train -> evaluate`, plus `benchmark`), using the real
  scripts and the real `mlops/configs/train_v1.yaml` as the params source
  (`lora_r`, `lora_alpha`, `lora_dropout`, `epochs`, `learning_rate`, `model`).
- `evaluate` is a `foreach` stage (2026-09-02), one instance per locally
  trained adapter (`evaluate@poetry-lora-v2`, `evaluate@poetry-lora-qwen3b`,
  etc. -- 8 total, `poetry-lora-composite` excluded since its `.dvc`-tracked
  artifact is empty). Each instance's `deps` are the eval script plus that
  one adapter's directory, so `dvc repro` only re-runs the adapters whose
  weights or the script actually changed -- the actual point of routing
  this through DVC instead of a hand-rolled sweep script.
- All 8 `evaluate@*` stages have been run for real and are locked in
  `dvc.lock` (2026-09-02, via `dvc repro --single-item`, see the gotcha
  below) -- confirmed via `dvc status evaluate` reporting up to date, and
  cross-checked against a manual run of the same 8 adapters logging
  identical numbers to MLflow (see `GENERATION_QUALITY_PLAN.md`).
- Verified: `dvc dag` resolves the correct chain, `dvc params diff`
  correctly reads the 6 tracked params out of the real YAML.
- The corpus is data-tracked (never in git since `f8b2017`; the GitHub repo
  is public): `.dvc` pointers under `seeds/poetry_corpus/` for
  `corpus_master`, `training_data_structured`, `external`, `eval_gold`,
  `sonetos_curated`, `training_data` and `repair_examples`. `corpus_master`
  was `dvc add`ed 2026-10-04 on the desktop; its cache is on the desktop
  only, not pushed to any remote.

## Gotcha: `dvc repro evaluate` is NOT safe to run bare (it retrains first)

`evaluate@poetry-lora-v2` depends on `models/poetry-lora-v2`, which is the
`train` stage's own `outs:` (not a standalone `.dvc` file) -- so it's a
stage dependency, not a data dependency. `train`'s `deps` (the training
script) have since changed, so DVC considers `train` out of date. A bare
`dvc repro evaluate` (or `dvc repro` with no target) walks the full
upstream chain and would **retrain `poetry-lora-v2` first** -- i.e. kick
off a real GPU training job -- which must never happen on the laptop
(training happens on the desktop, see `TRAINING_RUNBOOK.md`).
The `train` stage is still the July recipe (`train_v1.yaml` on
`sonetos_train.jsonl` → `poetry-lora-v2`), not the 2026-10 retraining
(`build_fixed_dataset.py --max-poems` on `corpus_master`, then
`train_poetry_lora.py`; `RETRAINING_PLAN_2026-10.md`), which runs outside
DVC — so a bare `dvc repro` is wrong on the desktop too.
Always reproduce each `evaluate@<adapter>` stage individually with
`--single-item` (`-s`), which skips the recursive upstream check entirely:

```bash
dvc repro --single-item evaluate@poetry-lora-v2
```

`--dry` first if in doubt -- it prints exactly which stages (including any
upstream `train`) would run, without executing anything.

## What's deliberately not done

- `evaluate` has no `outs:` -- eval metrics/artifacts already go to
  MLflow via `evaluate_adapter_mlflow.py`; DVC tracking the same numbers
  a second time would recreate the "dual unsynchronized tracking" failure
  mode `MLOPS_DIAGNOSIS.md` Gap #1 already named and fixed once.
- Remote storage is `local_d_drive` → `/mnt/d/dvc-remotes/poesia` (a local
  D: drive path, added 2026-08-31). Tracking policy (2026-09-07): DVC
  versions the source LoRA weights (`final_adapter/`) plus the deployable
  quantized GGUF (`*-Q4_K_M.gguf`); the regenerable intermediates
  (`merged/` full-model safetensors and `*-f16.gguf`) are excluded via
  `.dvcignore`. `poetry-lora-qwen3b` was re-tracked under this rule,
  shrinking it from ~20.7 GB to ~2.1 GB. As of 2026-10-04 this is still the
  only remote: the July adapters' data exists only there (the desktop's
  `models/` holds `.dvc` pointers), and the desktop can't reach it.
- Regenerable intermediates (`merged/` full-model safetensors, `*-f16.gguf`)
  are rebuilt from `final_adapter/` + the base model by
  `scripts/convert_adapters_to_gguf.py`.
- MLflow results are **not** in the Docker Postgres backend (that DB only
  holds MLflow's own demo traces). They live in the local SQLite/FileStore
  at `mlruns/` on the laptop — metadata in `mlruns/mlflow.db` (71 runs, 8
  registered models; the desktop has no `mlflow.db`), artifacts in `mlruns/<experiment_id>/<run_id>/`. A point-in-time
  SQL dump is committed at `mlops/mlflow_metadata_dump.sql`; regenerate it
  with a SQLite dump of `mlruns/mlflow.db` (e.g. `sqlite3 mlruns/mlflow.db
  .dump` or Python's `sqlite3.Connection.iterdump()`). To also back up
  artifacts, archive `mlruns/` itself.
- `distill` and `train` are still declared but not executed under DVC.
  The desktop can train since 2026-10; wiring `train` to `corpus_master`
  (and deciding whether to fold `dvc repro` into the `poesia` CLI or
  `MLproject`) is open, not scheduled — the retraining plan runs training
  outside DVC for now.

# DVC integration — data-to-training lineage

> **Status:** `evaluate` stage adopted and driven via `dvc repro` (2026-09-02) · `distill`/`train`
> still skeleton-only — never run under DVC on this machine, since training doesn't happen on
> this laptop (see `TRAINING_RUNBOOK.md`) · **Added:** 2026-08-10

## Why

`docs/MLOPS_DIAGNOSIS.md` documents PoesIA's MLflow setup as the most
complete MLOps stack among this repo's siblings, covering training-to-
deployment: autologging, model registry, serving. It does not cover
data-to-training: the `distill -> train -> eval` chain (`MLproject`'s
`pipeline` entry point) always re-runs every stage, and growing training
datasets under `seeds/poetry_corpus/` sit in plain git with no dependency-
aware versioning.

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

## Gotcha: `dvc repro evaluate` is NOT safe to run bare on this machine

`evaluate@poetry-lora-v2` depends on `models/poetry-lora-v2`, which is the
`train` stage's own `outs:` (not a standalone `.dvc` file) -- so it's a
stage dependency, not a data dependency. `train`'s `deps` (the training
script) have since changed, so DVC considers `train` out of date. A bare
`dvc repro evaluate` (or `dvc repro` with no target) walks the full
upstream chain and would **retrain `poetry-lora-v2` first** -- i.e. kick
off a real GPU training job -- which must never happen on this laptop
(training only happens on the GPU workstation, see `TRAINING_RUNBOOK.md`).
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
- No remote storage configured (`dvc remote add`) -- large files
  (`models/poetry-lora-v2`, the distilled JSONL) stay wherever they
  already live until a real remote (S3/local NAS/etc.) is chosen
  deliberately.
- `distill` and `train` are still declared but not executed under DVC --
  running `train` for real, and deciding whether to fold `dvc repro` into
  the `poesia` CLI or `MLproject`, stays out of scope until it can be done
  on training-capable hardware, not this laptop.

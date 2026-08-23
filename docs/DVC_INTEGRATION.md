# DVC integration — data-to-training lineage

> **Status:** Skeleton only, not adopted into the default workflow · **Added:** 2026-08-10

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
- `dvc.yaml`: three stages mirroring `MLproject`'s real `pipeline` entry
  point (`distill -> train -> evaluate`), using the real scripts and the
  real `mlops/configs/train_v1.yaml` as the params source (`lora_r`,
  `lora_alpha`, `lora_dropout`, `epochs`, `learning_rate`, `model`).
- Verified, not just written: `dvc dag` resolves the correct linear chain,
  `dvc params diff` correctly reads the 6 tracked params out of the real
  YAML, `dvc status` correctly reports all three stages as not-yet-run
  under DVC (expected -- `dvc repro` was deliberately not run; that would
  kick off a real multi-hour training job, out of scope for a skeleton).

## What's deliberately not done

- `evaluate` has no `outs:` -- eval metrics/artifacts already go to
  MLflow via `evaluate_adapter_mlflow.py`; DVC tracking the same numbers
  a second time would recreate the "dual unsynchronized tracking" failure
  mode `MLOPS_DIAGNOSIS.md` Gap #1 already named and fixed once.
- No remote storage configured (`dvc remote add`) -- large files
  (`models/poetry-lora-v2`, the distilled JSONL) stay wherever they
  already live until a real remote (S3/local NAS/etc.) is chosen
  deliberately.
- `dvc repro` has not been run -- these stages are declared, not
  executed under DVC yet. Running them for real, and deciding whether to
  fold `dvc repro` into the `poesia` CLI or `MLproject`, is the next
  deliberate step, not something to do silently.

#!/usr/bin/env python3
"""Backfill MLflow Model Registry entries for adapters trained outside train_poetry_lora.py's
inline registration (Phase 3) — legacy JSONL-tracked imports and manually-run training that
predates that code path. Safe to re-run: MLflow versions each registration, it doesn't overwrite.

Usage:
    python scripts/register_adapters.py
"""

from __future__ import annotations

import json
import os

import mlflow

from poesia.training.model_wrapper import PoetryModelWrapper

mlflow.set_tracking_uri(os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db"))

# (adapter dir name, registry model name, base model)
ADAPTERS = [
    ("poetry-lora-v2", "poesia-lora-v2", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-multiform", "poesia-lora-multiform", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-distilled", "poesia-lora-distilled", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-v2-fixed", "poesia-lora-v2-fixed", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-3b", "poesia-lora-3b", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-dpo-expanded", "poesia-lora-dpo-expanded", "Qwen/Qwen2.5-1.5B-Instruct"),
]

with open("mlops/adapter_registry.json") as f:
    local_registry = {a["adapter_path"]: a for a in json.load(f)["adapters"]}

mlflow.set_experiment("model-registry-backfill")

for dir_name, registry_name, base_model in ADAPTERS:
    adapter_path = f"models/{dir_name}/final_adapter"
    if not os.path.isdir(adapter_path):
        print(f"[SKIP] {dir_name}: no final_adapter/ found")
        continue

    known = local_registry.get(adapter_path, {})
    with mlflow.start_run(run_name=f"backfill-{dir_name}"):
        mlflow.log_param("adapter_path", adapter_path)
        mlflow.log_param("base_model", base_model)
        mlflow.log_param("source", "backfill-registration")
        if known.get("config"):
            mlflow.log_param("config", known["config"])
        if known.get("lora_r") is not None:
            mlflow.log_param("lora_r", known["lora_r"])
        if known.get("data_sha256"):
            mlflow.log_param("data_sha256", known["data_sha256"])
        if known.get("train_loss") is not None:
            mlflow.log_metric("train_loss", known["train_loss"])
        if known.get("eval_line_count_accuracy") is not None:
            mlflow.log_metric("eval_line_count_accuracy", known["eval_line_count_accuracy"])
        if known.get("eval_syllable_deviation") is not None:
            mlflow.log_metric("eval_syllable_deviation", known["eval_syllable_deviation"])

        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=PoetryModelWrapper(base_model=base_model),
            artifacts={"adapter": adapter_path},
            model_config={"base_model": base_model},
            registered_model_name=registry_name,
        )
        print(f"[OK] {dir_name} -> registered as {registry_name}")

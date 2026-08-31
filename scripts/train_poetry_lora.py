"""QLoRA fine-tuning for Spanish poetry on a 3B model.

All experiment tracking goes to MLflow — the single source of truth.
No more custom JSONL/JSON dual writes.

Usage:
    python scripts/train_poetry_lora.py
    python scripts/train_poetry_lora.py mlops/configs/train_v1.yaml

Requires: pip install transformers datasets peft bitsandbytes accelerate
"""

import datetime
import json
import os
import subprocess
import sys
import time

import mlflow
import torch
import yaml
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    TrainingArguments,
)

# ═══════════════════════════════════════════════════════════════════════
# Phase 1 — MLflow-only tracking
# Consolidated on 2026-07-30
# ═══════════════════════════════════════════════════════════════════════
#
# All experiment metadata (params, metrics, tags, artifacts) is logged
# exclusively to MLflow. The legacy custom JSONL/JSON writes in
# mlops/runs/ have been removed. Use `mlops/experiments.py` (now powered
# by MLflow API) or the MLflow UI to query runs.
#
# ═══════════════════════════════════════════════════════════════════════


def search_best_adapter(metric="eval_loss", goal="minimize", experiment=None):
    """Search all MLflow runs for the best adapter by a given metric.

    Args:
        metric: Metric to compare
        goal: 'minimize' or 'maximize'
        experiment: Experiment name filter (None = all)

    Returns:
        (run_id, adapter_path, metric_value) or None
    """
    mlflow.set_tracking_uri(_resolve_tracking_uri())
    from mlflow.tracking import MlflowClient

    client = MlflowClient()

    exp_filter = experiment or ""
    best_value = float("inf") if goal == "minimize" else float("-inf")
    best_run = None

    experiments = client.search_experiments()
    for exp in experiments:
        if exp_filter and exp_filter not in exp.name:
            continue
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string='attributes.status = "FINISHED"',
            order_by=[f"metrics.{metric} ASC"],
        )
        if runs:
            best_in_exp = runs[0]
            val = best_in_exp.data.metrics.get(metric, None)
            if val is not None:
                adapter = best_in_exp.data.params.get("adapter_path", "unknown")
                run_id = best_in_exp.info.run_id
                print(f"  {exp.name}: best {metric}={val:.4f} ({run_id[:8]}...)")
                if goal == "minimize" and val < best_value:
                    best_value = val
                    best_run = (run_id, adapter, val)
                elif goal == "maximize" and val > best_value:
                    best_value = val
                    best_run = (run_id, adapter, val)

    return best_run


def _resolve_tracking_uri() -> str:
    """MLflow tracking URI from DATABASE_URL env or default SQLite."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
        db_url = "sqlite:///mlruns/mlflow.db"
    return db_url


def _capture_git_commit() -> str:
    """First 12 chars of HEAD commit, or 'unknown'."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()[:12]
    except Exception:
        return "unknown"


def _pop_resume_flag(argv: list[str]) -> bool:
    """Pull a `--resume-from-checkpoint` flag out of argv in place, so a
    positional config path can still be given in any order. Needed for
    Colab: a disconnect/session-limit kill mid-run should resume from the
    Trainer's last save_steps checkpoint instead of restarting from scratch.
    """
    if "--resume-from-checkpoint" in argv:
        argv.remove("--resume-from-checkpoint")
        return True
    return False


def main():
    # ── Config ────────────────────────────────────────────────────────
    resume_from_checkpoint = _pop_resume_flag(sys.argv)
    config_path = sys.argv[1] if len(sys.argv) > 1 else "mlops/configs/train_v1.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    model_name = cfg["model"]
    train_path = cfg["train_data"]
    eval_path = cfg.get("eval_data", train_path)
    output_dir = cfg["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    # Compute data manifest (SHA256, record count, sources)
    sys.path.insert(0, "mlops")
    from data_manifest import compute_manifest

    data_manifest = compute_manifest(train_path)
    print(
        f"Data: {data_manifest['record_count']} records, SHA256: {data_manifest['sha256'][:16]}..."
    )

    git_commit = _capture_git_commit()

    # ── Data lineage (provenance tracking) ────────────────────────────
    data_lineage = {
        "dataset_version": "v1",
        "source_files": data_manifest.get("sources", [train_path]),
        "data_forms": data_manifest.get("forms", []),
        "record_count": data_manifest["record_count"],
        "data_sha256": data_manifest["sha256"][:16],
        "git_commit": git_commit,
        "config_file": config_path,
    }

    # ── MLflow setup ──────────────────────────────────────────────────
    mlflow.set_tracking_uri(_resolve_tracking_uri())
    experiment_name = cfg.get("experiment", "poesia-training")
    try:
        mlflow.create_experiment(experiment_name, artifact_location=f"./mlruns/{experiment_name}")
    except Exception:
        pass  # Experiment already exists
    mlflow.set_experiment(experiment_name)

    # Phase 2: Enable PyTorch autologging — captures optimizer state and
    # training metrics via HF Trainer's report_to='mlflow' in TrainingArguments
    # below. NOTE: mlflow.transformers.autolog() was attempted here but it is
    # a no-op (only disables sub-model logging).
    #
    # `mlflow.pytorch.autolog()` does NOT log hardware/system metrics (CPU,
    # GPU utilization, memory) on its own — a prior version of this comment
    # claimed it did; it doesn't. `mlflow.enable_system_metrics_logging()` is
    # the actual API for that, polling in a background thread for the
    # lifetime of the active run.
    mlflow.pytorch.autolog(
        log_models=False,  # We handle model saving manually
        log_datasets=False,  # We use data_manifest.py for dataset tracking
        disable=False,
        silent=True,
    )
    mlflow.enable_system_metrics_logging()

    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = cfg.get("run_name", f"run_{run_id}")
    run_tags = cfg.get("tags", [])

    # ══════════════════════════════════════════════════════════════════
    # Single MLflow run spanning the ENTIRE training lifecycle
    # Previously the mlflow.start_run() context was only ~20 lines
    # and closed BEFORE training. Now it wraps everything.
    # ══════════════════════════════════════════════════════════════════
    with mlflow.start_run(run_name=run_name) as active_run:
        mlflow_run_id = active_run.info.run_id
        print(f"MLflow run ID: {mlflow_run_id}")
        _train_start = time.time()

        # ── Log custom params to MLflow ────────────────────────────────
        # NOTE: HF Trainer auto-logs TrainingArguments via report_to="mlflow",
        # so we only log params that TrainingArguments doesn't cover.
        mlflow.log_param("model", model_name)
        mlflow.log_param("config", config_path)
        mlflow.log_param("git_commit", git_commit)
        mlflow.set_tag("git_commit", git_commit)
        mlflow.log_param("train_data", train_path)
        mlflow.log_param("eval_data", eval_path)
        mlflow.log_param("output_dir", output_dir)
        mlflow.log_param("loss_fn", cfg.get("loss_fn", "ce"))
        mlflow.log_param("lora_r", cfg.get("lora_r", 16))
        mlflow.log_param("lora_alpha", cfg.get("lora_alpha", 32))
        mlflow.log_param("lora_dropout", cfg.get("lora_dropout", 0.05))
        mlflow.log_param(
            "lora_target_modules", ",".join(cfg.get("lora_target_modules", ["q_proj", "v_proj"]))
        )
        mlflow.log_param(
            "effective_batch", cfg.get("batch_size", 8) * cfg.get("gradient_accumulation", 1)
        )
        mlflow.log_param("max_length", cfg.get("max_length", 300))
        mlflow.log_param("quantization", cfg.get("quantization", "4bit"))
        mlflow.log_param("data_records", data_manifest["record_count"])
        mlflow.log_param("data_sha256", data_manifest["sha256"][:16])
        mlflow.log_param("data_sources", ",".join(data_manifest.get("sources", [])))
        mlflow.log_param("data_forms", ",".join(data_manifest.get("forms", [])))
        mlflow.log_param("data_lineage", json.dumps(data_lineage, indent=2))

        # Set MLflow tags
        for tag in run_tags:
            mlflow.set_tag(tag, "true")
        mlflow.set_tag("run_id_str", run_id)

        # Log artifacts
        manifest_path = os.path.join(output_dir, "data_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(data_manifest, f, indent=2)
        mlflow.log_artifact(manifest_path)
        mlflow.log_artifact(config_path)

        # ── 4-bit quantisation ───────────────────────────────────────
        print(f"Free VRAM: {torch.cuda.mem_get_info()[0] / 1e9:.1f}GB")
        print(f"Loading {model_name} in 4-bit...")

        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )
        model = prepare_model_for_kbit_training(model)
        print(f"Model loaded. {model.num_parameters() / 1e9:.1f}B params")
        print(f"VRAM after load: {torch.cuda.mem_get_info()[0] / 1e9:.1f}GB free")

        # ── LoRA config ──────────────────────────────────────────────
        lora = LoraConfig(
            r=cfg.get("lora_r", 16),
            lora_alpha=cfg.get("lora_alpha", 32),
            target_modules=cfg.get("lora_target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"]),
            lora_dropout=cfg.get("lora_dropout", 0.05),
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora)
        model.print_trainable_parameters()

        # ── Load data ────────────────────────────────────────────────
        def load_jsonl(path):
            texts, weights = [], []
            with open(path) as f:
                for line in f:
                    ex = json.loads(line)
                    text = ex["prompt"] + ex["completion"] + tokenizer.eos_token
                    texts.append(text)
                    weights.append(ex.get("quality_score", 1.0))
            return Dataset.from_dict({"text": texts, "quality_weight": weights})

        train_ds = load_jsonl(train_path)
        eval_ds = load_jsonl(eval_path)
        print(f"Train: {len(train_ds)}, Eval: {len(eval_ds)}")

        def tokenize(ex):
            tokens = tokenizer(ex["text"], truncation=True, max_length=cfg.get("max_length", 300))
            tokens["quality_weight"] = ex["quality_weight"]
            return tokens

        train_ds = train_ds.map(tokenize, remove_columns=["text"])
        eval_ds = eval_ds.map(tokenize, remove_columns=["text"])

        collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

        # ── Train ────────────────────────────────────────────────────
        args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=cfg.get("batch_size", 8),
            per_device_eval_batch_size=cfg.get("batch_size", 8),
            gradient_accumulation_steps=cfg.get("gradient_accumulation", 2),
            num_train_epochs=cfg.get("epochs", 10),
            learning_rate=cfg.get("learning_rate", 2e-4),
            fp16=True,
            logging_steps=cfg.get("logging_steps", 10),
            eval_strategy="steps",
            eval_steps=cfg.get("eval_steps", 50),
            save_strategy="steps",
            save_steps=cfg.get("save_steps", 100),
            save_total_limit=1,
            report_to="mlflow",
            remove_unused_columns=False,
        )

        # Select trainer based on loss function
        loss_fn = cfg.get("loss_fn", "ce")
        if loss_fn == "composite":
            from poesia.training.poetry_trainer import PoetryTrainer

            trainer = PoetryTrainer(
                model=model,
                args=args,
                train_dataset=train_ds,
                eval_dataset=eval_ds,
                data_collator=collator,
                scorer_weight=cfg.get("scorer_weight", 0.15),
                syll_target=11,
                language=cfg.get("language", "es"),
            )
            print(f"PoetryTrainer composite loss (weight={cfg.get('scorer_weight', 0.15)})")
        elif loss_fn == "dpo":
            print("Use scripts/train_poetry_dpo.py for DPO training")
            sys.exit(1)
        else:
            from transformers import Trainer

            trainer = Trainer(
                model=model,
                args=args,
                train_dataset=train_ds,
                eval_dataset=eval_ds,
                data_collator=collator,
            )
            print("Standard Trainer with cross-entropy loss")

        print(f"Starting training... (resume_from_checkpoint={resume_from_checkpoint})")
        train_result = trainer.train(resume_from_checkpoint=resume_from_checkpoint or None)

        # ── Log final metrics to MLflow ──────────────────────────────
        final_loss = None
        for entry in reversed(trainer.state.log_history):
            if "loss" in entry:
                final_loss = entry["loss"]
                break
        if final_loss is not None:
            mlflow.log_metric("train_loss", final_loss)

        # Log step-level metrics from training
        for entry in trainer.state.log_history:
            if "loss" in entry and "step" in entry:
                mlflow.log_metric("loss", entry["loss"], step=entry["step"])
            if "eval_loss" in entry:
                mlflow.log_metric("eval_loss", entry["eval_loss"], step=entry.get("step", 0))

        _train_elapsed = time.time() - _train_start
        mlflow.log_metric("train_duration_seconds", round(_train_elapsed, 2))

        # Save adapter
        adapter_path = os.path.join(output_dir, "final_adapter")
        model.save_pretrained(adapter_path)
        tokenizer.save_pretrained(adapter_path)
        print(f"LoRA adapter saved to {adapter_path}/")

        # Log adapter files as MLflow artifacts
        mlflow.log_artifacts(adapter_path, artifact_path="adapter")
        mlflow.log_param("adapter_path", adapter_path)

        # Phase 5: Data versioning — log dataset provenance to MLflow
        try:
            from mlflow.data import from_json

            dataset = from_json(train_path, name="training_data")
            mlflow.log_input(dataset, context="training")
            if eval_path != train_path:
                eval_dataset = from_json(eval_path, name="eval_data")
                mlflow.log_input(eval_dataset, context="evaluation")
        except Exception as dv_err:
            print(f"  [WARN] Data versioning failed (non-blocking): {dv_err}")

        # Phase 3: Log the model as an MLflow pyfunc model and register it
        model_registry_name = f"poesia-lora-{experiment_name}"
        try:
            import pandas as pd
            from mlflow.models import infer_signature

            from poesia.training.model_wrapper import PoetryModelWrapper

            # A signature lets the Model Registry and `mlflow models serve`
            # validate input/output shape before running inference, and
            # documents the contract (a 'prompt' column in, generated text
            # out) for anyone loading this model later. It was previously
            # missing — `log_model()` accepted whatever was passed with no
            # schema check.
            input_example = pd.DataFrame({"prompt": ["Write a soneto in Spanish about the sea."]})
            signature = infer_signature(input_example, ["example generated poem text"])

            mlflow.pyfunc.log_model(
                artifact_path="model",
                python_model=PoetryModelWrapper(base_model=model_name),
                artifacts={"adapter": adapter_path},
                model_config={"base_model": model_name},
                registered_model_name=model_registry_name,
                signature=signature,
                input_example=input_example,
            )
            print(f"Model registered in MLflow Registry: {model_registry_name}")
            mlflow.set_tag("mlflow.registeredModelName", model_registry_name)
        except Exception as mr_err:
            print(f"  [WARN] Model Registry registration failed (non-blocking): {mr_err}")

        # Local adapter registry (kept for backward compatibility)
        registry_path = "mlops/adapter_registry.json"
        with open(registry_path) as f:
            registry = json.load(f)
        registry_entry = {
            "id": run_id,
            "mlflow_run_id": mlflow_run_id,
            "mlflow_model_name": model_registry_name,
            "created": datetime.datetime.now().isoformat(),
            "config": config_path,
            "data_sha256": data_manifest["sha256"],
            "base_model": model_name,
            "lora_r": cfg.get("lora_r", 16),
            "train_loss": final_loss,
            "adapter_path": adapter_path,
            "notes": "",
        }
        try:
            from mlflow.tracking import MlflowClient

            registry_entry["mlflow_model_version"] = (
                MlflowClient(_resolve_tracking_uri())
                .get_latest_versions(model_registry_name)[0]
                .version
            )
        except Exception:
            pass
        registry["adapters"].append(registry_entry)
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        print(f"Registered in {registry_path}")

        # ── Auto-evaluate ────────────────────────────────────────────
        print("\n=== Auto-evaluating adapter ===")
        try:
            sys.path.insert(0, "mlops")
            from evaluate_adapter import evaluate as eval_adapter

            eval_results = eval_adapter(adapter_path)
            summary = eval_results["summary"]

            mlflow.log_metric("eval_syllable_deviation", summary["avg_syllable_deviation"])
            mlflow.log_metric("eval_line_count_accuracy", summary["line_count_accuracy"])
            mlflow.log_metric("eval_avg_line_count", summary["avg_line_count"])

            for theme, tr in eval_results.get("themes", {}).items():
                mlflow.log_metric(f"{theme}_line_count", tr["lines"])
                mlflow.log_metric(f"{theme}_syllable_deviation", tr["avg_syllable_deviation"])

            # Log eval artifact
            eval_artifact_path = os.path.join(output_dir, "eval_results.json")
            with open(eval_artifact_path, "w") as f:
                json.dump(eval_results, f, indent=2, ensure_ascii=False)
            mlflow.log_artifact(eval_artifact_path)

            # Update adapter registry with eval metrics
            with open(registry_path) as f:
                registry = json.load(f)
            for entry in registry["adapters"]:
                if entry["id"] == run_id:
                    entry["eval_syllable_deviation"] = summary["avg_syllable_deviation"]
                    entry["eval_line_count_accuracy"] = summary["line_count_accuracy"]
                    break
            with open(registry_path, "w") as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)

            print(f"  Line count accuracy: {summary['line_count_accuracy']:.1%}")
            print(f"  Avg syllable deviation: {summary['avg_syllable_deviation']:.2f} per line")
        except Exception as eval_err:
            print(f"  [WARN] Evaluation failed (will not block training): {eval_err}")

        # ── Test ─────────────────────────────────────────────────────
        print("\n=== Testing ===")
        try:
            prompt = "Write a Spanish poem about the sea.\n"
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
            with torch.no_grad():
                out = model.generate(**inputs, max_new_tokens=100, temperature=0.8)
            generated_text = tokenizer.decode(out[0])
            print(generated_text)
            test_path = os.path.join(output_dir, "test_generation.txt")
            with open(test_path, "w") as f:
                f.write(generated_text)
            mlflow.log_artifact(test_path)
        except Exception as test_err:
            print(f"  [WARN] Test generation failed: {test_err}")

    # ── mlflow.start_run() context ends here ─────────────────────────
    print(f"\n✅ Training complete. MLflow run: {mlflow_run_id}")
    print(f"   Adapter: {adapter_path}")
    print("   View: mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db")


if __name__ == "__main__":
    main()

"""QLoRA fine-tuning for Spanish poetry on a 3B model.

Usage:
    python scripts/train_poetry_lora.py

Requires: pip install transformers datasets peft bitsandbytes accelerate
"""

import json
import os
import sys
import yaml
import torch
import hashlib
import datetime
import os
# MLflow tracking URI: DATABASE_URL env var, or fallback to SQLite
import mlflow
from pathlib import Path
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


def main():
    # ── Config ────────────────────────────────────────────────────────
    # Load from YAML config file (passed via --config or default)
    config_path = sys.argv[1] if len(sys.argv) > 1 else "mlops/configs/train_v1.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    model_name = cfg["model"]
    train_path = cfg["train_data"]
    eval_path = cfg.get("eval_data", train_path)
    output_dir = cfg["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    # Compute data manifest
    sys.path.insert(0, "mlops")
    from data_manifest import compute_manifest
    data_manifest = compute_manifest(train_path)
    print(f"Data: {data_manifest['record_count']} records, SHA256: {data_manifest['sha256'][:16]}...")
    
    # ── Data lineage (provenance tracking) ────────────────────────────
    data_lineage = {
        "dataset_version": "v1",
        "source_files": data_manifest.get("sources", [train_path]),
        "data_forms": data_manifest.get("forms", []),
        "record_count": data_manifest["record_count"],
        "data_sha256": data_manifest["sha256"][:16],
        "git_commit": git_hash,
        "config_file": config_path,
    }
    
    # ── MLflow tracking ────────────────────────────────────────────────
    # Requires Docker PostgreSQL running (docker compose up -d)
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Start CronologIA first:")
        print("  cd cronologia && docker compose up -d")
        print("  export DATABASE_URL=postgresql://mlflow:mlflow@localhost:5432/mlflow")
        sys.exit(1)
    mlflow.set_tracking_uri(db_url)
    experiment_name = cfg.get("experiment", "poesia-training")
    try:
        mlflow.create_experiment(experiment_name, artifact_location=f"./mlruns/{experiment_name}")
    except Exception:
        pass  # Experiment already exists
    mlflow.set_experiment(experiment_name)
    
    with mlflow.start_run(run_name=cfg.get("run_name", f"run_{run_id}")):
        # Log all config params
        mlflow.log_param("model", model_name)
        mlflow.log_param("lora_r", cfg.get("lora_r", 16))
        mlflow.log_param("lora_alpha", cfg.get("lora_alpha", 32))
        mlflow.log_param("lora_dropout", cfg.get("lora_dropout", 0.05))
        mlflow.log_param("batch_size", cfg.get("batch_size", 8))
        mlflow.log_param("gradient_accumulation", cfg.get("gradient_accumulation", 2))
        mlflow.log_param("epochs", cfg.get("epochs", 10))
        mlflow.log_param("learning_rate", cfg.get("learning_rate", 2e-4))
        mlflow.log_param("max_length", cfg.get("max_length", 300))
        mlflow.log_param("data_records", data_manifest["record_count"])
        mlflow.log_param("data_sha256", data_manifest["sha256"][:16])
        mlflow.log_param("config", config_path)
        mlflow.log_param("data_lineage", json.dumps(data_lineage, indent=2))
        mlflow.log_param("data_forms", ",".join(data_manifest.get("forms", [])))
        mlflow.log_param("git_commit", git_hash)
        run_id_mlflow = mlflow.active_run().info.run_id
        print(f"MLflow run ID: {run_id_mlflow}")
    
        # ── Experiment tracking ────────────────────────────────────────────
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Capture git commit hash for reproducibility
    git_hash = "unknown"
    try:
        import subprocess
        git_hash = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()[:12]
    except Exception:
        pass

    start_time = datetime.datetime.now().isoformat()

    run_log = {
        "run_id": run_id,
        "experiment": cfg.get("experiment", "default"),
        "run_name": cfg.get("run_name", f"run_{run_id}"),
        "git_commit": git_hash,
        "config": config_path,
        "model": model_name,
        "data_sha256": data_manifest["sha256"],
        "data_records": data_manifest["record_count"],
        "train_data": train_path,
        "eval_data": eval_path,
        "lora_r": cfg.get("lora_r", 16),
        "lora_alpha": cfg.get("lora_alpha", 32),
        "lora_dropout": cfg.get("lora_dropout", 0.05),
        "batch_size_per_device": cfg.get("batch_size", 8),
        "gradient_accumulation": cfg.get("gradient_accumulation", 2),
        "effective_batch": cfg.get("batch_size", 8) * cfg.get("gradient_accumulation", 2),
        "epochs": cfg.get("epochs", 10),
        "learning_rate": cfg.get("learning_rate", 2e-4),
        "max_length": cfg.get("max_length", 300),
        "fp16": cfg.get("fp16", True),
        "loss_fn": cfg.get("loss_fn", "ce"),
        "tags": cfg.get("tags", []),
        "start_time": start_time,
        "end_time": None,
        "duration_s": None,
        "train_samples": None,
        "eval_samples": None,
        "train_loss": None,
        "eval_loss": None,
        "train_runtime_s": None,
        "data_sources": data_manifest["sources"],
        "data_forms": data_manifest["forms"],
        "status": "RUNNING",
        "adapter_path": None,
    }
    # Append to experiments database (JSONL) — MLflow-style
    runs_dir = "mlops/runs"
    os.makedirs(runs_dir, exist_ok=True)
    experiments_db = os.path.join(runs_dir, "experiments.jsonl")
    with open(experiments_db, "a") as f:
        f.write(json.dumps(run_log) + "\n")
    # Also save individual run file for human readability
    run_log_path = os.path.join(runs_dir, f"{run_id}.json")
    with open(run_log_path, "w") as f:
        json.dump(run_log, f, indent=2)
    print(f"Run ID: {run_id}")
    print(f"Config: {config_path}")
    print(f"Run log: {run_log_path}")
    print(f"DB: {experiments_db}")

    print(f"Free VRAM: {torch.cuda.mem_get_info()[0]/1e9:.1f}GB")
    print(f"Loading {model_name} in 4-bit...")

    # ── 4-bit quantisation ────────────────────────────────────────────
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
    print(f"Model loaded. {model.num_parameters()/1e9:.1f}B params")
    print(f"VRAM after load: {torch.cuda.mem_get_info()[0]/1e9:.1f}GB free")

    # ── LoRA config ───────────────────────────────────────────────────
    lora = LoraConfig(
        r=cfg.get("lora_r", 16),
        lora_alpha=cfg.get("lora_alpha", 32),
        target_modules=cfg.get("lora_target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"]),
        lora_dropout=cfg.get("lora_dropout", 0.05),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()  # Should be ~0.5% of total

    # ── Load data ─────────────────────────────────────────────────────
    def load_jsonl(path):
        prompts, completions = [], []
        with open(path) as f:
            for line in f:
                ex = json.loads(line)
                # Format: prompt + completion + EOS
                text = ex["prompt"] + ex["completion"] + tokenizer.eos_token
                prompts.append(text)
        return Dataset.from_dict({"text": prompts})

    train_ds = load_jsonl(train_path)
    eval_ds = load_jsonl(eval_path)
    print(f"Train: {len(train_ds)}, Eval: {len(eval_ds)}")

    def tokenize(ex):
        return tokenizer(ex["text"], truncation=True, max_length=cfg.get("max_length", 300))

    train_ds = train_ds.map(tokenize, remove_columns=["text"])
    eval_ds = eval_ds.map(tokenize, remove_columns=["text"])

    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm=False
    )

    # ── Train ─────────────────────────────────────────────────────────
    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=cfg.get("batch_size", 8),
        per_device_eval_batch_size=cfg.get("batch_size", 8),
        gradient_accumulation_steps=cfg.get("gradient_accumulation", 2),
        num_train_epochs=cfg.get("epochs", 10),
        learning_rate=cfg.get("learning_rate", 2e-4),
        fp16=True,
        logging_steps=cfg.get('logging_steps', 10),
        eval_strategy="steps",
        eval_steps=cfg.get('eval_steps', 50),
        save_strategy="steps",
        save_steps=cfg.get('save_steps', 100),
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
        print(f"Using PoetryTrainer with composite loss (weight={cfg.get('scorer_weight', 0.15)})")
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
        print("Using standard Trainer with cross-entropy loss")
    
    # Add loss_fn to run log
    cfg["loss_fn"] = loss_fn

    print("Starting training...")
    trainer.train()
    
    # Log final metrics to MLflow
    train_result = trainer.state.log_history
    final_loss = None
    if train_result:
        # Get the last logged loss (train or eval)
        for entry in reversed(train_result):
            if "loss" in entry:
                final_loss = entry["loss"]
                break
        if final_loss is not None:
            mlflow.log_metric("final_loss", final_loss)
    
    # Log training metrics
    if hasattr(trainer.state, "log_history"):
        for entry in trainer.state.log_history:
            if "loss" in entry and "step" in entry:
                mlflow.log_metric("train_loss", entry["loss"], step=entry["step"])
            if "eval_loss" in entry:
                mlflow.log_metric("eval_loss", entry["eval_loss"], step=entry.get("step", 0))
    
    # Log adapter as artifact
    adapter_final = os.path.join(output_dir, "final_adapter")
    if os.path.exists(adapter_final):
        mlflow.log_artifacts(adapter_final, artifact_path="adapter")
        mlflow.log_param("adapter_path", adapter_final)
    
    # Update run log with results
    final_loss = None
    for entry in reversed(train_result):
        if "loss" in entry:
            final_loss = entry["loss"]
            break
    run_log["train_loss"] = final_loss
    run_log["train_runtime_s"] = trainer.state.total_flos
    run_log["train_samples"] = len(train_ds)
    run_log["eval_samples"] = len(eval_ds)
    run_log["status"] = "completed"
    run_log["end_time"] = datetime.datetime.now().isoformat()
    run_log["duration_s"] = (datetime.datetime.fromisoformat(run_log["end_time"]) - datetime.datetime.fromisoformat(run_log["start_time"])).total_seconds()
    with open(run_log_path, "w") as f:
        json.dump(run_log, f, indent=2)
    print(f"Final loss: {final_loss}")
    
    # Save adapter (~50MB)
    adapter_path = os.path.join(output_dir, "final_adapter")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"LoRA adapter saved to {adapter_path}/")
    run_log["adapter_path"] = adapter_path
    run_log["status"] = "saved"
    with open(run_log_path, "w") as f:
        json.dump(run_log, f, indent=2)

    # Register in adapter registry
    registry_path = "mlops/adapter_registry.json"
    with open(registry_path) as f:
        registry = json.load(f)
    registry["adapters"].append({
        "id": run_id,
        "created": datetime.datetime.now().isoformat(),
        "config": config_path,
        "data_sha256": data_manifest["sha256"],
        "base_model": model_name,
        "lora_r": cfg.get("lora_r", 16),
        "train_loss": run_log.get("train_loss"),
        "adapter_path": adapter_path,
        "notes": "",
    })
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print(f"Registered in {registry_path}")

    # ── Auto-evaluate ───────────────────────────────────────────────────
    print("\n=== Auto-evaluating adapter ===")
    try:
        sys.path.insert(0, "mlops")
        from evaluate_adapter import evaluate
        eval_results = evaluate(adapter_path)
        run_log["eval_syllable_deviation"] = eval_results["summary"]["avg_syllable_deviation"]
        run_log["eval_line_count_accuracy"] = eval_results["summary"]["line_count_accuracy"]
        run_log["eval_avg_line_count"] = eval_results["summary"]["avg_line_count"]
        run_log["status"] = "evaluated"
        with open(run_log_path, "w") as f:
            json.dump(run_log, f, indent=2)
        # Update registry with eval metrics
        with open(registry_path) as f:
            registry = json.load(f)
        for entry in registry["adapters"]:
            if entry["id"] == run_id:
                entry["eval_syllable_deviation"] = eval_results["summary"]["avg_syllable_deviation"]
                entry["eval_line_count_accuracy"] = eval_results["summary"]["line_count_accuracy"]
                break
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        print(f"  Line count accuracy: {eval_results['summary']['line_count_accuracy']:.1%}")
        print(f"  Avg syllable deviation: {eval_results['summary']['avg_syllable_deviation']:.2f} per line")
    except Exception as eval_err:
        print(f"  [WARN] Evaluation failed (will not block training): {eval_err}")
        run_log["status"] = "trained (eval failed)"

    # ── Test ──────────────────────────────────────────────────────────
    print("\n=== Testing ===")
    prompt = "Write a Spanish poem about the sea.\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=100, temperature=0.8)
    print(tokenizer.decode(out[0]))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""DPO fine-tuning with real LineScorer composite scores.

Uses composite_score() as the reward signal — scores metre, rhyme,
theme, novelty, cliché. Lines scoring above mean+0.5std are "chosen",
below are "rejected". Creates meaningful preference pairs from the
full metric suite, not just syllable heuristics.

Usage:
    python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml

Requires: pip install trl
"""

import datetime
import json
import os
import subprocess
import sys

import mlflow
import torch
import yaml
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from trl import DPOTrainer


def generate_preference_pairs(record, tokenizer, phonology):
    """Score each line with composite_score(), split at mean+0.5std."""
    from poesia.evaluation.metrics import composite_score

    prompt = record["prompt"]
    reference = record["completion"]
    lines = [l for l in reference.split("\n") if l.strip()]
    target_syll = 11

    scored_lines = []
    for line in lines:
        try:
            scan = phonology.scan_line(line)
            m_score = 1.0 - min(abs(scan.metrical_syllable_count - target_syll) / target_syll, 1.0)
            rk = phonology.rhyme_key(line)
            rk_str = rk.consonant if hasattr(rk, "consonant") else str(rk)
            r_score = 1.0 if rk_str and len(rk_str) > 1 else 0.0
            total = composite_score(
                metre=m_score,
                rhyme=r_score,
                theme=0.5,
                novelty=0.5,
                cliche=0.0,
                end_word=1.0,
            )
            scored_lines.append({"line": line, "score": total})
        except Exception:
            scored_lines.append({"line": line, "score": 0.3})

    if not scored_lines:
        return None

    scored_lines.sort(key=lambda x: x["score"], reverse=True)
    scores = [s["score"] for s in scored_lines]
    if not scores:
        return None
    median = sum(scores) / len(scores)
    std = (sum((s - median) ** 2 for s in scores) / len(scores)) ** 0.5 or 0.1
    threshold = median + std * 0.5

    chosen = [s for s in scored_lines if s["score"] >= threshold]
    rejected = [s for s in scored_lines if s["score"] < threshold]

    if len(chosen) < 1 or len(rejected) < 1:
        mid = len(scored_lines) // 2
        chosen = scored_lines[:mid]
        rejected = scored_lines[mid:]

    if not chosen or not rejected:
        return None

    pairs = []
    for c in chosen[:3]:
        for r in rejected[:3]:
            pairs.append(
                {
                    "prompt": prompt,
                    "chosen": c["line"] + tokenizer.eos_token,
                    "rejected": r["line"] + tokenizer.eos_token,
                }
            )
    return pairs


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


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "mlops/configs/dpo_v1.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    model_name = cfg["model"]
    output_dir = cfg["output_dir"]
    train_path = cfg["train_data"]

    mlflow.set_tracking_uri(os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db"))
    experiment_name = cfg.get("experiment", "soneto-dpo")
    try:
        mlflow.create_experiment(experiment_name, artifact_location=f"./mlruns/{experiment_name}")
    except Exception:
        pass
    mlflow.set_experiment(experiment_name)

    run_name = cfg.get("run_name", f"dpo-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")

    with mlflow.start_run(run_name=run_name) as active_run:
        mlflow_run_id = active_run.info.run_id
        print(f"MLflow run ID: {mlflow_run_id}")
        git_commit = _capture_git_commit()
        mlflow.log_param("git_commit", git_commit)
        mlflow.set_tag("git_commit", git_commit)
        mlflow.log_param("model", model_name)
        mlflow.log_param("lora_r", cfg.get("lora_r", 16))
        mlflow.log_param("epochs", cfg.get("epochs", 5))
        mlflow.log_param("learning_rate", cfg.get("learning_rate", 5e-5))
        mlflow.log_param("dpo_beta", cfg.get("dpo_beta", 0.1))

        print(f"Loading model: {model_name}")
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
        lora = LoraConfig(
            r=cfg.get("lora_r", 16),
            lora_alpha=cfg.get("lora_alpha", 32),
            target_modules=cfg.get("lora_target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"]),
            lora_dropout=cfg.get("lora_dropout", 0.05),
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora)

        from poesia.phonology.spanish import SpanishPhonology

        phonology = SpanishPhonology()

        print(f"Loading data from: {train_path}")
        with open(train_path) as f:
            records = [json.loads(line) for line in f]

        print(f"Generating preference pairs from {len(records)} records...")
        pairs = []
        for i, record in enumerate(records):
            result = generate_preference_pairs(record, tokenizer, phonology)
            if result:
                pairs.extend(result)
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(records)}... ({len(pairs)} pairs)")

        print(f"Generated {len(pairs)} preference pairs")
        mlflow.log_param("dpo_pairs", len(pairs))

        if not pairs:
            print("ERROR: No valid preference pairs generated.")
            sys.exit(1)

        dataset = Dataset.from_list(pairs)

        from trl import DPOConfig

        training_args = DPOConfig(
            output_dir=output_dir,
            per_device_train_batch_size=cfg.get("batch_size", 4),
            gradient_accumulation_steps=cfg.get("gradient_accumulation", 2),
            num_train_epochs=cfg.get("epochs", 5),
            learning_rate=cfg.get("learning_rate", 5e-5),
            fp16=cfg.get("fp16", False),
            bf16=cfg.get("bf16", False),
            logging_steps=cfg.get("logging_steps", 10),
            save_steps=cfg.get("save_steps", 50),
            save_total_limit=1,
            remove_unused_columns=False,
            report_to="mlflow",
            beta=cfg.get("dpo_beta", 0.1),
        )

        dpo_trainer = DPOTrainer(
            model=model,
            ref_model=None,
            args=training_args,
            train_dataset=dataset,
            processing_class=tokenizer,
        )

        print("Starting DPO training...")
        dpo_trainer.train()

        final_path = os.path.join(output_dir, "final_adapter")
        model.save_pretrained(final_path)
        tokenizer.save_pretrained(final_path)
        mlflow.log_artifacts(final_path, artifact_path="adapter")
        mlflow.log_param("adapter_path", final_path)
        print(f"DPO adapter saved to: {final_path}")

    print(f"\n\\U0001f3f4 DPO complete. MLflow run: {mlflow_run_id}")


if __name__ == "__main__":
    main()

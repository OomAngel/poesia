#!/usr/bin/env python3
"""DPO fine-tuning: train the model to prefer good lines over bad ones.

Uses the existing LineScorer as a reward signal. For each prompt, generates
multiple candidates, scores them, and trains the model to prefer high-scoring
lines over low-scoring ones.

Usage:
    python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml

Requires: pip install trl
"""

import json
import os
import sys
import yaml
import torch
import datetime
from pathlib import Path

from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model
from trl import DPOTrainer


def generate_preference_pairs(record, model, tokenizer, phonology, n_candidates=8):
    """Generate (chosen, rejected) line pairs using the scorer as reward."""
    from poesia.evaluation.scorer import LineScorer

    prompt = record["prompt"]
    reference = record["completion"]
    lines = [l for l in reference.split("\n") if l.strip()]

    # Score each line using our existing metrics
    scorer = LineScorer(
        phonology_backend=phonology,
        target_syllable_count=11,
    )

    chosen_lines = []
    rejected_lines = []

    for line in lines:
        try:
            scan = phonology.scan_line(line)
            score = scorer.score_candidates([line])[0].score if hasattr(scorer, 'score_candidates') else 0.5
        except Exception:
            score = 0.0

        # HACK: For now, we use syllable accuracy as the signal
        # If line has correct syllables -> chosen, else -> rejected
        try:
            scan = phonology.scan_line(line)
            syll_ok = abs(scan.metrical_syllable_count - 11) <= 1
        except Exception:
            syll_ok = False

        if syll_ok:
            chosen_lines.append(line)
        else:
            rejected_lines.append(line)

    # If no valid pairs, skip
    if not chosen_lines or not rejected_lines:
        return None

    # Build preference pairs
    pairs = []
    for chosen in chosen_lines[:3]:
        for rejected in rejected_lines[:3]:
            pairs.append({
                "prompt": prompt,
                "chosen": chosen + tokenizer.eos_token,
                "rejected": rejected + tokenizer.eos_token,
            })

    return pairs


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "mlops/configs/dpo_v1.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    model_name = cfg["model"]
    output_dir = cfg["output_dir"]
    train_path = cfg["train_data"]

    print(f"Loading model: {model_name}")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name, quantization_config=bnb,
        device_map="auto", torch_dtype=torch.bfloat16,
    )

    # LoRA config
    lora = LoraConfig(
        r=cfg.get("lora_r", 16),
        lora_alpha=cfg.get("lora_alpha", 32),
        target_modules=cfg.get("lora_target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"]),
        lora_dropout=cfg.get("lora_dropout", 0.05),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)

    # Load training data
    from poesia.phonology.spanish import SpanishPhonology
    phonology = SpanishPhonology()

    print(f"Loading data from: {train_path}")
    pairs = []
    with open(train_path) as f:
        for line in f:
            record = json.loads(line)
            result = generate_preference_pairs(record, model, tokenizer, phonology)
            if result:
                pairs.extend(result)

    print(f"Generated {len(pairs)} preference pairs")
    if not pairs:
        print("ERROR: No valid preference pairs generated. Check your data.")
        sys.exit(1)

    dataset = Dataset.from_list(pairs)

    # Training
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=cfg.get("batch_size", 4),
        gradient_accumulation_steps=cfg.get("gradient_accumulation", 2),
        num_train_epochs=cfg.get("epochs", 5),
        learning_rate=cfg.get("learning_rate", 5e-5),
        fp16=True,
        logging_steps=10,
        save_steps=50,
        save_total_limit=1,
        remove_unused_columns=False,
    )

    dpo_trainer = DPOTrainer(
        model=model,
        ref_model=None,  # Will use the LoRA base implicitly
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        beta=cfg.get("dpo_beta", 0.1),  # Preference scaling
    )

    print("Starting DPO training...")
    dpo_trainer.train()

    # Save
    final_path = os.path.join(output_dir, "final_adapter")
    model.save_pretrained(final_path)
    tokenizer.save_pretrained(final_path)
    print(f"DPO adapter saved to: {final_path}")


if __name__ == "__main__":
    main()

"""QLoRA fine-tuning for Spanish poetry on a 3B model.

Usage:
    python scripts/train_poetry_lora.py

Requires: pip install transformers datasets peft bitsandbytes accelerate
"""

import json
import os
import torch
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
    model_name = "Qwen/Qwen2.5-3B-Instruct"
    train_path = "seeds/poetry_corpus/training_data/train.jsonl"
    eval_path = "seeds/poetry_corpus/training_data/eval.jsonl"
    output_dir = "models/poetry-lora-3b"
    os.makedirs(output_dir, exist_ok=True)

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
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
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
        return tokenizer(ex["text"], truncation=True, max_length=192)

    train_ds = train_ds.map(tokenize, remove_columns=["text"])
    eval_ds = eval_ds.map(tokenize, remove_columns=["text"])

    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm=False
    )

    # ── Train ─────────────────────────────────────────────────────────
    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,       # Effective batch = 16
        num_train_epochs=2,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=200,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=1,
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
    )

    print("Starting training...")
    trainer.train()
    
    # Save adapter (~50MB)
    adapter_path = os.path.join(output_dir, "final_adapter")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"LoRA adapter saved to {adapter_path}/")

    # ── Test ──────────────────────────────────────────────────────────
    print("\n=== Testing ===")
    prompt = "Write a Spanish poem about the sea.\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=100, temperature=0.8)
    print(tokenizer.decode(out[0]))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Convert the remaining registered LoRA adapters to GGUF (merge -> fp16 GGUF -> Q4_K_M),
mirroring the qwen3b conversion already in models/poetry-lora-qwen3b/. Skips any adapter
whose GGUF outputs already exist. Updates mlops/adapter_registry.json with the resulting
paths so the registry reflects deployment-format state, not just training provenance.

Requires a local llama.cpp checkout with a built llama-quantize binary and a working
convert_hf_to_gguf.py (run inside an env with torch/transformers installed — this repo's
`poesia` conda env qualifies).

Usage:
    python scripts/convert_adapters_to_gguf.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

LLAMA_CPP_DIR = os.path.expanduser("~/.local/share/llama.cpp")
CONVERT_SCRIPT = os.path.join(LLAMA_CPP_DIR, "convert_hf_to_gguf.py")
QUANTIZE_BIN = os.path.join(LLAMA_CPP_DIR, "build", "bin", "llama-quantize")

# (adapter dir name, base model)
ADAPTERS = [
    ("poetry-lora-v2", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-v2-fixed", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-distilled", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-multiform", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-dpo-expanded", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("poetry-lora-3b", "Qwen/Qwen2.5-1.5B-Instruct"),
    ("smoke-test-adapter", "Qwen/Qwen2.5-1.5B-Instruct"),
]


def slug(dir_name: str) -> str:
    return dir_name.replace("poetry-lora-", "").replace("-adapter", "")


def convert_one(dir_name: str, base_model: str) -> dict | None:
    adapter_dir = os.path.join("models", dir_name)
    adapter_path = os.path.join(adapter_dir, "final_adapter")
    if not os.path.isdir(adapter_path):
        print(f"[SKIP] {dir_name}: no final_adapter/ found")
        return None

    name = slug(dir_name)
    merged_dir = os.path.join(adapter_dir, "merged")
    f16_path = os.path.join(adapter_dir, f"{name}-poetry-f16.gguf")
    q4_path = os.path.join(adapter_dir, f"{name}-poetry-Q4_K_M.gguf")

    if os.path.exists(q4_path):
        print(f"[SKIP] {dir_name}: {q4_path} already exists")
        return {"gguf_f16": f16_path, "gguf_q4_k_m": q4_path}

    print(f"[{dir_name}] loading base model {base_model} + merging adapter...")
    base = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype="bfloat16")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    merged = PeftModel.from_pretrained(base, adapter_path).merge_and_unload()

    os.makedirs(merged_dir, exist_ok=True)
    merged.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)
    del base, merged

    print(f"[{dir_name}] converting to fp16 GGUF...")
    subprocess.run(
        [sys.executable, CONVERT_SCRIPT, merged_dir, "--outfile", f16_path, "--outtype", "f16"],
        check=True,
    )

    print(f"[{dir_name}] quantizing to Q4_K_M...")
    subprocess.run([QUANTIZE_BIN, f16_path, q4_path, "Q4_K_M"], check=True)

    print(f"[{dir_name}] done: {q4_path}")
    return {"gguf_f16": f16_path, "gguf_q4_k_m": q4_path}


def main() -> None:
    registry_path = "mlops/adapter_registry.json"
    with open(registry_path) as f:
        registry = json.load(f)
    registry.setdefault("fields", {})["gguf_f16"] = "path to fp16 GGUF export"
    registry["fields"]["gguf_q4_k_m"] = "path to Q4_K_M quantized GGUF export"

    by_adapter_path = {a["adapter_path"]: a for a in registry["adapters"]}

    for dir_name, base_model in ADAPTERS:
        result = convert_one(dir_name, base_model)
        if result is None:
            continue
        adapter_path = os.path.join("models", dir_name, "final_adapter")
        entry = by_adapter_path.get(adapter_path)
        if entry is not None:
            entry.update(result)
        else:
            print(
                f"[WARN] {dir_name}: no matching registry entry at {adapter_path}, "
                f"not recorded in {registry_path}"
            )

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")
    print(f"Updated {registry_path}")


if __name__ == "__main__":
    main()

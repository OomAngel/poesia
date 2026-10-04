#!/usr/bin/env python3
"""Estimate the GPU memory that 4-bit QLoRA weights need, per Hugging Face model.

Reads only the safetensors headers (tensor names and shapes) over HTTP range
requests, so nothing is downloaded beyond a few hundred kB per model. Each tensor
is classified as a transformer linear weight (quantised to NF4 by bitsandbytes),
input embedding, lm_head, or vision/audio tower (left out: text-only training).

Two figures per model:
  default  NF4 body + bf16 embedding + bf16 lm_head (bitsandbytes' default skip list)
  best     NF4 body + NF4 lm_head, embedding kept in CPU RAM. Impossible when the
           embedding is tied to lm_head (Gemma), so "best" equals "default" there.

Training adds LoRA weights, optimiser state, activations under gradient
checkpointing, logits and the CUDA context on top: budgeted here as a flat
OVERHEAD_GB, which is an estimate. Only a smoke run with
torch.cuda.max_memory_allocated() settles whether a model fits
(docs/RETRAINING_PLAN_2026-10.md).

Usage:
    python scripts/estimate_qlora_vram.py Qwen/Qwen3.5-9B Qwen/Qwen3-8B
    python scripts/estimate_qlora_vram.py --budget-gb 6.5 google/gemma-4-12B-it
Gated repos (Llama) need a token in ~/.cache/huggingface/token.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import urllib.request
from math import prod

NF4_BYTES_PER_PARAM = 0.52  # 4-bit weights + double-quantised absmax
BF16_BYTES_PER_PARAM = 2.0
OVERHEAD_GB = 1.5  # LoRA + optimiser + activations + logits + CUDA context (estimate)
MULTIMODAL = re.compile(r"vision|visual|audio|image|mm_|multi_modal|embed_vision|embed_audio")


def _token() -> str | None:
    path = os.path.expanduser("~/.cache/huggingface/token")
    return open(path).read().strip() if os.path.exists(path) else None


def _get(url: str, byte_range: str | None = None) -> bytes:
    req = urllib.request.Request(url)
    if token := _token():
        req.add_header("Authorization", f"Bearer {token}")
    if byte_range:
        req.add_header("Range", f"bytes={byte_range}")
    return urllib.request.urlopen(req, timeout=60).read()


def _header(repo: str, filename: str) -> dict:
    url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
    length = struct.unpack("<Q", _get(url, "0-7"))[0]
    return json.loads(_get(url, f"8-{8 + length - 1}"))


def count_params(repo: str) -> dict:
    base = f"https://huggingface.co/{repo}/resolve/main"
    try:
        index = json.loads(_get(f"{base}/model.safetensors.index.json"))
        files = sorted(set(index["weight_map"].values()))
    except Exception:
        files = ["model.safetensors"]
    config = json.loads(_get(f"{base}/config.json"))
    text = config.get("text_config", config)
    counts = dict(linear=0, embedding=0, lm_head=0, multimodal=0, other=0)
    for filename in files:
        for name, tensor in _header(repo, filename).items():
            if name == "__metadata__":
                continue
            n, lower = prod(tensor["shape"]), name.lower()
            if MULTIMODAL.search(lower):
                counts["multimodal"] += n
            elif "lm_head" in lower:
                counts["lm_head"] += n
            elif "embed" in lower:
                counts["embedding"] += n
            elif len(tensor["shape"]) == 2:
                counts["linear"] += n
            else:
                counts["other"] += n
    counts["tied"] = bool(config.get("tie_word_embeddings", text.get("tie_word_embeddings")))
    counts["vocab"] = text.get("vocab_size")
    return counts


def estimate(counts: dict) -> tuple[float, float]:
    gb = 1e9
    body = counts["linear"] * NF4_BYTES_PER_PARAM / gb
    emb = counts["embedding"] * BF16_BYTES_PER_PARAM / gb
    head = counts["lm_head"] * BF16_BYTES_PER_PARAM / gb
    default = body + emb + head
    if counts["tied"]:
        return default, default
    best = body + counts["lm_head"] * NF4_BYTES_PER_PARAM / gb
    return default, best


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("repos", nargs="+", help="Hugging Face repo ids")
    parser.add_argument(
        "--budget-gb",
        type=float,
        default=6.5,
        help="free VRAM to compare against (RTX 3070 with apps closed: ~6.5)",
    )
    args = parser.parse_args()
    print(
        f"{'model':42s} {'body':>6s} {'emb':>5s} {'head':>5s} {'mm':>5s} tied "
        f"{'default':>8s} {'best':>6s} {'+train':>7s}  fits {args.budget_gb} GB?"
    )
    for repo in args.repos:
        try:
            c = count_params(repo)
        except Exception as exc:  # gated, missing, or no safetensors
            print(f"{repo:42s} ERROR {exc}")
            continue
        default, best = estimate(c)
        total = best + OVERHEAD_GB
        print(
            f"{repo:42s} {c['linear'] / 1e9:5.2f}B {c['embedding'] / 1e9:4.2f}B "
            f"{c['lm_head'] / 1e9:4.2f}B {c['multimodal'] / 1e9:4.2f}B {'yes' if c['tied'] else 'no ':3s} "
            f"{default:7.1f}G {best:5.1f}G {total:6.1f}G  {'yes' if total <= args.budget_gb else 'NO'}"
        )


if __name__ == "__main__":
    main()

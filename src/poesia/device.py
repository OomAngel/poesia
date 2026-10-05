"""Shared CUDA-usability probe.

``torch.cuda.is_available()`` only checks that a CUDA-capable GPU and driver
are visible to the process — it says nothing about whether the *installed
PyTorch build* actually ships compiled kernels for that GPU's compute
capability. Older cards (e.g. Maxwell, compute capability 5.0) are steadily
being dropped from official wheels as NVIDIA itself deprecates them in the
CUDA toolkit, so ``is_available()`` returning True can still blow up mid-run
with an opaque ``cudaErrorNoKernelImageForDevice`` instead of a clean,
early, actionable fallback.

This module centralizes the one reliable check across the codebase (used by
``poesia.memoria.embeddings`` and the ``lora``/``llama_cpp`` generation
backends): actually run a trivial kernel and see if it works.
``bnb_4bit_usable`` applies the same idea to bitsandbytes, which the
``lora`` backend needs on top of a working torch build.
"""

from __future__ import annotations


def cuda_usable() -> bool:
    """True only if a trivial CUDA op actually runs on the visible GPU.

    Parsing ``get_device_capability()``/``get_arch_list()`` is brittle — the
    string format has changed across PyTorch versions, and it doesn't
    distinguish SASS from PTX (forward-compatible) support. Running one real
    op is cheap and exercises the actual kernel-selection path directly.
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        (torch.zeros(1, device="cuda") + 1).cpu()
    except Exception:
        return False
    return True


def bnb_4bit_usable() -> bool:
    """True only if bitsandbytes 4-bit quantization actually runs on the visible GPU.

    This is what ``LoRAClient`` (transformers + bitsandbytes NF4) needs, and it
    is stricter than :func:`cuda_usable`: a torch build can ship kernels for a
    GPU that bitsandbytes has none for. The laptop's Quadro M1000M (compute
    capability 5.0) is that case with torch's cu126 wheels, which include
    sm_50, while bitsandbytes' Linux CUDA 12.x builds start at sm_60 (and the
    laptop's env does not install bitsandbytes at all). Same approach as
    ``cuda_usable``: run one real op rather than parse capability tables.
    """
    if not cuda_usable():
        return False
    try:
        import bitsandbytes.functional as bnb_functional
        import torch

        bnb_functional.quantize_4bit(
            torch.ones(64, device="cuda", dtype=torch.float16), quant_type="nf4"
        )
    except Exception:
        return False
    return True


MEMORY_LAYOUTS = ("default", "low_vram")


def four_bit_placement(layout: str = "default") -> tuple[dict, str | dict]:
    """Extra BitsAndBytesConfig kwargs and the ``device_map`` for a 4-bit model.

    ``default``: bitsandbytes' own behaviour (lm_head stays bf16), ``device_map="auto"``.
    ``low_vram`` (docs/RETRAINING_PLAN_2026-10.md §3): lm_head is quantized too (empty skip
    list) and the whole model loads on GPU 0. Training additionally moves the input
    embedding to CPU RAM with ``offload_input_embeddings`` after loading. (accelerate's own
    CPU placement treats such modules as offloaded and copies their weights to the GPU on
    every forward, which failed under WSL with "CUDA driver error: device not ready".)
    """
    if layout == "default":
        return {}, "auto"
    if layout != "low_vram":
        raise ValueError(f"memory_layout must be one of {MEMORY_LAYOUTS}, not {layout!r}")
    return {"llm_int8_skip_modules": []}, {"": 0}


def offload_input_embeddings(model, compute_device: str = "cuda"):
    """Keep the (frozen) input embedding in CPU RAM; run everything else on ``compute_device``.

    Token ids are moved to the CPU before the lookup and the embeddings back to
    ``compute_device`` after it, so no weight is copied per step. Frees the embedding's
    VRAM (about 1.2 GB in bf16 for Qwen3-8B). Returns the model.
    """
    emb = model.get_input_embeddings()
    out_emb = getattr(model, "get_output_embeddings", lambda: None)()
    if out_emb is not None and out_emb.weight is emb.weight:
        raise ValueError(
            "input and output embeddings are tied (e.g. Qwen3-4B): moving the embedding would "
            "move lm_head too; use memory_layout 'default' for this model"
        )
    emb.to("cpu")
    emb.register_forward_pre_hook(lambda _m, args: tuple(a.to("cpu") for a in args))
    emb.register_forward_hook(lambda _m, _args, out: out.to(compute_device))
    return model

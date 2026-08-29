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

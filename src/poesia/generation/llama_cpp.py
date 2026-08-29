"""LlamaCppLoRAClient — GGUF/llama.cpp fallback for pre-Maxwell-era GPUs.

``LoRAClient`` (see llm_client.py) loads the fine-tuned poetry adapter via
transformers + bitsandbytes 4-bit quantization, which requires CUDA compute
capability >= 6.0 (bitsandbytes' hard floor). GPUs below that — e.g. a
Quadro M1000M (CC 5.0, Maxwell) — can't take that path at all: PyTorch's
prebuilt wheels don't even ship sm_50 kernels anymore, so the model either
refuses to load onto the GPU or silently falls back to (unusably slow) CPU.

llama.cpp sidesteps this because it compiles its own CUDA kernels for
whatever architecture you target at build time, independent of upstream
PyTorch/bitsandbytes wheel support. This client drives a GGUF export of the
same fine-tuned adapter through ``llama-cpp-python`` instead.

One-time setup to produce the GGUF file this client loads:
  1. Merge the LoRA adapter into its base model (``peft``'s
     ``merge_and_unload``) — llama.cpp's converter wants plain weights, not
     a base + adapter pair.
  2. Convert to GGUF (llama.cpp's ``convert_hf_to_gguf.py``) and quantize
     (``llama-quantize``, e.g. to Q4_K_M).
  3. Build ``llama-cpp-python`` from source targeting the GPU's own compute
     capability:
       CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=50" \\
         pip install llama-cpp-python --no-binary llama-cpp-python
     Do this in an isolated env — the resulting wheel is pinned to one CUDA
     arch and has no relation to the main project's torch/bitsandbytes pins.

If ``llama-cpp-python`` isn't importable (e.g. running from the main
``poesia`` env rather than the GPU-specific build env), ``generate()``/
``repair()`` raise ``LLMProviderError`` with the setup steps above rather
than crashing on import.
"""

from __future__ import annotations

import os
import time
from typing import Any

from poesia.exceptions import LLMProviderError
from poesia.generation.llm_client import LLMUsage


class LlamaCppLoRAClient:
    """Fine-tuned poetry model via a GGUF export, for pre-CC6.0 GPUs.

    Default model path: ``models/poetry-lora-qwen3b/qwen3b-poetry-Q4_K_M.gguf``
    """

    # Known GGUF outputs, tried in priority order (mirrors LoRAClient's
    # _KNOWN_ADAPTERS — same underlying adapter, converted to GGUF).
    _KNOWN_GGUF: list[str] = [
        "models/poetry-lora-qwen3b/qwen3b-poetry-Q4_K_M.gguf",
    ]

    def __init__(self, model_path: str | None = None, n_ctx: int = 512) -> None:
        self.usage: LLMUsage = LLMUsage()
        self.provider = "llama_cpp"
        self.n_ctx = n_ctx
        self._llm: Any = None

        if model_path is None:
            env_path = os.environ.get("LLAMACPP_MODEL_PATH")
            if env_path and os.path.exists(env_path):
                model_path = env_path
                print(f"[llama.cpp] Using model from LLAMACPP_MODEL_PATH: {model_path}")
            else:
                pkg_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                )
                for candidate_rel in self._KNOWN_GGUF:
                    candidate = os.path.join(pkg_root, candidate_rel)
                    if os.path.exists(candidate):
                        model_path = candidate
                        print(f"[llama.cpp] Found GGUF model: {candidate_rel}")
                        break
                if model_path is None:
                    print(
                        f"[llama.cpp] No GGUF model found. Tried: {', '.join(self._KNOWN_GGUF)}. "
                        "Set LLAMACPP_MODEL_PATH or run the merge/convert/quantize pipeline "
                        "(see module docstring)."
                    )

        self._model_path = model_path

    def _load(self) -> None:
        if self._llm is not None:
            return
        if not self._model_path or not os.path.exists(self._model_path):
            raise LLMProviderError(
                "No GGUF model found. Set LLAMACPP_MODEL_PATH or run the "
                "merge/convert/quantize pipeline (see llama_cpp.py module docstring) "
                f"to produce one of: {', '.join(self._KNOWN_GGUF)}.",
                provider="llama_cpp",
            )
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise LLMProviderError(
                "llama-cpp-python is not installed in this interpreter. This backend "
                "needs a CUDA build targeting the GPU's own compute capability, e.g.:\n"
                '  CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=<CC*10>" '
                "pip install llama-cpp-python\n"
                "Run this from the isolated env it was built in, not the main project env "
                "(see llama_cpp.py module docstring).",
                provider="llama_cpp",
            ) from e
        try:
            self._llm = Llama(
                model_path=self._model_path,
                n_gpu_layers=-1,
                n_ctx=self.n_ctx,
                verbose=False,
            )
        except Exception as e:
            raise LLMProviderError(
                f"Failed to load GGUF model '{self._model_path}': {e}", provider="llama_cpp"
            ) from e

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        self._load()
        self.usage = LLMUsage()
        t0 = time.time()
        max_new = 50 if "Write line" in prompt or "Output ONLY" in prompt else 100

        # Sequential, not batched: llama-cpp-python's high-level Llama.__call__
        # has no num_return_sequences equivalent, and a 2 GB Maxwell card has
        # no headroom for concurrent contexts anyway (see LoRAClient.generate
        # for the batched approach used on modern GPUs).
        results: list[str] = []
        for _ in range(n):
            out = self._llm(
                prompt,
                max_tokens=max_new,
                temperature=temperature,
                stop=["\n"],
            )
            text = out["choices"][0]["text"].strip().strip('"').strip("'")
            if text:
                results.append(text)
        self.usage.latency_ms = (time.time() - t0) * 1000
        return results or [""]

    def repair(self, line: str, defect_description: str) -> str:
        prompt = f'Fix this poetic line: {defect_description}\nLine: "{line}"\nOutput ONLY the corrected line.\n'
        candidates = self.generate(prompt, n=1, temperature=0.7)
        return candidates[0].strip().strip("\"'") if candidates else line

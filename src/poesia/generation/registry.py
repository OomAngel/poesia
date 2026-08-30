"""LLM Backend Registry — auto-discovery via decorators.

Usage:
    @register_llm("groq")
    class GroqLLMClient: ...

    client = get_llm("groq")   # -> GroqLLMClient instance
    client = get_llm("stub")   # -> StubLLMClient (built-in)
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

# Registry: name -> class
_llm_registry: dict[str, type] = {}

# Default params per backend (can be overridden by config/env)
_DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "stub": {},
    "groq": {"provider": "groq"},
    "gemini": {"provider": "gemini"},
    "openai": {"provider": "openai"},
    "auto": {"provider": "auto"},
    "route": {},
    "ollama": {"model": "gemma2:2b"},
    "lora": {},
    "llama_cpp": {},
    "outlines": {},
    "mlflow": {},
    "cloudflare": {"model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast"},
}


def register_llm(
    name: str, params: dict[str, Any] | None = None
) -> Callable[[type[Any]], type[Any]]:
    """Decorator: register an LLM client class under a name.

    Usage:
        @register_llm("groq")
        class GroqLLMClient:
            ...

    The decorated class must implement LLMClient protocol.
    """

    def decorator(cls: type) -> type:
        _llm_registry[name] = cls
        if params:
            _DEFAULT_PARAMS[name] = {**_DEFAULT_PARAMS.get(name, {}), **params}
        return cls

    return decorator


def get_llm(name: str, **overrides) -> Any:
    """Factory: get an LLM client instance by registered name.

    Args:
        name: Registered backend name ("groq", "ollama", "lora", etc.)
        **overrides: Override default params (e.g., model="custom-model")

    Returns:
        An instance of the registered LLM client class.

    Raises:
        ValueError: If the backend name is not registered.
    """
    # Lazy-import to avoid circular imports and heavy loads
    if name not in _llm_registry:
        _import_backend(name)

    if name not in _llm_registry:
        raise ValueError(
            f"Unknown LLM backend '{name}'. Registered: {', '.join(sorted(_llm_registry))}"
        )

    cls = _llm_registry[name]
    params = {**_DEFAULT_PARAMS.get(name, {}), **overrides}

    # Map params to constructor arguments
    if name == "lora":
        adapter_path = overrides.get(
            "adapter_path",
            os.environ.get("LORA_ADAPTER_PATH"),
        )
        if adapter_path:
            return cls(adapter_path=adapter_path)
        return cls()
    elif name == "llama_cpp":
        model_path = overrides.get(
            "model_path",
            os.environ.get("LLAMACPP_MODEL_PATH"),
        )
        if model_path:
            return cls(model_path=model_path)
        return cls()
    elif name in ("groq", "gemini", "openai", "auto"):
        return cls(provider=params.get("provider", name))
    elif name == "ollama":
        return cls(
            model=params.get("model", "gemma2:2b"),
            host=params.get("host", os.environ.get("OLLAMA_HOST")),
        )
    elif name == "mlflow":
        model_uri = overrides.get(
            "model_uri",
            os.environ.get("MLFLOW_MODEL_URI", ""),
        )
        return cls(model_uri=model_uri)
    elif name in ("stub", "outlines"):
        return cls()

    return cls(**params)


def _import_backend(name: str) -> None:
    """Lazy-import the module that registers a backend."""
    import importlib

    try:
        importlib.import_module(f"poesia.generation.{name}")
    except ImportError:
        pass


def list_backends() -> list[str]:
    """List all registered backend names."""
    # Ensure all are imported
    for module_name in (
        "stub",
        "groq",
        "gemini",
        "openai",
        "ollama",
        "lora",
        "llama_cpp",
        "outlines",
        "mlflow",
        "cloudflare",
    ):
        _import_backend(module_name)
    return sorted(_llm_registry.keys())


# ── Auto-register built-in backends ──────────────────────────────
from poesia.generation.cloudflare import CloudflareLLMClient  # noqa: E402
from poesia.generation.llama_cpp import LlamaCppLoRAClient  # noqa: E402
from poesia.generation.llm_client import (  # noqa: E402
    HostedLLMClient,
    LoRAClient,
    MLflowModelClient,
    OllamaClient,
    OutlinesClient,
    StubLLMClient,
)
from poesia.generation.router import RoutedLLMClient  # noqa: E402

_LLM_MAP = {
    "stub": StubLLMClient,
    "groq": HostedLLMClient,
    "gemini": HostedLLMClient,
    "openai": HostedLLMClient,
    "auto": HostedLLMClient,
    "route": RoutedLLMClient,
    "ollama": OllamaClient,
    "lora": LoRAClient,
    "llama_cpp": LlamaCppLoRAClient,
    "outlines": OutlinesClient,
    "mlflow": MLflowModelClient,
    "cloudflare": CloudflareLLMClient,
}

for name, cls in _LLM_MAP.items():
    if name not in _llm_registry:
        _llm_registry[name] = cls

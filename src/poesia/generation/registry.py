"""LLM Backend Registry — auto-discovery via decorators.

Usage:
    @register_llm("groq")
    class GroqLLMClient: ...

    client = get_llm("groq")   # -> GroqLLMClient instance
    client = get_llm("stub")   # -> StubLLMClient (built-in)
"""

from __future__ import annotations

import os
from typing import Any

# Registry: name -> class
_llm_registry: dict[str, type] = {}

# Default params per backend (can be overridden by config/env)
_DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "stub": {},
    "groq": {"model": "llama-3.3-70b-versatile", "provider": "groq"},
    "gemini": {"provider": "gemini"},
    "openai": {"provider": "openai"},
    "auto": {"provider": "auto"},
    "ollama": {"model": "gemma2:2b"},
    "lora": {},
    "outlines": {},
}


def register_llm(name: str, params: dict[str, Any] | None = None) -> callable:
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
            f"Unknown LLM backend '{name}'. "
            f"Registered: {', '.join(sorted(_llm_registry))}"
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
    elif name in ("groq", "gemini", "openai", "auto"):
        return cls(provider=params.get("provider", name))
    elif name == "ollama":
        return cls(
            model=params.get("model", "gemma2:2b"),
            host=params.get("host", os.environ.get("OLLAMA_HOST")),
        )
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
    for module_name in ("stub", "groq", "gemini", "openai", "ollama", "lora", "outlines"):
        _import_backend(module_name)
    return sorted(_llm_registry.keys())


# ── Auto-register built-in backends ──────────────────────────────
from poesia.generation.llm_client import (  # noqa: E402
    HostedLLMClient,
    LoRAClient,
    OllamaClient,
    OutlinesClient,
    StubLLMClient,
)

_LLM_MAP = {
    "stub": StubLLMClient,
    "groq": HostedLLMClient,
    "gemini": HostedLLMClient,
    "openai": HostedLLMClient,
    "auto": HostedLLMClient,
    "ollama": OllamaClient,
    "lora": LoRAClient,
    "outlines": OutlinesClient,
}

for name, cls in _LLM_MAP.items():
    if name not in _llm_registry:
        _llm_registry[name] = cls

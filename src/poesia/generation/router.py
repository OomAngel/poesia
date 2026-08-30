"""LLM routing chain — ordered fallback across providers.

The default chain is ``groq → openai → ollama → llama_cpp → stub``: each step is
a more degraded but still functional fallback, ending in the deterministic
offline stub. Register this client as ``route`` in ``registry`` so
``poesia write --llm route`` uses the chain; the router returns the first
provider that actually serves the request and falls back on any failure
(missing key, 401/429, model-not-found, unreachable local service).
"""

from __future__ import annotations

from typing import Any

# Ordered fallback chain. ``model`` is a per-provider override; omitted means
# "use that provider's own default". This is the single source of truth for
# routing — not a hardcoded default scattered across registry/llm_client.
DEFAULT_ROUTE: list[dict[str, Any]] = [
    {"provider": "llama_cpp"},  # fine-tuned qwen3b-poetry GGUF (primary; CPU/CUDA)
    {"provider": "groq", "model": "qwen/qwen3.8-27b"},  # hosted fallback
    {"provider": "openai"},  # default gpt-4o-mini (OPENAI_API_KEY)
    {"provider": "ollama"},  # local model (OLLAMA_HOST / gemma2:2b)
    {"provider": "stub"},  # deterministic offline floor
]


class RoutedLLMClient:
    """LLMClient that tries providers in order, falling back on failure.

    Implements the same ``generate`` / ``repair`` surface as the other clients
    so it drops into ``ConstrainedLoop`` / ``CandidateGenerator`` unchanged.
    """

    def __init__(self, route: list[dict[str, Any]] | None = None) -> None:
        self._route = route or DEFAULT_ROUTE
        self.provider = "route"
        self.model = None

    def _iter_clients(self):
        # Lazy import to avoid a circular import with registry.py.
        from poesia.generation.registry import get_llm

        for entry in self._route:
            name = entry["provider"]
            overrides = {k: v for k, v in entry.items() if k != "provider"}
            try:
                yield name, get_llm(name, **overrides)
            except Exception:  # noqa: BLE001 — provider unavailable, try next
                continue

    def _record(self, client: Any, name: str) -> None:
        """Expose the actual provider/model used, for CLI logging."""
        self.model = getattr(client, "model", None)
        self.provider = getattr(client, "provider", None) or name

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        last_error: Exception | None = None
        for name, client in self._iter_clients():
            try:
                result = client.generate(prompt, n=n, temperature=temperature)
            except Exception as exc:  # noqa: BLE001 — fall back to next provider
                last_error = exc
                continue
            self._record(client, name)
            return result
        if last_error is not None:
            raise last_error
        raise RuntimeError("LLM route exhausted — no usable provider")

    def repair(self, line: str, defect_description: str) -> str:
        last_error: Exception | None = None
        for name, client in self._iter_clients():
            repair = getattr(client, "repair", None)
            if repair is None:
                continue
            try:
                result = repair(line, defect_description)
            except Exception as exc:  # noqa: BLE001 — fall back to next provider
                last_error = exc
                continue
            self._record(client, name)
            return result
        if last_error is not None:
            raise last_error
        raise RuntimeError("LLM route exhausted — no usable provider (repair)")

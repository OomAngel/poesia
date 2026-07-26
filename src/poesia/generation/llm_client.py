"""Abstract LLM client interface.

Concrete backends (hosted API, llama.cpp local inference, transformers local
inference) implement this Protocol so the generation loop stays decoupled
from any single provider. This mirrors the "typed port" discipline used
elsewhere: no SDK-specific import should leak into evaluation/ or phonology/.
"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Minimal interface the generation loop needs from any LLM backend."""

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        """Return `n` candidate completions for `prompt`."""
        ...

    def repair(self, line: str, defect_description: str) -> str:
        """Ask the model to fix one explicit, named defect in a single line."""
        ...


class StubLLMClient:
    """Deterministic no-op client for tests and offline development.

    Returns the prompt itself (or a trivially modified variant) instead of
    calling any real model. Useful for exercising the generation loop's
    control flow without network access or GPU/CPU inference cost.
    """

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        return [f"{prompt} [candidate {i}]" for i in range(n)]

    def repair(self, line: str, defect_description: str) -> str:
        return f"{line} [repaired: {defect_description}]"

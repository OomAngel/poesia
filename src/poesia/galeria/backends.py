"""Image-generation backend port.

Mirrors the `poesia.generation.llm_client.LLMClient` Protocol discipline:
GalerIA's illustration logic (composition, auca layout, PDF export) must
never import a specific image-gen SDK directly. Concrete backends
(`openai`, `replicate`, local `diffusers`) implement this Protocol.
"""

from __future__ import annotations

from typing import Protocol


class ImageBackend(Protocol):
    """Minimal interface GalerIA needs from any image-generation backend."""

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        """Return raw image bytes (PNG) for a text prompt + optional style tag."""
        ...


class StubImageBackend:
    """Deterministic no-op backend for tests and offline development.

    Returns a tiny valid 1x1 PNG instead of calling any real image model.
    """

    _MINIMAL_PNG = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        return self._MINIMAL_PNG


# --- Candidate real backends (Phase 2, not yet implemented) -----------------
#
# OpenAIImageBackend    -> wraps `openai` (DALL-E / gpt-image), hosted, strong
#                          stylization via prompt engineering.
# ReplicateImageBackend -> wraps `replicate`, hosted, access to SDXL and
#                          specialized woodcut/line-art models (good fit for
#                          a "grabado español" auca aesthetic).
# DiffusersImageBackend -> wraps HuggingFace `diffusers` for local SDXL,
#                          offline, GPU-heavy.

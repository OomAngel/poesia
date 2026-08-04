"""WriteConfig — single source of truth for generation parameters.

Replaces the 16-parameter god function in cli.py with a typed dataclass
that can be built, validated, logged, and serialised.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class WriteConfig:
    """All parameters for a poem generation request.

    Usage:
        config = WriteConfig.build(
            theme="luna",
            form="soneto",
            llm="groq",
            tone=["melancholic"],
        )
    """

    # Required
    theme: str

    # Optional with defaults
    form: str = "soneto"
    language: str = "es"
    n_candidates: int = 16
    max_repair_attempts: int = 2
    temperature: float = 0.9

    # LLM
    llm: str = "stub"
    llm_provider: str | None = None  # resolved at runtime

    # Brief / enrichment
    use_brief: bool = False
    semantic: bool = False  # semantic theme/novelty scoring without context
    brief_level: Literal["minimal", "standard", "maximal"] = "standard"
    tone: list[str] | None = None
    seeds: list[str] | None = None
    movement: str | None = None

    # Library
    use_library: bool = False
    save: bool = False
    tags: list[str] | None = None

    # Display
    show_alternatives: int = 0
    show_retrieval: bool = False
    interactive: bool = False
    yes: bool = False

    # Form override (for variable-length forms)
    lines: int | None = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    config_source: str = "CLI"  # CLI, API, config file

    @classmethod
    def build(
        cls,
        theme: str,
        form: str = "soneto",
        language: str = "es",
        llm: str = "stub",
        tone: list[str] | None = None,
        seeds: list[str] | None = None,
        **kwargs,
    ) -> WriteConfig:
        """Convenience builder with validation."""
        from poesia.forms.definitions import FORM_REGISTRY

        if form not in FORM_REGISTRY:
            known = ", ".join(sorted(FORM_REGISTRY))
            raise ValueError(f"Unknown form '{form}'. Known: {known}")

        if language not in ("es", "en", "nl"):
            raise ValueError(f"Unsupported language '{language}'. Use es, en, nl.")

        return cls(
            theme=theme,
            form=form,
            language=language,
            llm=llm,
            tone=tone,
            seeds=seeds,
            **kwargs,
        )

    def to_dict(self) -> dict:
        """Serialise for logging / provenance."""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

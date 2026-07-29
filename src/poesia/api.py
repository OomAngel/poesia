"""PoesIA Facade — clean Python API for poem generation.

Usage:
    from poesia.api import write_poem

    # Simplest case
    result = write_poem("luna", form="haiku")

    # Full config
    result = write_poem(
        "soledad",
        form="soneto",
        language="es",
        llm="groq",
        tone=["melancholic", "tender"],
        save=True,
    )
    print(result.text)
    print(result.metrics)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class PoemResult:
    """Result of a poem generation call."""

    text: str
    lines: list[str]
    form: str
    language: str
    theme: str
    llm: str
    metrics: dict[str, float] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_result: Any = None  # The full LoopResult for advanced use


def write_poem(
    theme: str,
    form: str = "soneto",
    language: str = "es",
    llm: str = "stub",
    n_candidates: int = 16,
    tone: list[str] | None = None,
    seeds: list[str] | None = None,
    use_brief: bool = False,
    brief_level: Literal["minimal", "standard", "maximal"] = "standard",
    save: bool = False,
    tags: list[str] | None = None,
    interactive: bool = False,
    yes: bool = False,
    lines: int | None = None,
    movement: str | None = None,
    hooks: list | None = None,
) -> PoemResult:
    """Generate a poem with a single function call.

    Args:
        theme: Central theme for the poem.
        form: Poetic form (soneto, haiku, romance, sonnet_shakespearean).
        language: Language code (es, en, nl).
        llm: LLM backend (stub, groq, gemini, openai, ollama, lora, outlines).
        n_candidates: Candidates per line position.
        tone: Tonal qualities (e.g., ["melancholic", "tender"]).
        seeds: Seed words for expansion.
        use_brief: Use BriefBuilder for rich context.
        brief_level: Verbosity level.
        save: Save to library.
        tags: Tags for saved poem.
        interactive: Human line selection.
        yes: Skip privacy prompt.
        lines: Override line count (for romance).
        movement: Filter by literary movement.
        hooks: Optional list of GenerationHook instances.

    Returns:
        PoemResult with generated text and metadata.
    """
    from poesia.config.types import WriteConfig
    from poesia.generation.constrained_loop import ConstrainedLoop
    from poesia.generation.registry import get_llm

    # Build config
    config = WriteConfig.build(
        theme=theme,
        form=form,
        language=language,
        llm=llm,
        n_candidates=n_candidates,
        tone=tone,
        seeds=seeds,
        brief_level=brief_level,
        use_brief=use_brief,
        save=save,
        tags=tags,
        interactive=interactive,
        yes=yes,
        lines=lines,
        movement=movement,
        config_source="API",
    )

    # Resolve LLM
    llm_client = get_llm(config.llm)

    # Build the loop
    loop = ConstrainedLoop(
        language=config.language,
        form=config.form,
        llm=llm_client,
    )

    # Attach hooks
    if hooks:
        for hook in hooks:
            loop.add_hook(hook)

    # Run
    result = loop.run(
        theme=config.theme,
        n_candidates=config.n_candidates,
        tone=config.tone,
        seeds=config.seeds,
        brief_level=config.brief_level,
        total_lines_override=config.lines,
        movement=config.movement,
    )

    return PoemResult(
        text="\n".join(result.lines),
        lines=result.lines,
        form=config.form,
        language=config.language,
        theme=config.theme,
        llm=config.llm,
        raw_result=result,
    )

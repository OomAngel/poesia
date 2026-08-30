"""Tests for the draft-then-revise path (run_draft)."""

from __future__ import annotations

from poesia.generation.constrained_loop import ConstrainedLoop


class _FakeDraftLLM:
    """Returns a fixed multi-line poem; repairs by substituting a fixed string."""

    def __init__(self, poem: str, repair_to: str | None = None):
        self.poem = poem
        self.repair_to = repair_to

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        return [self.poem]

    def repair(self, line: str, defect_description: str) -> str:
        return self.repair_to if self.repair_to is not None else line


def test_build_draft_prompt_has_structure_and_quality() -> None:
    """The whole-poem prompt carries form structure and quality directives."""
    loop = ConstrainedLoop(language="en", form="sonnet_shakespearean")
    prompt = loop._build_draft_prompt("the orchard", ["reverent"])
    assert "14 lines" in prompt
    assert "ABABCDCDEFEFGG" in prompt
    assert "volta" in prompt
    assert "concrete imagery" in prompt
    assert "corrected afterward" in prompt


def test_run_draft_generates_and_splits_lines() -> None:
    """A multi-line completion is split into the form's lines."""
    poem = (
        "The moon hangs in the quiet tree tonight\n"
        "And counts the apples with a silver eye\n"
        "A machine learns the dark, the bloom, the light\n"
    )
    loop = ConstrainedLoop(language="en", form="haiku")
    loop._llm = _FakeDraftLLM(poem)  # noqa: SLF001 — test seam
    result = loop.run_draft(theme="the orchard")
    assert len(result.lines) == 3
    assert result.lines[0] == "The moon hangs in the quiet tree tonight"


def test_run_draft_empty_response_is_safe() -> None:
    """An empty/blank completion yields no lines rather than crashing."""
    loop = ConstrainedLoop(language="en", form="haiku")
    loop._llm = _FakeDraftLLM("")  # noqa: SLF001
    result = loop.run_draft(theme="the orchard")
    assert result.lines == []

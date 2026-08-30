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


def test_build_draft_prompt_matches_training_format() -> None:
    """The whole-poem prompt uses the fine-tune's training prompt shape."""
    loop = ConstrainedLoop(language="es", form="soneto")
    prompt = loop._build_draft_prompt("la luna", ["reverent"])
    assert prompt.startswith("Write a soneto in Spanish.\n")
    assert "Rhyme scheme: ABBAABBACDCDCD." in prompt
    assert "Theme: la luna." in prompt


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
    assert result.warnings  # the empty completion must be surfaced, not silent


def test_run_draft_short_completion_warns_instead_of_silently_shipping() -> None:
    """A draft shorter than the form's line count is a degraded-provider signal.

    A router falling all the way through to the offline stub (which only ever
    emits one line, regardless of the whole-poem prompt it was given) must not
    be mistaken for a complete poem — the gap has to show up in `warnings`.
    """
    loop = ConstrainedLoop(language="es", form="soneto")
    loop._llm = _FakeDraftLLM("Solo llega una línea de un proveedor degradado")  # noqa: SLF001
    result = loop.run_draft(theme="the orchard")
    assert len(result.lines) == 1
    assert any("1/14 lines" in w for w in result.warnings)

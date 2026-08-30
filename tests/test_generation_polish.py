"""Tests for the --polish fluency gate (stiff-line detection + repair)."""

from __future__ import annotations

from poesia.evaluation.scorer import ScoredCandidate
from poesia.generation.constrained_loop import (
    ConstrainedLoop,
    _fluency_defect_description,
    _line_is_stiff,
)


class _FakeLLM:
    """Deterministic fake: a fixed fluency verdict and an optional repair result."""

    def __init__(self, verdict: str, repair_result: str | None = None, fail: bool = False):
        self.verdict = verdict
        self.repair_result = repair_result
        self.fail = fail
        self.repair_calls = 0

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        if self.fail:
            raise RuntimeError("provider down")
        return [self.verdict]

    def repair(self, line: str, defect_description: str) -> str:
        self.repair_calls += 1
        return self.repair_result or line


def test_line_is_stiff_detects_stiff() -> None:
    assert _line_is_stiff("any line", "en", _FakeLLM("STIFF")) is True


def test_line_is_stiff_accepts_natural() -> None:
    assert _line_is_stiff("any line", "en", _FakeLLM("NATURAL")) is False


def test_line_is_stiff_fails_open_on_provider_error() -> None:
    assert _line_is_stiff("any line", "en", _FakeLLM("NATURAL", fail=True)) is False


def test_line_is_stiff_fails_open_on_unparsable() -> None:
    assert _line_is_stiff("any line", "en", _FakeLLM("something unexpected")) is False


def test_fluency_defect_includes_metre_and_rhyme() -> None:
    defect = _fluency_defect_description(10, "M")
    assert "natural and fluent" in defect
    assert "exactly 10 syllables" in defect
    assert "rhyme key 'M'" in defect


def test_fluency_defect_omits_rhyme_when_none() -> None:
    defect = _fluency_defect_description(5, None)
    assert "rhyme" not in defect
    assert "exactly 5 syllables" in defect


def test_polish_line_is_noop_when_natural() -> None:
    """A naturally-reading line is returned unchanged and never repaired."""
    loop = ConstrainedLoop(language="en", form="haiku")
    llm = _FakeLLM("NATURAL")
    loop._llm = llm  # noqa: SLF001 — test seam
    scan = loop._phonology.scan_line("the moon hangs there")
    candidate = ScoredCandidate(line="the moon hangs there", scan=scan, score=1.0, breakdown={})

    result = loop._polish_line(candidate, 5, None, [], 2)

    assert result is candidate
    assert llm.repair_calls == 0

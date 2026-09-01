"""Gap #12: run_draft() sometimes concatenates two disconnected fragments into
one drafted line (e.g. "tranquila alta.", "brinda, ansia.") instead of one
coherent thought. These lines land far short of the target syllable count, so
the old defect message ("has N syllables but must be exactly M") just invited
the repair LLM to pad the fragment rather than rewrite it. `_metre_defect_text`
should call out a severe undershoot explicitly using these reproduced examples
as ground truth.
"""

from __future__ import annotations

from poesia.generation.constrained_loop import _line_is_stiff, _metre_defect_text
from poesia.phonology.spanish import SpanishPhonology

# Reproduced fragment-concatenation lines from a live "el mar" hybrid trial
# (see docs/GENERATION_QUALITY_PLAN.md gap #12).
_FRAGMENT_LINES = [
    "tranquila alta.",
    "brinda, ansia.",
    "pura, elida.",
    "corazón, espíritu.",
]

_TARGET_SYLLABLES = 11  # hendecasyllable, e.g. a soneto line


def test_reproduced_fragment_lines_are_flagged_as_severe_undershoot() -> None:
    phonology = SpanishPhonology()
    for line in _FRAGMENT_LINES:
        actual = phonology.scan_line(line).metrical_syllable_count
        desc = _metre_defect_text(actual, _TARGET_SYLLABLES)
        assert "disconnected fragments" in desc, f"{line!r} ({actual} syll) not flagged: {desc!r}"
        assert "rewrite it as a single coherent" in desc


def test_near_miss_undershoot_keeps_plain_syllable_message() -> None:
    # 9/11 and 10/11 are the near-misses seen in the same trial that a small
    # syllable-count nudge genuinely can fix — must not be treated as fragments.
    for actual in (9, 10):
        desc = _metre_defect_text(actual, _TARGET_SYLLABLES)
        assert "disconnected fragments" not in desc
        assert f"has {actual} syllables but must be exactly {_TARGET_SYLLABLES}" in desc


def test_overshoot_keeps_plain_syllable_message() -> None:
    desc = _metre_defect_text(13, _TARGET_SYLLABLES)
    assert "disconnected fragments" not in desc
    assert "has 13 syllables but must be exactly 11" in desc


class _CapturingLLM:
    """Records the prompt sent to generate() and returns a fixed verdict."""

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict
        self.prompts: list[str] = []

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        self.prompts.append(prompt)
        return [self.verdict]


def test_stiffness_prompt_names_the_fragment_pattern() -> None:
    """A prior diagnostic found the polish-path coherence check scored only 60%
    on these reproduced fragment lines, misclassifying all 4 as COHERENT — it
    was never told to look for "two disconnected fragments" at all. The prompt
    must name that failure mode explicitly, using a reproduced example, so the
    LLM has something concrete to check for instead of guessing.
    """
    llm = _CapturingLLM("NATURAL")
    _line_is_stiff("tranquila alta.", "es", llm)
    assert len(llm.prompts) == 1
    assert "disconnected" in llm.prompts[0]
    assert "tranquila alta." in llm.prompts[0]

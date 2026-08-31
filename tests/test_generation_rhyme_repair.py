"""Regression tests for gap #11: rhyme-key repair acceptance logic.

Both repair paths used to accept a repair attempt (or skip repairing
altogether) based on metre alone, never checking whether a rhyme-key defect
was actually resolved. See docs/GENERATION_QUALITY_PLAN.md, "Root cause:
rhyme-key repair (gap #11)".
"""

from __future__ import annotations

from poesia.evaluation.scorer import LineScorer, ScoredCandidate
from poesia.generation.constrained_loop import ConstrainedLoop


class _QueuedRepairLLM:
    """Returns each item of `responses` in order, one per repair() call."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.repair_calls = 0

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        return [self.responses[-1]]

    def repair(self, line: str, defect_description: str) -> str:
        response = self.responses[min(self.repair_calls, len(self.responses) - 1)]
        self.repair_calls += 1
        return response


def test_repair_draft_line_keeps_retrying_until_rhyme_is_actually_fixed() -> None:
    """Metre-only acceptance used to `break` on attempt 1 even with rhyme still wrong.

    "The cat sat on the mat" and "The cat sat on the map" both scan to 6
    syllables but rhyme on a different sound than the "IY1" target; "A bird
    flew to the sea" scans to 6 syllables *and* rhymes correctly.
    """
    loop = ConstrainedLoop(language="en", form="haiku")
    llm = _QueuedRepairLLM(["The cat sat on the map", "A bird flew to the sea"])
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_draft_line(  # noqa: SLF001 — test seam
        "The cat sat on the mat",
        target_syllables=6,
        target_rhyme_key="IY1",
        max_attempts=2,
        line_index=0,
    )

    assert result == "A bird flew to the sea"
    assert llm.repair_calls == 2, "must retry past the first attempt when rhyme is still wrong"
    assert not loop._warnings, "no warning once both metre and rhyme are satisfied"


def test_repair_draft_line_still_warns_when_rhyme_never_gets_fixed() -> None:
    """If the repair LLM never fixes the rhyme, max_attempts is exhausted and it's reported."""
    loop = ConstrainedLoop(language="en", form="haiku")
    llm = _QueuedRepairLLM(["The cat sat on the map"])  # never rhymes with "IY1"
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_draft_line(  # noqa: SLF001 — test seam
        "The cat sat on the mat",
        target_syllables=6,
        target_rhyme_key="IY1",
        max_attempts=2,
        line_index=0,
    )

    assert result == "The cat sat on the map"
    assert any("wrong rhyme key" in w for w in loop._warnings)


def test_repair_candidate_repairs_a_metrically_valid_but_wrong_rhyme_line() -> None:
    """`_needs_repair` used to ignore rhyme entirely, shipping a wrong-rhyme line silently."""
    loop = ConstrainedLoop(language="en", form="haiku")
    scan = loop._phonology.scan_line("The cat sat on the mat")
    bad = ScoredCandidate(line="The cat sat on the mat", scan=scan, score=1.0, breakdown={})
    loop._scorer = LineScorer(  # noqa: SLF001 — test seam
        phonology_backend=loop._phonology, target_syllable_count=6, target_rhyme_key="IY1"
    )
    llm = _QueuedRepairLLM(["A bird flew to the sea"])
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_candidate(  # noqa: SLF001 — test seam
        bad,
        [bad],
        target_syllables=6,
        target_rhyme_key="IY1",
        prior_lines=[],
        max_repair_attempts=2,
        line_index=0,
    )

    assert result is not None
    assert result.line == "A bird flew to the sea"
    assert llm.repair_calls == 1, "a wrong-rhyme candidate must trigger a repair attempt"
    assert not loop._warnings


def test_repair_draft_line_repairs_a_repeated_rhyme_word() -> None:
    """A line that repeats its rhyme partner's exact word passes `rhyme_key()`
    trivially (same word = same key) but isn't a resolved rhyme — it must
    still be treated as a defect and repaired.

    "The dog sat on the mat" repeats "mat", the word already committed for
    this rhyme group; "The dog sat with a hat" ends on a different word
    that genuinely rhymes with it.
    """
    loop = ConstrainedLoop(language="en", form="haiku")
    llm = _QueuedRepairLLM(["The dog sat with a hat"])
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_draft_line(  # noqa: SLF001 — test seam
        "The dog sat on the mat",
        target_syllables=6,
        target_rhyme_key="AE1 T",
        max_attempts=2,
        line_index=1,
        example_word="mat",
    )

    assert result == "The dog sat with a hat"
    assert llm.repair_calls == 1
    assert not loop._warnings, "no warning once the line rhymes with a genuinely new word"


def test_repair_draft_line_warns_with_repeat_message_when_repeat_never_gets_fixed() -> None:
    """If repair keeps handing back the same committed word, the warning must
    name the repeat, not the generic "wrong rhyme key" message — the rhyme
    *sound* is fine, the defect is that it's not a new word.
    """
    loop = ConstrainedLoop(language="en", form="haiku")
    llm = _QueuedRepairLLM(["The dog sat on the mat"])  # keeps repeating "mat"
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_draft_line(  # noqa: SLF001 — test seam
        "The dog sat on the mat",
        target_syllables=6,
        target_rhyme_key="AE1 T",
        max_attempts=2,
        line_index=1,
        example_word="mat",
    )

    assert result == "The dog sat on the mat"
    assert any('repeats the word "mat"' in w for w in loop._warnings)
    assert not any("wrong rhyme key" in w for w in loop._warnings)


def test_repair_candidate_repairs_a_repeated_rhyme_word() -> None:
    """Same repeated-word defect, but through the line-by-line repair path."""
    loop = ConstrainedLoop(language="en", form="haiku")
    scan = loop._phonology.scan_line("The dog sat on the mat")
    bad = ScoredCandidate(line="The dog sat on the mat", scan=scan, score=1.0, breakdown={})
    loop._scorer = LineScorer(  # noqa: SLF001 — test seam
        phonology_backend=loop._phonology, target_syllable_count=6, target_rhyme_key="AE1 T"
    )
    llm = _QueuedRepairLLM(["The dog sat with a hat"])
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_candidate(  # noqa: SLF001 — test seam
        bad,
        [bad],
        target_syllables=6,
        target_rhyme_key="AE1 T",
        prior_lines=[],
        max_repair_attempts=2,
        line_index=1,
        example_word="mat",
    )

    assert result is not None
    assert result.line == "The dog sat with a hat"
    assert llm.repair_calls == 1, "a repeated-word candidate must trigger a repair attempt"
    assert not loop._warnings


def test_repair_candidate_warns_with_repeat_message_when_repeat_never_gets_fixed() -> None:
    """Fallback acceptance must name the repeated word, not claim a wrong sound."""
    loop = ConstrainedLoop(language="en", form="haiku")
    scan = loop._phonology.scan_line("The dog sat on the mat")
    bad = ScoredCandidate(line="The dog sat on the mat", scan=scan, score=1.0, breakdown={})
    loop._scorer = LineScorer(  # noqa: SLF001 — test seam
        phonology_backend=loop._phonology, target_syllable_count=6, target_rhyme_key="AE1 T"
    )
    llm = _QueuedRepairLLM(["The dog sat on the mat"])  # keeps repeating "mat"
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_candidate(  # noqa: SLF001 — test seam
        bad,
        [bad],
        target_syllables=6,
        target_rhyme_key="AE1 T",
        prior_lines=[],
        max_repair_attempts=1,
        line_index=1,
        example_word="mat",
    )

    assert result is not None
    assert any('repeats the word "mat"' in w for w in loop._warnings)
    assert not any("wrong rhyme key" in w for w in loop._warnings)


def test_repair_candidate_warns_when_rhyme_cant_be_fixed() -> None:
    """Fallback acceptance used to warn about metre/guest-word only, never rhyme."""
    loop = ConstrainedLoop(language="en", form="haiku")
    scan = loop._phonology.scan_line("The cat sat on the mat")
    bad = ScoredCandidate(line="The cat sat on the mat", scan=scan, score=1.0, breakdown={})
    loop._scorer = LineScorer(  # noqa: SLF001 — test seam
        phonology_backend=loop._phonology, target_syllable_count=6, target_rhyme_key="IY1"
    )
    llm = _QueuedRepairLLM(["The cat sat on the map"])  # never rhymes with "IY1"
    loop._llm = llm  # noqa: SLF001 — test seam

    result = loop._repair_candidate(  # noqa: SLF001 — test seam
        bad,
        [bad],
        target_syllables=6,
        target_rhyme_key="IY1",
        prior_lines=[],
        max_repair_attempts=1,
        line_index=0,
    )

    assert result is not None
    assert any("wrong rhyme key" in w for w in loop._warnings)

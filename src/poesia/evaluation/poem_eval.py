"""Whole-poem scores for adapter evaluation (docs/RETRAINING_PLAN_2026-10.md §6 step 2).

Pure functions over a generated poem, its form and a phonology backend:

- ``line_count_ok``: the poem has the form's line count.
- ``syllable_abs_dev``: mean per-line |counted - target| syllables. The previous metric,
  |mean(counted) - target|, let long and short lines cancel (a poem alternating 9 and 13
  syllables scored a perfect 0).
- ``metre_pass_rate``: share of lines with exactly the target count.
- ``rhyme_accuracy``: share of rhyme-scheme pairings that hold. Each line in a rhyme group
  is compared with the group's first line by consonant rhyme key; letters that appear once
  and ``-`` positions (unrhymed) are not scored. ``None`` when the scheme has no pairs.

The syllable counter itself disagrees with expert scansion on part of the lines
(``scripts/check_scansion_vs_adso.py``); read deviations against that floor.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class _Form(Protocol):
    """What the scorer needs from a form (poesia.forms.FormSpec satisfies it; evaluation/
    may not import forms/, see tests/test_architecture_layers.py)."""

    rhyme_scheme: str

    @property
    def total_lines(self) -> int: ...

    def syllables_for_line(self, line_index: int) -> int: ...


class _Phonology(Protocol):
    def scan_line(self, line: str) -> Any: ...

    def rhyme_key(self, line: str) -> Any: ...


def rhyme_accuracy(lines: Sequence[str], scheme: str, phonology: _Phonology) -> float | None:
    """Share of rhyme-scheme pairings whose consonant rhyme keys match."""
    first_of_group: dict[str, str] = {}
    checked = matched = 0
    for line, letter in zip(lines, scheme.replace(" ", ""), strict=False):
        if not letter.isalpha():
            continue
        key = phonology.rhyme_key(line).consonant
        if letter not in first_of_group:
            first_of_group[letter] = key
            continue
        checked += 1
        matched += bool(key) and key == first_of_group[letter]
    return matched / checked if checked else None


def score_poem(lines: Sequence[str], form: _Form, phonology: _Phonology) -> dict[str, Any]:
    """Line count, syllable deviation, metre pass rate and rhyme accuracy for one poem."""
    lines = [line for line in lines if line.strip()]
    targets = [form.syllables_for_line(i) for i in range(len(lines))]
    counts = [phonology.scan_line(line).metrical_syllable_count for line in lines]
    devs = [abs(c - t) for c, t in zip(counts, targets, strict=True)]
    return {
        "line_count": len(lines),
        "line_count_ok": len(lines) == form.total_lines,
        "syllable_abs_dev": sum(devs) / len(devs) if devs else None,
        "metre_pass_rate": sum(d == 0 for d in devs) / len(devs) if devs else None,
        "rhyme_accuracy": rhyme_accuracy(lines, form.rhyme_scheme, phonology),
        "syllables": counts,
    }


def aggregate(scores: Sequence[dict[str, Any]]) -> dict[str, float | None]:
    """Means over poems; ``None`` values (no scorable lines or pairs) are left out."""

    def mean(key: str) -> float | None:
        vals = [float(s[key]) for s in scores if s.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "poems": float(len(scores)),
        "line_count_accuracy": mean("line_count_ok"),
        "syllable_abs_dev": mean("syllable_abs_dev"),
        "metre_pass_rate": mean("metre_pass_rate"),
        "rhyme_accuracy": mean("rhyme_accuracy"),
    }

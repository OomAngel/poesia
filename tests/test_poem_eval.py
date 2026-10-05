"""Whole-poem evaluation scores (src/poesia/evaluation/poem_eval.py)."""

from __future__ import annotations

from dataclasses import dataclass

from poesia.evaluation.poem_eval import aggregate, rhyme_accuracy, score_poem
from poesia.forms.definitions import get_form


@dataclass
class _Scan:
    metrical_syllable_count: int


@dataclass
class _Key:
    consonant: str
    assonant: str = ""


class FakePhonology:
    """Syllables = word count; rhyme key = last two letters of the last word."""

    def scan_line(self, line: str) -> _Scan:
        return _Scan(len(line.split()))

    def rhyme_key(self, line: str) -> _Key:
        return _Key(line.split()[-1][-2:] if line.split() else "")


def test_cancelling_errors_are_not_hidden() -> None:
    form = get_form("soneto", "es")  # 14 lines, 11 syllables
    lines = [" ".join(["w"] * (9 if i % 2 else 13)) for i in range(14)]
    s = score_poem(lines, form, FakePhonology())
    assert s["syllable_abs_dev"] == 2.0  # the old |mean - 11| metric reported 0.0
    assert s["metre_pass_rate"] == 0.0
    assert s["line_count_ok"] is True


def test_rhyme_accuracy_counts_pairings_in_each_group() -> None:
    lines = ["a al", "b bo", "c bo", "d al"]  # ABBA, both pairs rhyme
    assert rhyme_accuracy(lines, "ABBA", FakePhonology()) == 1.0
    lines = ["a al", "b bo", "c xx", "d al"]  # B pair broken
    assert rhyme_accuracy(lines, "ABBA", FakePhonology()) == 0.5


def test_unrhymed_positions_and_no_pairs_give_none() -> None:
    assert rhyme_accuracy(["a", "b", "c"], "-A-", FakePhonology()) is None
    assert rhyme_accuracy(["a", "b"], "", FakePhonology()) is None


def test_aggregate_skips_missing_values() -> None:
    agg = aggregate(
        [
            {
                "line_count_ok": True,
                "syllable_abs_dev": 1.0,
                "metre_pass_rate": 0.5,
                "rhyme_accuracy": None,
            },
            {
                "line_count_ok": False,
                "syllable_abs_dev": 3.0,
                "metre_pass_rate": 0.0,
                "rhyme_accuracy": 1.0,
            },
        ]
    )
    assert agg["line_count_accuracy"] == 0.5 and agg["syllable_abs_dev"] == 2.0
    assert agg["rhyme_accuracy"] == 1.0


class RaisingPhonology(FakePhonology):
    def scan_line(self, line: str) -> _Scan:
        if "BAD" in line:
            raise ValueError("cannot scan")
        return super().scan_line(line)

    def rhyme_key(self, line: str) -> _Key:
        if "BAD" in line:
            raise ValueError("no pronunciation")
        return super().rhyme_key(line)


def test_an_unscorable_line_fails_instead_of_crashing() -> None:
    form = get_form("soneto", "es")
    lines = [" ".join(["w"] * 11)] * 13 + ["BAD"]
    s = score_poem(lines, form, RaisingPhonology())
    assert s["unscorable_lines"] == 1
    assert s["metre_pass_rate"] == 13 / 14
    assert s["syllable_abs_dev"] == 11 / 14

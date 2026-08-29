"""Tests for mixed-language line scanning (poesia.phonology.macaronic).

Uses a minimal fake PhonologyBackend (syllable count = word count) instead of
real Spanish/English backends, so these tests stay fast and only exercise the
splitting/recombination logic in `scan_mixed_line` itself.
"""

from __future__ import annotations

from poesia.phonology.base import RhymeKey, ScanResult, Stress
from poesia.phonology.macaronic import scan_mixed_line


class _FakePhonology:
    """Deterministic stand-in backend: syllable count = word count."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def scan_line(self, line: str) -> ScanResult:
        self.calls.append(line)
        words = line.split()
        return ScanResult(
            line=line,
            metrical_syllable_count=len(words),
            stress_pattern=tuple(Stress.PRIMARY for _ in words),
            is_valid=True,
        )

    def rhyme_key(self, line: str) -> RhymeKey:  # pragma: no cover - untouched by this module
        raise NotImplementedError


def test_splits_and_recombines_around_guest_word() -> None:
    host, guest = _FakePhonology(), _FakePhonology()
    line = "la luna brilla hello en el cielo"

    result = scan_mixed_line(line, "hello", host, guest)

    # 6 host words + 1 guest word, scanned separately, summed back together.
    assert result.metrical_syllable_count == 7
    assert result.stress_pattern == tuple(Stress.PRIMARY for _ in range(7))
    assert result.is_valid is True
    assert result.line == line
    # Host backend scanned the two surrounding spans; guest scanned only "hello".
    assert host.calls == ["la luna brilla ", " en el cielo"]
    assert guest.calls == ["hello"]


def test_falls_back_to_host_only_when_guest_word_absent() -> None:
    host, guest = _FakePhonology(), _FakePhonology()
    line = "la luna brilla en el cielo"

    result = scan_mixed_line(line, "hello", host, guest)

    assert result.metrical_syllable_count == len(line.split())
    assert host.calls == [line]
    assert guest.calls == []


def test_word_boundary_does_not_match_inside_another_word() -> None:
    """ "el" must not match the "el" inside "aquel" -- word-boundary regex."""
    host, guest = _FakePhonology(), _FakePhonology()
    line = "aquel día es hermoso"

    result = scan_mixed_line(line, "el", host, guest)

    assert result.metrical_syllable_count == len(line.split())
    assert host.calls == [line]
    assert guest.calls == []


def test_match_is_case_insensitive() -> None:
    host, guest = _FakePhonology(), _FakePhonology()
    line = "la luna dice HELLO amigo mio"

    result = scan_mixed_line(line, "hello", host, guest)

    assert guest.calls == ["HELLO"]
    assert result.metrical_syllable_count == len(line.split())


def test_guest_word_at_line_start_skips_empty_before_span() -> None:
    host, guest = _FakePhonology(), _FakePhonology()
    line = "hello mundo cruel"

    result = scan_mixed_line(line, "hello", host, guest)

    # No text before the guest word -> host.scan_line called once, not twice.
    assert host.calls == [" mundo cruel"]
    assert guest.calls == ["hello"]
    assert result.metrical_syllable_count == 3


def test_guest_word_at_line_end_skips_empty_after_span() -> None:
    host, guest = _FakePhonology(), _FakePhonology()
    line = "buenas noches hello"

    result = scan_mixed_line(line, "hello", host, guest)

    assert host.calls == ["buenas noches "]
    assert guest.calls == ["hello"]
    assert result.metrical_syllable_count == 3

"""Unit tests for EuphonyAnalyzer."""

from __future__ import annotations

from poesia.eufonia.analyzer import EuphonyAnalyzer, EuphonyReport
from poesia.phonology.base import RhymeKey, ScanResult


def test_euphony_analyzer_empty() -> None:
    analyzer = EuphonyAnalyzer()
    report = analyzer.analyze([])
    assert report.rhyme_scheme == ""
    assert report.assonance_score == 0.0
    assert report.consonance_score == 0.0
    assert len(report.cacophony_flags) == 0


def test_detect_rhyme_scheme_abab() -> None:
    analyzer = EuphonyAnalyzer()
    scans = [
        ScanResult(line="The cat sat on the mat", rhyme_key=RhymeKey(consonant="at", assonant="a")),
        ScanResult(line="A dog jumped over the log", rhyme_key=RhymeKey(consonant="og", assonant="o")),
        ScanResult(line="He wore a funny hat", rhyme_key=RhymeKey(consonant="at", assonant="a")),
        ScanResult(line="And walked across the fog", rhyme_key=RhymeKey(consonant="og", assonant="o")),
    ]
    scheme = analyzer.detect_rhyme_scheme(scans)
    assert scheme == "ABAB"


def test_euphony_analysis_scores() -> None:
    analyzer = EuphonyAnalyzer()
    scans = [
        ScanResult(line="Solo la soledad de las olas", rhyme_key=RhymeKey(consonant="as", assonant="oa")),
        ScanResult(line="Silba la brisa sutil", rhyme_key=RhymeKey(consonant="il", assonant="i")),
    ]
    report = analyzer.analyze(scans)
    assert report.rhyme_scheme == "AB"
    assert report.assonance_score > 0.0
    assert report.consonance_score > 0.0


def test_cacophony_sibilance_flag() -> None:
    analyzer = EuphonyAnalyzer()
    scans = [
        ScanResult(line="SSSSSS sssss ssssss zzzzzz"),
    ]
    report = analyzer.analyze(scans)
    assert len(report.cacophony_flags) > 0
    assert "Excessive sibilance" in report.cacophony_flags[0]

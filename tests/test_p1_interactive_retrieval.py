"""P1 tests: interactive line selection, memoria list/search."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from poesia.cli import app
from poesia.evaluation.scorer import ScoredCandidate
from poesia.generation.constrained_loop import ConstrainedLoop
from poesia.phonology.base import RhymeKey, ScanResult

runner = CliRunner()


def _make_scan(syllables: int = 5) -> ScanResult:
    return ScanResult(
        metrical_syllable_count=syllables,
        stress_pattern=[],
        is_valid=True,
        violations=[],
        rhyme_key=RhymeKey(consonant="", assonant=""),
    )


# ── LineSelector ─────────────────────────────────────────────────────────────


class TestLineSelector:
    def test_selector_overrides_top_candidate(self) -> None:
        """Selector returning candidate[1] causes that line to be committed."""
        from poesia.generation.llm_client import StubLLMClient

        def selector(line_index: int, candidates: list[ScoredCandidate]) -> str:
            return candidates[1].line if len(candidates) > 1 else candidates[0].line

        loop = ConstrainedLoop(language="es", form="haiku", llm=StubLLMClient())
        result = loop.run(theme="luna", n_candidates=5, line_selector=selector)

        assert len(result.lines) == 3
        assert all(isinstance(l, str) and l for l in result.lines)

    def test_none_selector_keeps_auto_best(self) -> None:
        from poesia.generation.llm_client import StubLLMClient

        loop = ConstrainedLoop(language="en", form="haiku", llm=StubLLMClient())
        result = loop.run(theme="moon", n_candidates=3, line_selector=None)
        assert len(result.lines) == 3

    def test_selector_receives_all_scored_candidates(self) -> None:
        from poesia.generation.llm_client import StubLLMClient

        call_counts: list[int] = []

        def selector(line_index: int, candidates: list[ScoredCandidate]) -> str:
            call_counts.append(len(candidates))
            return candidates[0].line

        loop = ConstrainedLoop(language="es", form="haiku", llm=StubLLMClient())
        loop.run(theme="luna", n_candidates=4, line_selector=selector)

        assert len(call_counts) == 3  # haiku = 3 lines
        assert all(c > 0 for c in call_counts)

    def test_selector_can_return_own_typed_line(self) -> None:
        """Selector may return a line not in the candidate list (user typed)."""
        from poesia.generation.llm_client import StubLLMClient

        own_line = "mi propia línea escrita"

        def selector(line_index: int, candidates: list[ScoredCandidate]) -> str:
            return own_line if line_index == 1 else candidates[0].line

        loop = ConstrainedLoop(language="es", form="haiku", llm=StubLLMClient())
        result = loop.run(theme="luna", n_candidates=3, line_selector=selector)
        assert result.lines[1] == own_line


# ── memoria list ──────────────────────────────────────────────────────────────


class TestMemoriaList:
    def test_shows_saved_poems(self, tmp_path: Path) -> None:
        from poesia.memoria.library import Library, PoemRecord

        lib = Library(tmp_path)
        lib.add(PoemRecord(lines=["la luna brilla"], language="es", form="haiku", theme="luna"))
        lib.add(PoemRecord(lines=["the moon shines"], language="en", form="haiku", theme="moon"))

        with patch("poesia.memoria.library.Library", return_value=lib):
            result = runner.invoke(app, ["memoria", "list"])

        assert result.exit_code == 0
        assert "luna" in result.output
        assert "moon" in result.output

    def test_filters_by_form(self, tmp_path: Path) -> None:
        from poesia.memoria.library import Library, PoemRecord

        lib = Library(tmp_path)
        lib.add(PoemRecord(lines=["v"] * 14, language="es", form="soneto", theme="vida"))
        lib.add(PoemRecord(lines=["h"], language="es", form="haiku", theme="luna"))

        with patch("poesia.memoria.library.Library", return_value=lib):
            result = runner.invoke(app, ["memoria", "list", "--form", "soneto"])

        assert result.exit_code == 0
        assert "vida" in result.output
        assert "luna" not in result.output

    def test_empty_library_message(self, tmp_path: Path) -> None:
        from poesia.memoria.library import Library

        with patch("poesia.memoria.library.Library", return_value=Library(tmp_path)):
            result = runner.invoke(app, ["memoria", "list"])

        assert result.exit_code == 0
        assert "No poems" in result.output


# ── memoria search ────────────────────────────────────────────────────────────


class TestMemoriaSearch:
    def test_finds_matching_poem(self, tmp_path: Path) -> None:
        from poesia.memoria.library import Library, PoemRecord

        lib = Library(tmp_path)
        lib.add(
            PoemRecord(lines=["la luna brilla"], language="es", form="haiku", theme="luna nocturna")
        )
        lib.add(PoemRecord(lines=["el sol calienta"], language="es", form="haiku", theme="verano"))

        with patch("poesia.memoria.library.Library", return_value=lib):
            result = runner.invoke(app, ["memoria", "search", "luna"])

        assert result.exit_code == 0
        assert "luna nocturna" in result.output
        assert "verano" not in result.output

    def test_no_results_message(self, tmp_path: Path) -> None:
        from poesia.memoria.library import Library, PoemRecord

        lib = Library(tmp_path)
        lib.add(PoemRecord(lines=["verso"], language="es", form="haiku", theme="tema"))

        with patch("poesia.memoria.library.Library", return_value=lib):
            result = runner.invoke(app, ["memoria", "search", "xyz_inexistente"])

        assert result.exit_code == 0
        assert "No poems found" in result.output

"""Unit tests for macaronic (guest-word) helpers in the generation pipeline.

Covers the module-level helpers in constrained_loop.py, the prompt
instruction built by CandidateGenerator, the guest-word branch of
LineScorer, and end-to-end wiring through ConstrainedLoop.run().
"""

from __future__ import annotations

import pytest

from poesia.generation.candidate_generator import CandidateGenerator
from poesia.generation.constrained_loop import (
    ConstrainedLoop,
    _assign_guest_lines,
    _guest_word_ok,
    _prefer_guest_word,
    _repair_defect_description,
)
from poesia.generation.llm_client import StubLLMClient


class _GuestAwareLLM:
    """Fake LLM that actually reads the guest-word instruction out of the
    prompt and works it into every candidate it returns, mid-line -- unlike
    StubLLMClient, which ignores prompt content entirely. Lets tests verify
    the guest word really flows end-to-end through ConstrainedLoop.run().
    """

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        import re

        self.prompts.append(prompt)
        match = re.search(r'word or phrase "([^"]+)"', prompt)
        guest = match.group(1) if match else None
        if guest:
            return [f"una linea con {guest} en medio del verso" for _ in range(n)]
        return ["una linea cualquiera sin nada mas que decir" for _ in range(n)]

    def repair(self, line: str, defect_description: str) -> str:
        return line


class TestGuestWordOk:
    def test_true_when_no_guest_word_required(self) -> None:
        assert _guest_word_ok("cualquier linea", None) is True

    def test_true_when_guest_word_present_mid_line(self) -> None:
        assert _guest_word_ok("una linea con hello en medio", "hello") is True

    def test_false_when_guest_word_absent(self) -> None:
        assert _guest_word_ok("una linea sin nada", "hello") is False

    def test_false_when_guest_word_is_last_word(self) -> None:
        assert _guest_word_ok("una linea que termina en hello", "hello") is False

    def test_false_when_guest_word_is_last_word_with_punctuation(self) -> None:
        # Trailing punctuation shouldn't fool the "not line-final" check.
        assert _guest_word_ok("una linea que termina en hello,", "hello") is False

    def test_case_insensitive(self) -> None:
        assert _guest_word_ok("una linea con HELLO en medio", "hello") is True


class TestPreferGuestWord:
    def test_prefers_mid_line_candidates(self) -> None:
        candidates = [
            "sin la palabra",
            "con hello en medio del verso",
            "otra linea sin nada",
        ]
        assert _prefer_guest_word(candidates, "hello") == ["con hello en medio del verso"]

    def test_falls_back_to_line_final_mentions_if_no_mid_line_hit(self) -> None:
        candidates = ["una linea sin nada", "una linea que termina en hello"]
        result = _prefer_guest_word(candidates, "hello")
        assert result == ["una linea que termina en hello"]

    def test_falls_back_to_unfiltered_list_if_word_never_appears(self) -> None:
        candidates = ["una linea sin nada", "otra linea distinta"]
        assert _prefer_guest_word(candidates, "hello") == candidates


class TestAssignGuestLines:
    def test_no_guest_words_returns_empty(self) -> None:
        assert _assign_guest_lines(14, []) == {}

    def test_single_guest_word_spreads_to_middle(self) -> None:
        result = _assign_guest_lines(3, ["hello"])
        assert result == {1: "hello"}

    def test_multiple_guest_words_spread_evenly_without_collision(self) -> None:
        result = _assign_guest_lines(14, ["hello", "world"])
        assert len(result) == 2
        assert len(set(result.keys())) == 2  # no two words on the same line
        assert set(result.values()) == {"hello", "world"}
        for idx in result:
            assert 0 <= idx < 14

    def test_more_guest_words_than_lines_truncates(self) -> None:
        result = _assign_guest_lines(2, ["a", "b", "c"])
        assert len(result) == 2


class TestRepairDefectDescriptionGuestBranch:
    def test_includes_guest_word_instruction_when_present(self) -> None:
        desc = _repair_defect_description(
            actual_syllables=9, target_syllables=11, target_rhyme_key=None, guest_word="hello"
        )
        assert "hello" in desc
        assert "not as the last word" in desc

    def test_omits_guest_word_instruction_when_absent(self) -> None:
        desc = _repair_defect_description(
            actual_syllables=9, target_syllables=11, target_rhyme_key=None
        )
        assert "must naturally include" not in desc


class TestCandidateGeneratorGuestInstruction:
    def test_prompt_includes_guest_word_and_language_name(self) -> None:
        generator = CandidateGenerator(StubLLMClient())
        # StubLLMClient ignores the prompt, so we spy by wrapping generate().
        captured: list[str] = []
        original_llm = generator._llm

        class _Spy:
            def generate(self, prompt, n=1, temperature=0.9):
                captured.append(prompt)
                return original_llm.generate(prompt, n=n, temperature=temperature)

            def repair(self, line, defect_description):
                return original_llm.repair(line, defect_description)

        generator._llm = _Spy()
        generator.generate_lines(
            theme="luna",
            language="es",
            n_candidates=1,
            guest_word="hello",
            guest_lang="en",
        )
        assert len(captured) == 1
        assert 'English word or phrase "hello"' in captured[0]
        assert "NOT as the last word" in captured[0]

    def test_prompt_omits_guest_instruction_when_no_guest_word(self) -> None:
        generator = CandidateGenerator(StubLLMClient())
        captured: list[str] = []
        original_llm = generator._llm

        class _Spy:
            def generate(self, prompt, n=1, temperature=0.9):
                captured.append(prompt)
                return original_llm.generate(prompt, n=n, temperature=temperature)

            def repair(self, line, defect_description):
                return original_llm.repair(line, defect_description)

        generator._llm = _Spy()
        generator.generate_lines(theme="luna", language="es", n_candidates=1)
        assert "word or phrase" not in captured[0]


class TestLineScorerGuestBranch:
    def test_scores_with_scan_mixed_line_when_guest_word_present(self) -> None:
        from poesia.evaluation.scorer import LineScorer
        from poesia.phonology.english import EnglishPhonology
        from poesia.phonology.spanish import SpanishPhonology

        scorer = LineScorer(
            phonology_backend=SpanishPhonology(),
            target_syllable_count=7,
            language="es",
            guest_word="hello",
            guest_phonology=EnglishPhonology(),
        )
        scored = scorer.score_candidates(["la luna dice hello amigo"])
        assert len(scored) == 1
        # Just verifying this doesn't crash going through scan_mixed_line
        # and produces a real scan (not a zeroed-out default).
        assert scored[0].scan.metrical_syllable_count > 0

    def test_scores_normally_without_guest_word(self) -> None:
        from poesia.evaluation.scorer import LineScorer
        from poesia.phonology.spanish import SpanishPhonology

        scorer = LineScorer(
            phonology_backend=SpanishPhonology(),
            target_syllable_count=7,
            language="es",
        )
        scored = scorer.score_candidates(["la luna brilla en el cielo"])
        assert len(scored) == 1
        assert scored[0].scan.metrical_syllable_count > 0


class TestConstrainedLoopGuestWiring:
    def test_run_validates_guest_lang_and_guest_words_given_together(self) -> None:
        loop = ConstrainedLoop(language="es", form="haiku", llm=StubLLMClient())
        with pytest.raises(ValueError, match="together"):
            loop.run(theme="luna", guest_lang="en")
        with pytest.raises(ValueError, match="together"):
            loop.run(theme="luna", guest_words=["hello"])

    def test_run_rejects_unsupported_guest_lang(self) -> None:
        loop = ConstrainedLoop(language="es", form="haiku", llm=StubLLMClient())
        with pytest.raises(ValueError, match="No phonology backend registered"):
            loop.run(theme="luna", guest_lang="la", guest_words=["amor"])

    def test_run_places_guest_word_on_assigned_line_only(self) -> None:
        llm = _GuestAwareLLM()
        loop = ConstrainedLoop(language="es", form="haiku", llm=llm)

        result = loop.run(theme="luna", n_candidates=2, guest_lang="en", guest_words=["hello"])

        assert len(result.lines) == 3
        target_index = _assign_guest_lines(3, ["hello"])
        assert target_index == {1: "hello"}
        for i, line in enumerate(result.lines):
            if i == 1:
                assert "hello" in line.lower()
            else:
                assert "hello" not in line.lower()

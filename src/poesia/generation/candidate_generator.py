"""Candidate line generation: prompt construction + batch sampling.

Separated from the constrained loop (constrained_loop.py) so prompt
engineering can evolve independently of the accept/reject/repair control
flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from poesia.generation.llm_client import LLMClient

if TYPE_CHECKING:
    from poesia.generation.brief_builder import GenerationBrief


class CandidateGenerator:
    """Builds prompts and requests batches of candidate lines from an LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def generate_lines(
        self,
        theme: str,
        language: str,
        n_candidates: int = 16,
        prior_lines: list[str] | None = None,
        brief: GenerationBrief | None = None,
        target_syllables: int | None = None,
        target_rhyme_key: str | None = None,
        example_rhyme_word: str | None = None,
    ) -> list[str]:
        """Generate a batch of candidate next-lines for a poem in progress.

        Args:
            theme: Thematic anchor for the poem (used if no brief provided).
            language: Language code ('es', 'en').
            n_candidates: Number of candidate lines to generate.
            prior_lines: Lines already written in the poem (for continuity).
            brief: Optional GenerationBrief with rich context from BriefBuilder.
            target_syllables: Expected syllable count for this line position.
            target_rhyme_key: Phonetic rhyme key the line end must match.
            example_rhyme_word: A word already committed to this rhyme group
                (e.g. "claras") shown in the prompt so the model can hear the sound.

        Returns:
            List of candidate lines from the LLM.
        """
        prior_lines = prior_lines or []

        # --- constraint instructions ------------------------------------
        syllable_instruction = (
            f"Exactly {target_syllables} syllables." if target_syllables else ""
        )
        if target_rhyme_key and example_rhyme_word:
            rhyme_instruction = (
                f'End the line with a word that rhymes with "{example_rhyme_word}" '
                f"(same ending sound)."
            )
        elif target_rhyme_key:
            rhyme_instruction = (
                f"End the line with a word whose rhyme key is '{target_rhyme_key}'."
            )
        else:
            rhyme_instruction = ""  # first of its rhyme group — model is free

        anti_repeat = (
            "Do NOT begin the line with the same word as any prior line."
            if prior_lines else ""
        )

        constraints = " ".join(filter(None, [syllable_instruction, rhyme_instruction, anti_repeat]))
        output_rule = (
            "Output ONLY the single bare poetry line — no explanation, "
            "no preamble, no numbering, no quotes."
        )

        # --- numbered prior-lines block ---------------------------------
        if prior_lines:
            numbered = "\n".join(f"{i+1}. {ln}" for i, ln in enumerate(prior_lines))
            prior_block = f"Poem so far:\n{numbered}\n\n"
        else:
            prior_block = ""

        # --- assemble prompt --------------------------------------------
        if brief is not None:
            base_prompt = brief.to_prompt()
            prompt = (
                f"{base_prompt}\n"
                f"## POEM IN PROGRESS\n{prior_block}"
                f"## TASK\n"
                f"Write line {len(prior_lines)+1}. {constraints}\n"
                f"{output_rule}"
            )
        else:
            lang_name = {"es": "Spanish", "en": "English", "nl": "Dutch"}.get(language, language)
            prompt = (
                f"You are writing a {lang_name} poem on the theme: {theme}.\n"
                f"{prior_block}"
                f"Write line {len(prior_lines)+1}. {constraints}\n"
                f"{output_rule}"
            )

        return self._llm.generate(prompt, n=n_candidates)

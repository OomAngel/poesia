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
    ) -> list[str]:
        """Generate a batch of candidate next-lines for a poem in progress.

        Args:
            theme: Thematic anchor for the poem (used if no brief provided).
            language: Language code ('es', 'en').
            n_candidates: Number of candidate lines to generate.
            prior_lines: Lines already written in the poem (for continuity).
            brief: Optional GenerationBrief with rich context from BriefBuilder.
                   If provided, uses brief.to_prompt() for a much richer prompt.
            target_syllables: Expected syllable count for this line position.
                   Included in the prompt so the model knows the metrical target.

        Returns:
            List of candidate lines from the LLM.
        """
        prior = "\n".join(prior_lines or [])
        syllable_instruction = (
            f" The line must have exactly {target_syllables} syllables."
            if target_syllables
            else ""
        )
        output_rule = (
            "Output ONLY the single bare line of poetry — no explanation, "
            "no preamble, no questions, no punctuation outside the line itself."
        )

        if brief is not None:
            base_prompt = brief.to_prompt()
            prompt = (
                f"{base_prompt}\n"
                f"## POEM IN PROGRESS\n{prior}\n\n"
                f"## TASK\n"
                f"Write the next line of the poem above.{syllable_instruction} "
                f"Stay faithful to the form, personal context, and tone.\n"
                f"{output_rule}"
            )
        else:
            lang_name = {"es": "Spanish", "en": "English", "nl": "Dutch"}.get(language, language)
            prior_block = f"Poem so far:\n{prior}\n\n" if prior else ""
            prompt = (
                f"You are writing a {lang_name} poem on the theme: {theme}.\n"
                f"{prior_block}"
                f"Write the next line.{syllable_instruction}\n"
                f"{output_rule}"
            )

        return self._llm.generate(prompt, n=n_candidates)

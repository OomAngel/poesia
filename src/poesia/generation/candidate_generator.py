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
    ) -> list[str]:
        """Generate a batch of candidate next-lines for a poem in progress.

        Args:
            theme: Thematic anchor for the poem (used if no brief provided).
            language: Language code ('es', 'en').
            n_candidates: Number of candidate lines to generate.
            prior_lines: Lines already written in the poem (for continuity).
            brief: Optional GenerationBrief with rich context from BriefBuilder.
                   If provided, uses brief.to_prompt() for a much richer prompt.

        Returns:
            List of candidate lines from the LLM.
        """
        prior = "\n".join(prior_lines or [])

        if brief is not None:
            # Use the rich brief prompt with full context
            base_prompt = brief.to_prompt()
            prompt = (
                f"{base_prompt}\n"
                f"## POEM IN PROGRESS\n{prior}\n\n"
                "Write the next line, staying faithful to the form constraints, "
                "personal context, and tone guidance above."
            )
        else:
            # Fall back to simple prompt (legacy behavior)
            prompt = (
                f"Language: {language}\n"
                f"Theme: {theme}\n"
                f"Poem so far:\n{prior}\n"
                "Write the next line, staying faithful to imagery and tone."
            )

        return self._llm.generate(prompt, n=n_candidates)

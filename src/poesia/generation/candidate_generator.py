"""Candidate line generation: prompt construction + batch sampling.

Separated from the constrained loop (constrained_loop.py) so prompt
engineering can evolve independently of the accept/reject/repair control
flow.
"""

from __future__ import annotations

from poesia.generation.llm_client import LLMClient


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
    ) -> list[str]:
        """Generate a batch of candidate next-lines for a poem in progress."""
        prior = "\n".join(prior_lines or [])
        prompt = (
            f"Language: {language}\n"
            f"Theme: {theme}\n"
            f"Poem so far:\n{prior}\n"
            "Write the next line, staying faithful to imagery and tone."
        )
        return self._llm.generate(prompt, n=n_candidates)

"""The core generate → validate → rank → repair loop.

    1. Generate 16-64 candidate lines.
    2. Scan syllables, stress, rhyme and sound pattern.
    3. Reject formally impossible candidates.
    4. Score semantic continuity and novelty.
    5. Detect clichés and repeated syntactic templates.
    6. Keep the best few candidates.
    7. Ask the LLM to repair one explicit defect at a time.
    8. Rescan after every revision.
    9. Let the human choose among surviving lines.

Phase 0 status: structural skeleton wired to StubLLMClient and the Spanish/
English phonology backends. Not yet a working poem generator — this is the
control-flow scaffold that Phase 1 will fill in with real scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from poesia.evaluation.scorer import LineScorer, ScoredCandidate
from poesia.forms.definitions import FormSpec, get_form
from poesia.generation.candidate_generator import CandidateGenerator
from poesia.generation.llm_client import LLMClient, StubLLMClient
from poesia.phonology.english import EnglishPhonology
from poesia.phonology.spanish import SpanishPhonology


def _phonology_for(language: str):
    if language == "es":
        return SpanishPhonology()
    if language == "en":
        return EnglishPhonology()
    raise ValueError(f"No phonology backend registered for language '{language}'.")


@dataclass
class LoopResult:
    """Final output of a constrained generation run."""

    lines: list[str] = field(default_factory=list)
    scored_history: list[list[ScoredCandidate]] = field(default_factory=list)


class ConstrainedLoop:
    """Drives the generate/validate/rank/repair cycle for one poem.

    Args:
        language: ISO-ish language code, currently 'es' or 'en'.
        form: name of a registered FormSpec (see poesia.forms.definitions).
        llm: optional LLMClient; defaults to StubLLMClient for offline dev.
    """

    def __init__(
        self,
        language: str,
        form: str,
        llm: LLMClient | None = None,
    ) -> None:
        self.language = language
        self.form_spec: FormSpec = get_form(form)
        self._llm = llm or StubLLMClient()
        self._phonology = _phonology_for(language)
        self._generator = CandidateGenerator(self._llm)
        self._scorer = LineScorer(
            phonology_backend=self._phonology,
            target_syllable_count=self.form_spec.syllables_per_line,
        )

    def run(self, theme: str, n_candidates: int = 16, max_repair_attempts: int = 2) -> LoopResult:
        """Generate a full poem, one line at a time, for `total_lines` lines."""
        result = LoopResult()
        for _ in range(self.form_spec.total_lines):
            candidates = self._generator.generate_lines(
                theme=theme,
                language=self.language,
                n_candidates=n_candidates,
                prior_lines=result.lines,
            )
            scored = self._scorer.score_candidates(candidates)
            result.scored_history.append(scored)

            best = scored[0] if scored else None
            attempts = 0
            while best is not None and not best.scan.is_valid and attempts < max_repair_attempts:
                repaired_text = self._llm.repair(
                    best.line, defect_description="metrical syllable count mismatch"
                )
                rescored = self._scorer.score_candidates([repaired_text])
                best = rescored[0]
                attempts += 1

            if best is not None:
                result.lines.append(best.line)
        return result

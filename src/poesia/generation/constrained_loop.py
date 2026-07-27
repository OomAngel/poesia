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

Phase 3E: now supports BriefBuilder integration for rich pre-generation context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from poesia.evaluation.scorer import LineScorer, ScoredCandidate
from poesia.forms.definitions import FormSpec, get_form
from poesia.generation.candidate_generator import CandidateGenerator
from poesia.generation.llm_client import LLMClient, StubLLMClient
from poesia.phonology.english import EnglishPhonology
from poesia.phonology.spanish import SpanishPhonology

if TYPE_CHECKING:
    from poesia.generation.brief_builder import BriefBuilder, GenerationBrief
    from poesia.memoria.embeddings import EmbeddingClient
    from poesia.memoria.records import FragmentRecord, InfluenceRecord


def _phonology_for(language: str):
    if language == "es":
        return SpanishPhonology()
    if language == "en":
        return EnglishPhonology()
    if language == "nl":
        from poesia.phonology.dutch import DutchPhonology
        return DutchPhonology()
    raise ValueError(f"No phonology backend registered for language '{language}'.")


@dataclass
class LoopResult:
    """Final output of a constrained generation run."""

    lines: list[str] = field(default_factory=list)
    scored_history: list[list[ScoredCandidate]] = field(default_factory=list)
    brief: GenerationBrief | None = None  # The brief used (if any)


class ConstrainedLoop:
    """Drives the generate/validate/rank/repair cycle for one poem.

    Args:
        language: ISO-ish language code, currently 'es' or 'en'.
        form: name of a registered FormSpec (see poesia.forms.definitions).
        llm: optional LLMClient; defaults to StubLLMClient for offline dev.
        brief_builder: optional BriefBuilder for rich pre-generation context.
        embedding_client: optional EmbeddingClient for semantic retrieval.
        fragments: optional list of FragmentRecords for personal context.
        influences: optional list of InfluenceRecords for style anchoring.
    """

    def __init__(
        self,
        language: str,
        form: str,
        llm: LLMClient | None = None,
        brief_builder: BriefBuilder | None = None,
        embedding_client: EmbeddingClient | None = None,
        fragments: list[FragmentRecord] | None = None,
        influences: list[InfluenceRecord] | None = None,
    ) -> None:
        self.language = language
        self.form_spec: FormSpec = get_form(form)
        self._llm = llm or StubLLMClient()
        self._phonology = _phonology_for(language)
        self._generator = CandidateGenerator(self._llm)
        # Phase 3E: brief building support
        self._brief_builder = brief_builder
        self._embedding_client = embedding_client
        self._fragments = fragments or []
        self._influences = influences or []
        # Scorer is created per-run with theme, so store config here
        self._scorer: LineScorer | None = None

    def run(
        self,
        theme: str,
        n_candidates: int = 16,
        max_repair_attempts: int = 2,
        tone: list[str] | None = None,
        seeds: list[str] | None = None,
        brief_level: str = "standard",
    ) -> LoopResult:
        """Generate a full poem, one line at a time, for `total_lines` lines.

        Args:
            theme: Thematic anchor for the poem.
            n_candidates: Number of candidate lines to generate per position.
            max_repair_attempts: Maximum repair attempts per line.
            tone: Optional tone descriptors (e.g. ['melancholic', 'intimate']).
            seeds: Optional seed words to expand for rhymes/synonyms.
            brief_level: Brief verbosity: 'minimal', 'standard', or 'maximal'.

        Returns:
            LoopResult with generated lines, scoring history, and brief used.
        """
        result = LoopResult()

        # Build brief if we have a builder (Phase 3E integration)
        brief: GenerationBrief | None = None
        if self._brief_builder is not None:
            brief = self._brief_builder.build(
                form=self.form_spec,
                theme=theme,
                tone=tone,
                seeds=seeds,
                level=brief_level,
                language=self.language,
            )
            result.brief = brief

        # Generate lines one by one, updating scorer target for variable patterns (e.g., haiku)
        for line_index in range(self.form_spec.total_lines):
            # Create/update scorer with correct target for this line position
            target_syllables = self.form_spec.syllables_for_line(line_index)
            self._scorer = LineScorer(
                phonology_backend=self._phonology,
                target_syllable_count=target_syllables,
                embedding_client=self._embedding_client,
                theme_text=theme,
                language=self.language,
            )
            candidates = self._generator.generate_lines(
                theme=theme,
                language=self.language,
                n_candidates=n_candidates,
                prior_lines=result.lines,
                brief=brief,
            )
            # Pass prior lines for novelty scoring (Phase 1 fix)
            scored = self._scorer.score_candidates(candidates, prior_lines=result.lines)
            result.scored_history.append(scored)

            best = scored[0] if scored else None
            attempts = 0
            while best is not None and not best.scan.is_valid and attempts < max_repair_attempts:
                repaired_text = self._llm.repair(
                    best.line, defect_description="metrical syllable count mismatch"
                )
                rescored = self._scorer.score_candidates([repaired_text], prior_lines=result.lines)
                best = rescored[0]
                attempts += 1

            if best is not None:
                result.lines.append(best.line)
        return result

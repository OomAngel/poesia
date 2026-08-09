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

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, cast

from poesia.evaluation.scorer import LineScorer, ScoredCandidate
from poesia.forms.definitions import FormSpec, get_form
from poesia.generation.candidate_generator import CandidateGenerator
from poesia.generation.hooks import HookEvent
from poesia.generation.llm_client import LLMClient, StubLLMClient
from poesia.generation.rhyme_tracker import RhymeTracker
from poesia.phonology.english import EnglishPhonology
from poesia.phonology.spanish import SpanishPhonology

if TYPE_CHECKING:
    from poesia.generation.brief_builder import BriefBuilder, GenerationBrief
    from poesia.generation.hooks import GenerationHook
    from poesia.memoria.embeddings import EmbeddingClient
    from poesia.memoria.records import FragmentRecord, InfluenceRecord


# ── Language detection filter ────────────────────────────────────────────


def _filter_by_language(candidates: list[str], target_lang: str) -> list[str]:
    """Filter candidate lines by target language using lightweight heuristics.

    Keeps only lines that appear to be in the target language.
    This prevents the LLM from ignoring the language instruction
    and producing e.g. English lines for a Spanish poem.

    Args:
        candidates: Generated candidate lines.
        target_lang: ``"es"``, ``"en"``, or ``"nl"``.

    Returns:
        Candidates that pass the language check, preserving order.
        If all candidates are rejected, returns the originals (fail open).
    """
    if target_lang == "es":
        _es_words = frozenset(
            {
                "el",
                "la",
                "los",
                "las",
                "que",
                "con",
                "por",
                "para",
                "del",
                "una",
                "como",
                "más",
                "pero",
                "sus",
                "era",
                "son",
                "entre",
                "todo",
                "sin",
                "cada",
                "este",
                "esta",
                "ese",
                "esa",
                "tiene",
                "donde",
                "siempre",
                "nunca",
                "tiempo",
                "mundo",
            }
        )

        def _is_es(line: str) -> bool:
            low = line.lower()
            if "ñ" in low or "¿" in low or "¡" in low:
                return True
            words = set(low.split())
            return len(words & _es_words) >= 1

        filtered = [c for c in candidates if _is_es(c)]
        return filtered if filtered else candidates  # Fail open

    elif target_lang == "en":
        _es_signals = frozenset(
            {
                "el",
                "la",
                "los",
                "las",
                "que",
                "del",
                "por",
                "para",
                "como",
                "más",
                "pero",
                "sus",
                "entre",
                "todo",
                "sin",
            }
        )

        def _is_en(line: str) -> bool:
            low = line.lower()
            if "ñ" in low or "¿" in low or "¡" in low:
                return False
            words = set(low.split())
            return len(words & _es_signals) < 1

        filtered = [c for c in candidates if _is_en(c)]
        return filtered if filtered else candidates  # Fail open

    return candidates


def _phonology_for(language: str):
    if language == "es":
        return SpanishPhonology()
    if language == "en":
        return EnglishPhonology()
    if language == "nl":
        from poesia.phonology.dutch import DutchPhonology

        return DutchPhonology()
    raise ValueError(f"No phonology backend registered for language '{language}'.")


# ── Candidate cleaning ────────────────────────────────────────────────────
# Local/fine-tuned models frequently echo prompt fragments back as line
# prefixes: numbering ("3. "), rhyme-scheme letters ("AE ", "FLO ", "FI "),
# or prompt boilerplate ("Line content: "). Cleaning BEFORE scoring both
# rescues genuinely usable lines and stops the echo from inflating the
# metre/rhyme scores of junk. Exact repeats of already-committed lines (and
# of other candidates in the same batch) are rejected too, so a model's
# degenerate loops cannot dominate a poem.

_ECHO_PREFIXES = ("AE ", "FLO ", "FI ", "Line content: ", "Line ")


def _clean_candidate(line: str) -> str:
    """Strip prompt-echo artifacts from a single candidate line."""
    text = line.strip()
    while True:
        stripped = re.sub(r"^\d+[.:]\s*", "", text)  # leading numbering "3. "/"5:"
        for prefix in _ECHO_PREFIXES:
            if stripped.lower().startswith(prefix.lower()):
                stripped = stripped[len(prefix) :].lstrip()
                break
        if stripped == text:
            break
        text = stripped
    # Rhyme-key echoes are often uppercased by the model ("MUEVE", "MOMENTO").
    match = re.match(r"^([A-ZÁÉÍÓÚÑ]{2,})\s", text)
    if match:
        text = match.group(1).lower() + text[match.end(1) :]
    return text.strip()


def _clean_candidates(candidates: list[str], prior_lines: list[str]) -> list[str]:
    """Clean artifacts and reject repeats, preserving order; fail-open.

    If cleaning would empty the list, the original candidates are returned so
    the loop never stalls on a pathological batch.
    """
    if not candidates:
        return candidates
    cleaned: list[str] = []
    seen: set[str] = {p.strip().lower() for p in prior_lines}
    for cand in candidates:
        cc = _clean_candidate(cand)
        key = cc.lower()
        if not cc or key in seen:
            continue
        seen.add(key)
        cleaned.append(cc)
    return cleaned or candidates


def _repair_defect_description(
    actual_syllables: int | None,
    target_syllables: int,
    target_rhyme_key: str | None,
) -> str:
    """Build a precise repair request so the LLM knows the exact defect.

    The old generic message (\"metrical syllable count mismatch\") forced the
    model to guess the target; giving it the actual vs target count and the
    rhyme key it must hit makes repairs effective instead of destructive.
    """
    parts = [f"the line has {actual_syllables} syllables but must be exactly {target_syllables}"]
    if target_rhyme_key:
        parts.append(f"the line must end with rhyme key '{target_rhyme_key}'")
    return "; ".join(parts)


# Callable type: receives (line_index, scored_candidates) → returns chosen line text
LineSelector = Callable[[int, "list[ScoredCandidate]"], str]


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
        # Observer hooks
        from poesia.generation.hooks import CompositeHook

        self._hooks = CompositeHook()

    def add_hook(self, hook: GenerationHook) -> None:
        """Attach a hook to observe generation events."""
        self._hooks.add(hook)

    def _build_brief(
        self,
        theme: str,
        tone: list[str] | None,
        seeds: list[str] | None,
        brief_level: str,
        movement: str | None,
    ) -> GenerationBrief | None:
        """Build the generation brief when a builder is configured."""
        if self._brief_builder is None:
            return None
        brief = self._brief_builder.build(
            form=self.form_spec,
            theme=theme,
            tone=tone,
            seeds=seeds,
            level=cast(Literal["minimal", "standard", "maximal"], brief_level),
            language=self.language,
            movement=movement,
        )
        return brief

    def _repair_candidate(
        self,
        best: ScoredCandidate | None,
        scored: list[ScoredCandidate],
        target_syllables: int,
        target_rhyme_key: str | None,
        prior_lines: list[str],
        max_repair_attempts: int,
        line_index: int,
    ) -> ScoredCandidate | None:
        """Repair an invalid best candidate up to max_repair_attempts."""
        attempts = 0
        while best is not None and not best.scan.is_valid and attempts < max_repair_attempts:
            repaired_text = self._llm.repair(
                best.line,
                defect_description=_repair_defect_description(
                    actual_syllables=best.scan.metrical_syllable_count,
                    target_syllables=target_syllables,
                    target_rhyme_key=target_rhyme_key,
                ),
            )
            rescored = self._scorer.score_candidates([repaired_text], prior_lines=prior_lines)
            best = rescored[0]
            attempts += 1
            # Safety: if repair produced same text, it will never improve — move on
            if attempts > 0 and best.line == scored[0].line:
                break
        if best is not None and not best.scan.is_valid and attempts >= max_repair_attempts:
            # Fallback: accept best scored candidate even if invalid,
            # otherwise the loop hangs forever with a bad LLM.
            best = scored[0]
            print(
                f"  [WARN] Line {line_index + 1}: accepted best candidate despite invalid metre "
                f"(syllables={scored[0].scan.metrical_syllable_count}, "
                f"target={target_syllables})"
            )
        return best

    def _select_best(
        self,
        line_index: int,
        scored: list[ScoredCandidate],
        line_selector: LineSelector,
    ) -> ScoredCandidate | None:
        """Apply the human line-selection callback, if provided."""
        if line_selector is None or not scored:
            return None
        chosen_text = line_selector(line_index, scored)
        # Find the ScoredCandidate for the chosen line.
        # If the human typed their own line, wrap it in a ScoredCandidate.
        match = next((c for c in scored if c.line == chosen_text), None)
        if match is not None:
            return match
        custom_scan = self._phonology.scan_line(chosen_text)
        return ScoredCandidate(
            line=chosen_text,
            scan=custom_scan,
            score=1.0,
            breakdown={
                "metre": 1.0,
                "rhyme": 0.0,
                "theme": 0.0,
                "novelty": 1.0,
                "cliche": 0.0,
            },
        )

    def _generate_line(
        self,
        line_index: int,
        theme: str,
        n_candidates: int,
        brief: GenerationBrief | None,
        target_syllables: int,
        target_rhyme_key: str | None,
        example_rhyme_word: str | None,
        rhyme_candidates: list[str],
        prior_lines: list[str],
    ) -> list[ScoredCandidate]:
        """Generate + score the candidates for one line position."""
        # P4: extract fragment fidelity text from the brief (best fragment)
        fidelity_text: str | None = None
        if brief and brief.fragments:
            fidelity_text = brief.fragments[0][0].content

        # Observer: before generation
        self._hooks.on_event(
            HookEvent(
                line_index=line_index,
                phase="before_generate",
                data={"target_syllables": target_syllables, "theme": theme},
            )
        )

        self._scorer = LineScorer(
            phonology_backend=self._phonology,
            target_syllable_count=target_syllables,
            embedding_client=self._embedding_client,
            theme_text=theme,
            target_rhyme_key=target_rhyme_key,
            language=self.language,
            fragment_fidelity_text=fidelity_text,
        )
        candidates = self._generator.generate_lines(
            theme=theme,
            language=self.language,
            n_candidates=n_candidates,
            prior_lines=prior_lines,
            brief=brief,
            target_syllables=target_syllables,
            target_rhyme_key=target_rhyme_key,
            example_rhyme_word=example_rhyme_word,
            rhyme_candidates=rhyme_candidates,
        )
        # Clean prompt-echo artifacts and reject exact repeats (accuracy)
        candidates = _clean_candidates(candidates, prior_lines)
        # Filter out candidates not in the target language
        candidates = _filter_by_language(candidates, self.language)
        if not candidates:
            # Should not happen (fail-open in _filter_by_language),
            # but guard against empty list
            return []
        scored = self._scorer.score_candidates(candidates, prior_lines=prior_lines)

        # Observer: after scoring
        self._hooks.on_event(
            HookEvent(
                line_index=line_index,
                phase="after_score",
                data={
                    "n_candidates": len(scored),
                    "best_score": scored[0].score if scored else 0,
                    "best_line": scored[0].line if scored else "",
                },
            )
        )
        return scored

    def run(
        self,
        theme: str,
        n_candidates: int = 16,
        max_repair_attempts: int = 2,
        tone: list[str] | None = None,
        seeds: list[str] | None = None,
        brief_level: str = "standard",
        line_selector: LineSelector | None = None,
        total_lines_override: int | None = None,
        movement: str | None = None,
    ) -> LoopResult:
        """Generate a full poem, one line at a time, for `total_lines` lines.

        Args:
            theme: Thematic anchor for the poem.
            n_candidates: Number of candidate lines to generate per position.
            max_repair_attempts: Maximum repair attempts per line.
            tone: Optional tone descriptors (e.g. ['melancholic', 'intimate']).
            seeds: Optional seed words to expand for rhymes/synonyms.
            brief_level: Brief verbosity: 'minimal', 'standard', or 'maximal'.
            line_selector: Optional callable ``(line_index, candidates) -> str``.
                If provided, called after scoring each line position so the human
                can choose among candidates. If None (default) the top-scored
                candidate is selected automatically.
            total_lines_override: Override the form's total_lines. Used for
                variable-length forms like romance (which has lines_per_stanza=[])
                where the user specifies the desired line count via --lines.

        Returns:
            LoopResult with generated lines, scoring history, and brief used.
        """
        result = LoopResult()

        # Build brief if we have a builder (Phase 3E integration)
        brief = self._build_brief(theme, tone, seeds, brief_level, movement)
        if brief is not None:
            result.brief = brief

        # Rhyme tracker: maps rhyme-scheme letters to committed rhyme keys
        rhyme_tracker = RhymeTracker(
            self.form_spec.rhyme_scheme,
            self._phonology,
            language=self.language,
        )

        # Determine total lines: use override for variable-length forms (e.g., romance),
        # otherwise use the form's defined total_lines.
        total_lines = (
            total_lines_override if total_lines_override is not None else self.form_spec.total_lines
        )

        # Generate lines one by one, updating scorer target for variable patterns (e.g., haiku)
        for line_index in range(total_lines):
            target_syllables = self.form_spec.syllables_for_line(line_index)
            target_rhyme_key = rhyme_tracker.target_key_for_line(line_index)
            example_rhyme_word = rhyme_tracker.example_word_for_line(line_index)
            rhyme_candidates = rhyme_tracker.candidates_for_line(line_index)

            scored = self._generate_line(
                line_index,
                theme,
                n_candidates,
                brief,
                target_syllables,
                target_rhyme_key,
                example_rhyme_word,
                rhyme_candidates,
                result.lines,
            )
            if not scored:
                continue
            result.scored_history.append(scored)

            best = self._repair_candidate(
                scored[0] if scored else None,
                scored,
                target_syllables,
                target_rhyme_key,
                result.lines,
                max_repair_attempts,
                line_index,
            )
            if best is not None:
                chosen = self._select_best(line_index, scored, line_selector)
                if chosen is not None:
                    best = chosen
                result.lines.append(best.line)
                rhyme_tracker.commit(line_index, best.line)

        return result

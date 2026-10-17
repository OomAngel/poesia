"""Optional ranking penalties against repetition across a poem and its openings across poems.

The plain 8B repeats 3x more content words per poem than the poets, and its poems open with the
same few words (b17 scorecard 2026-10-14, TUNING_ROUNDS §1a). The page already ranks a proposal
down for both (``webapp._proposal_rank``); the generation loop did not. These penalties act on the
loop's composite score, so they only reorder candidates of nearly equal metre and rhyme.

Both weights default to 0, which leaves the ranking unchanged. The values used in a measurement are
set by the caller and reported with it: they are movable defaults, not findings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PUNCT_OPEN = ".,;:!?¡¿«»\"'()—–-…“”‘’„"
_MAX_REUSED = 4  # beyond this many reused words a line is as bad as it gets


def content_words(text: str, language: str) -> set[str]:
    """Words outside the language's ~150 most frequent (mostly function words), 3+ letters."""
    from poesia.phonology.rhyme_index import rank

    small = rank(language)
    return {
        w
        for w in re.findall(r"[^\W\d_]+", text.lower())
        if len(w) > 2 and small.get(w, 10**6) >= 150
    }


def opening_word(text: str) -> str | None:
    """The line's first word, lower-cased and stripped of punctuation (None for an empty line)."""
    words = text.split()
    return words[0].lower().strip(_PUNCT_OPEN) if words else None


@dataclass
class RankPenalties:
    """Penalties subtracted from a candidate's composite score.

    repeat_weight: per content word the poem has already used (at most ``_MAX_REUSED`` count).
    opening_weight: once, when the line opens with a word an earlier line of this poem opened with,
        or one in ``recent_openings`` (the caller keeps that set across the last few poems).
    """

    repeat_weight: float = 0.0
    opening_weight: float = 0.0
    recent_openings: set[str] = field(default_factory=set)
    # True: order candidates by metre, then rhyme, then reused words, then reused opening, then the
    # composite score, as the page does (``webapp._proposal_rank``). The penalties then only break
    # ties between equally well-formed lines and can never trade form for variety; the weights
    # only switch each term on. False: subtract the weighted penalty from the composite score.
    lexicographic: bool = False

    def counts(self, text: str, prior_lines: list[str] | None, language: str) -> tuple[int, int]:
        """(reused content words, 1 if the opening was used) -- each 0 when its term is off."""
        prior = [ln for ln in (prior_lines or []) if ln.strip()]
        reused = 0
        if self.repeat_weight and prior:
            used = set().union(*(content_words(ln, language) for ln in prior))
            reused = min(len(content_words(text, language) & used), _MAX_REUSED)
        opening = 0
        if self.opening_weight:
            first = opening_word(text)
            seen = {opening_word(ln) for ln in prior} | self.recent_openings
            opening = int(first is not None and first in seen)
        return reused, opening

    def penalty(self, text: str, prior_lines: list[str] | None, language: str) -> float:
        reused, opening = self.counts(text, prior_lines, language)
        return self.repeat_weight * reused + self.opening_weight * opening

"""RhymeTracker — maps form rhyme scheme to per-line targets during generation.

As lines are committed one by one the tracker:
  1. Records the rhyme key of the first line that opens each letter group.
  2. Returns that key as the target for every subsequent line in the same group.
  3. Provides a human-readable example word for use in LLM prompts.

Usage::

    tracker = RhymeTracker("ABBAABBACDCDCD", phonology)
    for i, line in enumerate(committed_lines):
        tracker.commit(i, line)

    # Before generating line i:
    target_key   = tracker.target_key_for_line(i)   # None = first of group
    example_word = tracker.example_word_for_line(i)  # None = first of group
    is_new       = tracker.is_new_rhyme(i)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poesia.phonology.base import PhonologyBackend


class RhymeTracker:
    """Tracks rhyme commitments for one poem, driven by a FormSpec rhyme scheme.

    Args:
        rhyme_scheme: A string like ``"ABBAABBACDCDCD"`` where each character
            is the rhyme-group letter for that line (0-indexed). ``"-"``
            means the line is free / not rhymed.
        phonology: The phonology backend used to extract rhyme keys from lines.
    """

    def __init__(self, rhyme_scheme: str, phonology: PhonologyBackend) -> None:
        # Strip spaces so "ABBA ABBA CDC DCD" and "ABBAABBACDCDCD" both work
        self._scheme: list[str] = list(rhyme_scheme.replace(" ", ""))
        self._phonology = phonology
        # letter → consonant rhyme key of the first committed line with that letter
        self._committed_keys: dict[str, str] = {}
        # letter → last word of that first committed line (for prompt examples)
        self._example_words: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Query API (call before generating a line)
    # ------------------------------------------------------------------

    def letter_for_line(self, line_index: int) -> str | None:
        """Return the rhyme-group letter for this line, or None if free/out-of-range."""
        if line_index >= len(self._scheme):
            return None
        letter = self._scheme[line_index]
        return None if letter == "-" else letter

    def is_new_rhyme(self, line_index: int) -> bool:
        """True if this line is the FIRST occurrence of its rhyme group."""
        letter = self.letter_for_line(line_index)
        return letter is not None and letter not in self._committed_keys

    def target_key_for_line(self, line_index: int) -> str | None:
        """Return the committed rhyme key for this line's group, or None if new."""
        letter = self.letter_for_line(line_index)
        if letter is None:
            return None
        return self._committed_keys.get(letter)

    def example_word_for_line(self, line_index: int) -> str | None:
        """Return the example word that established this line's rhyme group, or None."""
        letter = self.letter_for_line(line_index)
        if letter is None:
            return None
        return self._example_words.get(letter)

    # ------------------------------------------------------------------
    # Commit API (call after a line is accepted)
    # ------------------------------------------------------------------

    def commit(self, line_index: int, line: str) -> None:
        """Record the rhyme of an accepted line if it opens a new group."""
        letter = self.letter_for_line(line_index)
        if letter is None or letter in self._committed_keys:
            return  # free line or group already established

        rhyme_key = self._phonology.rhyme_key(line)
        key = rhyme_key.consonant
        if key:
            self._committed_keys[letter] = key
            # Grab the last word, stripped of trailing punctuation
            words = line.split()
            if words:
                last = words[-1].rstrip(".,;:!?¿¡\"'")
                self._example_words[letter] = last

    # ------------------------------------------------------------------
    # Introspection (for tests and debugging)
    # ------------------------------------------------------------------

    @property
    def committed_keys(self) -> dict[str, str]:
        """Read-only view of letter → rhyme key commitments so far."""
        return dict(self._committed_keys)

    @property
    def example_words(self) -> dict[str, str]:
        """Read-only view of letter → example word commitments so far."""
        return dict(self._example_words)

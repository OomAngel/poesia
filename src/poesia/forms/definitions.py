"""Concrete poetic form definitions.

Each `FormSpec` describes the structural constraints of a form: how many
lines/stanzas, target syllable count per line, and rhyme scheme (using the
conventional letter notation, e.g. ABBA ABBA CDC DCD for a Petrarchan
sonnet).

This is intentionally data, not behavior — the generation loop and evaluator
consume a FormSpec to know what to enforce.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormSpec:
    """Structural specification for a poetic form."""

    name: str
    language: str
    lines_per_stanza: list[int]  # e.g. [4, 4, 3, 3] for a sonnet
    syllables_per_line: int
    rhyme_scheme: str  # e.g. "ABBAABBACDCDCD"
    syllable_pattern: list[int] | None = None  # For variable patterns like haiku [5, 7, 5]

    @property
    def total_lines(self) -> int:
        return sum(self.lines_per_stanza)

    def syllables_for_line(self, line_index: int) -> int:
        """Get target syllable count for a specific line position (0-indexed).
        
        If syllable_pattern is provided, uses that (e.g., haiku: [5, 7, 5]).
        Otherwise, returns the uniform syllables_per_line.
        
        Args:
            line_index: 0-based line position in the poem
            
        Returns:
            Target syllable count for that line position
        """
        if self.syllable_pattern:
            # Use pattern, cycling if needed (though typically exact match)
            return self.syllable_pattern[line_index % len(self.syllable_pattern)]
        return self.syllables_per_line


# --- Spanish forms -----------------------------------------------------

SONETO_ES = FormSpec(
    name="soneto",
    language="es",
    lines_per_stanza=[4, 4, 3, 3],
    syllables_per_line=11,  # hendecasyllable
    rhyme_scheme="ABBAABBACDCDCD",
)

ROMANCE_ES = FormSpec(
    name="romance",
    language="es",
    lines_per_stanza=[],  # variable length, even-numbered lines assonate
    syllables_per_line=8,  # octosyllable
    rhyme_scheme="-A-A-A-A",  # even lines assonant-rhyme, odd lines free
)


# --- English forms ------------------------------------------------------

SONNET_SHAKESPEAREAN_EN = FormSpec(
    name="sonnet_shakespearean",
    language="en",
    lines_per_stanza=[4, 4, 4, 2],
    syllables_per_line=10,  # iambic pentameter
    rhyme_scheme="ABABCDCDEFEFGG",
)

HAIKU_EN = FormSpec(
    name="haiku",
    language="en",
    lines_per_stanza=[1, 1, 1],
    syllables_per_line=5,  # Default/typical, but pattern overrides
    rhyme_scheme="",
    syllable_pattern=[5, 7, 5],  # The defining 5-7-5 pattern
)

FORM_REGISTRY: dict[str, FormSpec] = {
    "soneto": SONETO_ES,
    "romance": ROMANCE_ES,
    "sonnet_shakespearean": SONNET_SHAKESPEAREAN_EN,
    "haiku": HAIKU_EN,
}


def get_form(name: str) -> FormSpec:
    """Look up a registered form by name, raising a clear error if unknown."""
    try:
        return FORM_REGISTRY[name]
    except KeyError as exc:
        known = ", ".join(sorted(FORM_REGISTRY))
        raise ValueError(f"Unknown form '{name}'. Known forms: {known}") from exc

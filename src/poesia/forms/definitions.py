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
    foot: str | None = None  # e.g. "iambic" for pentameter; None = no foot claim

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
    foot="iambic",
)

HAIKU_EN = FormSpec(
    name="haiku",
    language="en",
    lines_per_stanza=[1, 1, 1],
    syllables_per_line=5,  # Default/typical, but pattern overrides
    rhyme_scheme="",
    syllable_pattern=[5, 7, 5],  # The defining 5-7-5 pattern
)

# Haiku's 5-7-5 shape is not English-specific — it's a real, long-established
# form in Spanish poetry too, with the same structural constraint (rhyme-free,
# no foot claim). Registered separately from HAIKU_EN, rather than reused
# across languages, because FormSpec.language also drives the generation
# prompt's "write in X" instruction (see GenerationBrief._lang_name) — one
# shared spec would print the wrong language into that instruction whichever
# language it was tagged with.
HAIKU_ES = FormSpec(
    name="haiku",
    language="es",
    lines_per_stanza=[1, 1, 1],
    syllables_per_line=5,
    rhyme_scheme="",
    syllable_pattern=[5, 7, 5],
)

# Keyed by (name, language): most forms have real, language-specific
# structural rules (soneto's Petrarchan 11-syllable rules are not
# sonnet_shakespearean's 10-syllable iambic rules, even though both are
# "sonnets") and only exist for one language. haiku is the one form
# registered under the same name for more than one language.
FORM_REGISTRY: dict[tuple[str, str], FormSpec] = {
    ("soneto", "es"): SONETO_ES,
    ("romance", "es"): ROMANCE_ES,
    ("sonnet_shakespearean", "en"): SONNET_SHAKESPEAREAN_EN,
    ("haiku", "en"): HAIKU_EN,
    ("haiku", "es"): HAIKU_ES,
}


def get_form(name: str, language: str | None = None) -> FormSpec:
    """Look up a registered form by name, raising a clear error if unknown.

    Args:
        name: Registered form name (e.g. "soneto", "sonnet_shakespearean").
        language: If given, the form must actually be defined for this
            language. Without this, ``get_form("soneto", language="en")``
            used to silently return the *Spanish* soneto spec (11-syllable
            hendecasyllable, Petrarchan rhyme scheme) — the caller asked to
            write in English but every downstream syllable/rhyme/foot check
            would run against Spanish rules with no warning at all.
            If omitted, returns the form registered under `name` — or, for a
            name registered in more than one language (currently only
            "haiku"), an arbitrary but deterministic one. Callers that care
            which language they get should always pass `language`.
    """
    variants = {lang: spec for (n, lang), spec in FORM_REGISTRY.items() if n == name}
    if not variants:
        known = ", ".join(sorted({n for n, _ in FORM_REGISTRY}))
        raise ValueError(f"Unknown form '{name}'. Known forms: {known}")

    if language is None:
        return next(iter(variants.values()))

    try:
        return variants[language]
    except KeyError:
        available = ", ".join(sorted(variants))
        raise ValueError(
            f"Form '{name}' is not defined for language '{language}'. "
            f"'{name}' is available for: {available}."
        ) from None

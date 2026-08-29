"""Tests for poesia.forms.definitions: FormSpec + the form registry."""

from __future__ import annotations

import pytest

from poesia.forms.definitions import (
    FORM_REGISTRY,
    HAIKU_EN,
    HAIKU_ES,
    ROMANCE_ES,
    SONETO_ES,
    SONNET_SHAKESPEAREAN_EN,
    FormSpec,
    get_form,
)


def test_defined_form_shapes() -> None:
    """The four registered forms carry their structural constants."""
    assert SONETO_ES.language == "es"
    assert SONETO_ES.lines_per_stanza == [4, 4, 3, 3]
    assert SONETO_ES.total_lines == 14
    assert SONETO_ES.syllables_per_line == 11
    assert SONETO_ES.rhyme_scheme == "ABBAABBACDCDCD"

    assert SONNET_SHAKESPEAREAN_EN.language == "en"
    assert SONNET_SHAKESPEAREAN_EN.total_lines == 14
    assert SONNET_SHAKESPEAREAN_EN.syllables_per_line == 10
    assert SONNET_SHAKESPEAREAN_EN.rhyme_scheme == "ABABCDCDEFEFGG"

    assert HAIKU_EN.total_lines == 3
    assert HAIKU_EN.lines_per_stanza == [1, 1, 1]

    # Romance has no fixed stanza length -- lines_per_stanza is empty and
    # total_lines is therefore 0 (the form is variable-length by design).
    assert ROMANCE_ES.lines_per_stanza == []
    assert ROMANCE_ES.total_lines == 0


def test_form_registry_and_get_form() -> None:
    assert FORM_REGISTRY == {
        ("soneto", "es"): SONETO_ES,
        ("romance", "es"): ROMANCE_ES,
        ("sonnet_shakespearean", "en"): SONNET_SHAKESPEAREAN_EN,
        ("haiku", "en"): HAIKU_EN,
        ("haiku", "es"): HAIKU_ES,
    }
    assert get_form("soneto") is SONETO_ES
    with pytest.raises(ValueError, match="Unknown form 'villanelle'"):
        get_form("villanelle")


def test_get_form_language_mismatch_is_rejected() -> None:
    """`--form soneto --language en` used to silently return the *Spanish*
    soneto spec (wrong syllable count, wrong rhyme scheme) instead of the
    Shakespearean form the caller actually meant. Passing `language` now
    catches that instead of generating against the wrong rules."""
    with pytest.raises(ValueError, match="Form 'soneto' is not defined for language 'en'"):
        get_form("soneto", language="en")

    # Correct name for the requested language still resolves normally.
    assert get_form("sonnet_shakespearean", language="en") is SONNET_SHAKESPEAREAN_EN
    assert get_form("soneto", language="es") is SONETO_ES

    # No language given -> old, permissive behavior (name lookup only).
    assert get_form("soneto") is SONETO_ES


def test_get_form_language_mismatch_hint_lists_alternatives() -> None:
    with pytest.raises(ValueError, match="'soneto' is available for: es"):
        get_form("soneto", language="en")


def test_get_form_haiku_resolves_per_language() -> None:
    """haiku is the one form registered for more than one language — each
    variant is a distinct FormSpec instance (language field feeds the
    generation prompt directly), not one spec reused across languages."""
    assert get_form("haiku", language="en") is HAIKU_EN
    assert get_form("haiku", language="es") is HAIKU_ES
    assert HAIKU_EN.syllable_pattern == HAIKU_ES.syllable_pattern == [5, 7, 5]


def test_formspec_is_frozen() -> None:
    spec = FormSpec(
        name="test",
        language="en",
        lines_per_stanza=[4],
        syllables_per_line=8,
        rhyme_scheme="ABAB",
    )
    try:
        spec.name = "other"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("FormSpec should be frozen (immutable)")


def test_romance_total_lines_override() -> None:
    """The --lines CLI flag overrides total_lines for variable-length forms."""
    from poesia.generation.constrained_loop import ConstrainedLoop
    from poesia.generation.llm_client import StubLLMClient

    loop = ConstrainedLoop(language="es", form="romance", llm=StubLLMClient())

    # Without override, romance total_lines=0 means no lines generated
    result_no_override = loop.run(theme="test", n_candidates=2)
    assert len(result_no_override.lines) == 0, (
        f"Without --lines, romance should produce 0 lines, got {len(result_no_override.lines)}"
    )

    # With total_lines_override=8, should generate 8 lines
    result_override = loop.run(theme="test", n_candidates=2, total_lines_override=8)
    assert len(result_override.lines) == 8, (
        f"With --lines 8, romance should produce 8 lines, got {len(result_override.lines)}"
    )

    # With total_lines_override=16, should generate 16 lines
    result_16 = loop.run(theme="test", n_candidates=2, total_lines_override=16)
    assert len(result_16.lines) == 16, (
        f"With --lines 16, romance should produce 16 lines, got {len(result_16.lines)}"
    )

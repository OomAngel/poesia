"""Tests for poesia.forms.definitions: FormSpec + the form registry."""

from __future__ import annotations

import pytest

from poesia.forms.definitions import (
    FORM_REGISTRY,
    HAIKU_EN,
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
        "soneto": SONETO_ES,
        "romance": ROMANCE_ES,
        "sonnet_shakespearean": SONNET_SHAKESPEAREAN_EN,
        "haiku": HAIKU_EN,
    }
    assert get_form("soneto") is SONETO_ES
    with pytest.raises(ValueError, match="Unknown form 'villanelle'"):
        get_form("villanelle")


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

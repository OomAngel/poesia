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


def test_soneto_es_shape() -> None:
    assert SONETO_ES.language == "es"
    assert SONETO_ES.lines_per_stanza == [4, 4, 3, 3]
    assert SONETO_ES.total_lines == 14
    assert SONETO_ES.syllables_per_line == 11
    assert SONETO_ES.rhyme_scheme == "ABBAABBACDCDCD"


def test_sonnet_shakespearean_en_shape() -> None:
    assert SONNET_SHAKESPEAREAN_EN.language == "en"
    assert SONNET_SHAKESPEAREAN_EN.total_lines == 14
    assert SONNET_SHAKESPEAREAN_EN.syllables_per_line == 10
    assert SONNET_SHAKESPEAREAN_EN.rhyme_scheme == "ABABCDCDEFEFGG"


def test_haiku_en_shape() -> None:
    assert HAIKU_EN.total_lines == 3
    assert HAIKU_EN.lines_per_stanza == [1, 1, 1]


def test_romance_es_variable_length() -> None:
    # Romance has no fixed stanza length -- lines_per_stanza is empty and
    # total_lines is therefore 0 (the form is variable-length by design).
    assert ROMANCE_ES.lines_per_stanza == []
    assert ROMANCE_ES.total_lines == 0


def test_form_registry_contains_all_defined_forms() -> None:
    assert FORM_REGISTRY["soneto"] is SONETO_ES
    assert FORM_REGISTRY["romance"] is ROMANCE_ES
    assert FORM_REGISTRY["sonnet_shakespearean"] is SONNET_SHAKESPEAREAN_EN
    assert FORM_REGISTRY["haiku"] is HAIKU_EN


def test_get_form_returns_registered_form() -> None:
    assert get_form("soneto") is SONETO_ES


def test_get_form_raises_clear_error_for_unknown_form() -> None:
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

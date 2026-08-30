"""Tests for poesia.generation.router: form-aware default routing."""

from __future__ import annotations

from typing import Any

from poesia.generation.router import default_route_for


def _first_provider(route: list[dict[str, Any]]) -> str | None:
    return route[0]["provider"] if route else None


def _providers(route: list[dict[str, Any]]) -> list[str]:
    return [entry["provider"] for entry in route]


def test_fine_tune_leads_for_trained_spanish_forms() -> None:
    """The GGUF leads for the Spanish forms it was trained on."""
    for form in ("soneto", "romance"):
        route = default_route_for(form=form, language="es")
        assert _first_provider(route) == "llama_cpp"
        assert "llama_cpp" in _providers(route)


def test_fine_tune_skipped_for_other_spanish_forms() -> None:
    """Sparse/unseen Spanish forms skip the GGUF to avoid annotation overfit."""
    for form in ("haiku", "decima", "cuarteto", "quintilla"):
        route = default_route_for(form=form, language="es")
        assert "llama_cpp" not in _providers(route)
        assert _first_provider(route) == "groq"


def test_fine_tune_skipped_for_english_forms() -> None:
    """English forms never use the Spanish-trained GGUF."""
    for form in ("haiku", "sonnet_shakespearean"):
        route = default_route_for(form=form, language="en")
        assert "llama_cpp" not in _providers(route)
        assert _first_provider(route) == "groq"


def test_fine_tune_skipped_when_language_or_form_unknown() -> None:
    """Without a known es+form pair, the GGUF is skipped (safe default)."""
    assert "llama_cpp" not in _providers(default_route_for())
    assert "llama_cpp" not in _providers(default_route_for(form="soneto"))
    assert "llama_cpp" not in _providers(default_route_for(language="es"))

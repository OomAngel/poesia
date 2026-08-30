"""Tests for poesia.generation.router: default routing + overrides."""

from __future__ import annotations

from typing import Any

from poesia.generation.router import RoutedLLMClient, default_route_for


def _first_provider(route: list[dict[str, Any]]) -> str | None:
    return route[0]["provider"] if route else None


def _providers(route: list[dict[str, Any]]) -> list[str]:
    return [entry["provider"] for entry in route]


def test_default_route_is_form_agnostic_and_groq_first() -> None:
    """Every form/language starts with groq; the fine-tune is excluded."""
    for form, lang in [
        ("soneto", "es"),
        ("romance", "es"),
        ("haiku", "es"),
        ("haiku", "en"),
        ("sonnet_shakespearean", "en"),
        (None, None),
    ]:
        route = default_route_for(form=form, language=lang)
        assert _first_provider(route) == "groq"
        assert "llama_cpp" not in _providers(route)


def test_explicit_route_override_wins() -> None:
    """An explicit route is used verbatim, ignoring the default."""
    explicit = [{"provider": "stub"}]
    assert RoutedLLMClient(route=explicit)._route == explicit


def test_env_route_override(monkeypatch) -> None:
    """LLM_ROUTE overrides the default route."""
    monkeypatch.setenv("LLM_ROUTE", "stub,groq:gpt-x")
    assert RoutedLLMClient()._route == [
        {"provider": "stub"},
        {"provider": "groq", "model": "gpt-x"},
    ]

"""Unit tests for poesia.generation.titles: LLM-backed poem title suggestion."""

from __future__ import annotations

from poesia.generation.titles import (
    _clean_title,
    build_title_prompt,
    suggest_title,
)

LINES = [
    "The radicle that splits the sleeping seed",
    "reaches for light through soil and stubborn clay",
]


class _FakeClient:
    """Minimal LLMClient stand-in recording its calls."""

    def __init__(self, results: list[str] | None = None, error: Exception | None = None) -> None:
        self.results = results or [""]
        self.error = error
        self.calls: list[tuple[str, int, float]] = []

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        self.calls.append((prompt, n, temperature))
        if self.error:
            raise self.error
        return self.results


def test_suggest_title_strips_quotes_and_prefixes() -> None:
    client = _FakeClient(results=['Title: "A Harvest Hope"'])
    title = suggest_title(LINES, "en", "sonnet_shakespearean", "quinoa hope", client)
    assert title == "A Harvest Hope"


def test_suggest_title_keeps_first_line_only() -> None:
    client = _FakeClient(results=["In Greener Days.\n(A reflection on the couplet.)"])
    title = suggest_title(LINES, "en", "sonnet_shakespearean", "paths that converge", client)
    assert title == "In Greener Days"


def test_suggest_title_requests_single_candidate_at_lower_temperature() -> None:
    client = _FakeClient(results=["Harvest Hope"])
    suggest_title(LINES, "en", "sonnet_shakespearean", "theme", client)
    prompt, n, temperature = client.calls[0]
    assert n == 1
    assert temperature == 0.7
    assert "sonnet_shakespearean" in prompt
    assert "The radicle that splits" in prompt


def test_suggest_title_falls_back_on_error() -> None:
    client = _FakeClient(error=RuntimeError("offline"))
    title = suggest_title(LINES, "en", "sonnet_shakespearean", "A Harvest Hope", client)
    assert title == "A Harvest Hope"


def test_suggest_title_falls_back_on_empty_result() -> None:
    client = _FakeClient(results=[])
    title = suggest_title(LINES, "en", "sonnet_shakespearean", "hope", client)
    assert title == "hope"


def test_suggest_title_fallback_uses_first_line_for_long_theme() -> None:
    client = _FakeClient(error=RuntimeError("offline"))
    long_theme = "a very long theme " + "x" * 120
    title = suggest_title(LINES, "en", "sonnet", long_theme, client)
    assert title == LINES[0]


def test_build_title_prompt_mentions_language_form_theme() -> None:
    prompt = build_title_prompt(LINES, "es", "soneto", "luna")
    assert "soneto" in prompt
    assert "luna" in prompt
    assert "The radicle that splits" in prompt


def test_clean_title_truncates_long_titles() -> None:
    cleaned = _clean_title("word " * 60)
    assert len(cleaned) <= 80
    assert cleaned.endswith("word")

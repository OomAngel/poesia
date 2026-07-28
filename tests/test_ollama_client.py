"""Tests for OllamaClient — local LLM via Ollama API.

Uses mocked HTTP calls to avoid requiring Ollama to be running.
"""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import OllamaClient


# ---------------------------------------------------------------------------
# Construction and defaults
# ---------------------------------------------------------------------------


def test_ollama_client_default_model() -> None:
    client = OllamaClient()
    assert client.model == "gemma2:2b"


def test_ollama_client_default_host() -> None:
    client = OllamaClient()
    assert client.host == "http://localhost:11434"


def test_ollama_client_custom_model() -> None:
    client = OllamaClient(model="llama3.2:3b")
    assert client.model == "llama3.2:3b"


def test_ollama_client_custom_host() -> None:
    client = OllamaClient(host="http://192.168.1.100:11434")
    assert client.host == "http://192.168.1.100:11434"


def test_ollama_client_provider_attribute() -> None:
    client = OllamaClient()
    assert client.provider == "ollama"
    assert client.usage is not None


# ---------------------------------------------------------------------------
# Connection check
# ---------------------------------------------------------------------------


@patch("urllib.request.urlopen")
def test_check_available_raises_when_ollama_offline(mock_urlopen: MagicMock) -> None:
    from poesia.exceptions import LLMProviderError
    mock_urlopen.side_effect = ConnectionError("Connection refused")
    client = OllamaClient()
    with pytest.raises(LLMProviderError, match="Cannot connect to Ollama"):
        client._check_available()

# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------


def _mock_ollama(tag_models: list[str], responses: list[str]):
    """Helper: build a side_effect list for urlopen mocks.

    First call is the /api/tags check; subsequent calls are generate/chat.
    """
    tags_resp = MagicMock()
    tags_resp.read.return_value = json.dumps({
        "models": [{"name": m} for m in tag_models]
    }).encode("utf-8")
    tags_mock = MagicMock()
    tags_mock.__enter__.return_value = tags_resp

    effects = [tags_mock]
    for text in responses:
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "message": {"content": text}
        }).encode("utf-8")
        m = MagicMock()
        m.__enter__.return_value = resp
        effects.append(m)
    return effects


@patch("urllib.request.urlopen")
def test_generate_returns_lines(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = _mock_ollama(
        ["gemma2:2b"], ["luna en la noche"]
    )
    client = OllamaClient()
    results = client.generate("write a line about the moon", n=1)
    assert len(results) == 1
    assert "luna" in results[0]


@patch("urllib.request.urlopen")
def test_generate_multiple_candidates(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = _mock_ollama(
        ["gemma2:2b"],
        ["luna en la noche", "brilla la luna", "luna de plata"],
    )
    client = OllamaClient()
    results = client.generate("write about the moon", n=3)
    assert len(results) == 3
    assert results[0] == "luna en la noche"
    assert results[1] == "brilla la luna"
    assert results[2] == "luna de plata"


@patch("urllib.request.urlopen")
def test_generate_raises_provider_error_on_http_error(mock_urlopen: MagicMock) -> None:
    from poesia.exceptions import LLMProviderError

    tags_resp = MagicMock()
    tags_resp.read.return_value = json.dumps({
        "models": [{"name": "gemma2:2b"}]
    }).encode("utf-8")
    tags_mock = MagicMock()
    tags_mock.__enter__.return_value = tags_resp

    http_error = urllib.error.HTTPError(
        "http://localhost:11434/api/chat", 404,
        "Model not found", {}, None,
    )
    mock_urlopen.side_effect = [tags_mock, http_error]

    client = OllamaClient()
    with pytest.raises(LLMProviderError) as excinfo:
        client.generate("test", n=1)
    assert excinfo.value.status_code == 404
    assert excinfo.value.provider == "ollama"


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------


@patch("urllib.request.urlopen")
def test_repair_returns_corrected_line(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = _mock_ollama(
        ["gemma2:2b"], ["luna brillante en la noche"]
    )
    client = OllamaClient()
    result = client.repair("luna noche", "needs more syllables")
    assert "luna" in result


# ---------------------------------------------------------------------------
# Usage metadata
# ---------------------------------------------------------------------------


@patch("urllib.request.urlopen")
def test_usage_populated_after_generate(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = _mock_ollama(
        ["gemma2:2b"], ["luna en la noche"]
    )
    client = OllamaClient()
    client.generate("test", n=1)
    assert client.usage.latency_ms is not None
    assert client.usage.latency_ms >= 0
    assert client.usage.completion_tokens is not None



@patch("urllib.request.urlopen")
def test_check_available_succeeds_when_ollama_online(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "models": [{"name": "gemma2:2b"}]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    client = OllamaClient()
    client._check_available()
    assert client._checked is True

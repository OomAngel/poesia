"""Unit tests for HostedLLMClient and LLMClient implementations."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from poesia.generation.llm_client import HostedLLMClient, StubLLMClient


def test_stub_llm_client() -> None:
    """StubLLMClient generates short plausible lines based on theme extraction."""
    client = StubLLMClient()
    
    # Stub extracts theme and generates template-based lines
    candidates = client.generate("Theme: luna\nLanguage: es\nWrite a line", n=2)
    assert len(candidates) == 2
    # Should generate Spanish lines with "luna" theme, not echo prompt
    assert "luna" in candidates[0].lower()
    assert len(candidates[0].split()) <= 10  # Short lines, not full prompt
    
    # Repair adds a word
    repaired = client.repair("luna brillante", "syllables")
    assert "clara" in repaired  # Adds "clara" for syllable adjustment


def test_hosted_llm_client_missing_key() -> None:
    client = HostedLLMClient(api_key="", provider="openai")
    with pytest.raises(RuntimeError, match="requires an API key"):
        client.generate("hello")


@patch("urllib.request.urlopen")
def test_hosted_llm_client_openai_mock(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Generated poem line"}}]
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    client = HostedLLMClient(provider="openai", api_key="sk-test", model="gpt-4o-mini")
    res = client.generate("Write a line", n=1)

    assert len(res) == 1
    assert res[0] == "Generated poem line"


@patch("urllib.request.urlopen")
def test_hosted_llm_client_gemini_mock(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "candidates": [{"content": {"parts": [{"text": "Lluvia sobre la piedra"}]}}]
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    client = HostedLLMClient(provider="gemini", api_key="AIzaTestKey", model="gemini-2.5-flash")
    res = client.generate("Write a line", n=1)

    assert len(res) == 1
    assert res[0] == "Lluvia sobre la piedra"

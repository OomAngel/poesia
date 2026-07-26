"""Unit tests for HostedLLMClient and LLMClient implementations."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from poesia.generation.llm_client import HostedLLMClient, StubLLMClient


def test_stub_llm_client() -> None:
    client = StubLLMClient()
    candidates = client.generate("test prompt", n=2)
    assert len(candidates) == 2
    assert "test prompt" in candidates[0]

    repaired = client.repair("line", "syllables")
    assert "repaired: syllables" in repaired


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

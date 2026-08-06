"""OpenAI-compatible chat-completions wire contract (OpenAI + Groq).

OpenAI and Groq expose the same wire protocol — ``messages`` request shape,
``Authorization: Bearer`` auth, ``choices[].message.content`` response —
so their *wire-shape* tests are one parametrized family. Vendor-specific
behavior (Groq's n=1-sequential + pacing) lives in the provider files; this
module pins only the shared contract, per contract-testing practice.

Gemini is a different wire protocol (contents/candidates/key-in-URL) and is
tested in test_hosted_llm_gemini.py.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import HostedLLMClient


def _mock_openai_compat_response(content: str) -> MagicMock:
    """Build a mock urllib response returning an OpenAI-format choice."""
    mock = MagicMock()
    mock.read.return_value = json.dumps(
        {"choices": [{"message": {"content": content}}]}
    ).encode("utf-8")
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


@pytest.mark.parametrize("provider", ["openai", "groq"], indirect=False)
class TestOpenAICompatWire:
    """The shared request/response contract of the OpenAI-compatible family."""

    def _client(self, provider: str) -> HostedLLMClient:
        return HostedLLMClient(provider=provider, api_key="test-key", groq_pace_seconds=0)

    def test_request_payload_shape(self, provider: str) -> None:
        client = self._client(provider)
        captured = None

        def capture(req, timeout=None):
            nonlocal captured
            captured = json.loads(req.data.decode("utf-8"))
            return _mock_openai_compat_response("test output")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("Write a poem", n=2, temperature=0.7)

        assert captured["messages"] == [{"role": "user", "content": "Write a poem"}]
        assert captured["temperature"] == 0.7

    def test_authorization_bearer_header(self, provider: str) -> None:
        client = self._client(provider)
        captured_headers = None

        def capture(req, timeout=None):
            nonlocal captured_headers
            captured_headers = dict(req.headers)
            return _mock_openai_compat_response("output")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("prompt")

        assert captured_headers.get("Authorization") == "Bearer test-key"

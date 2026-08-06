"""Mock-based tests for HostedLLMClient OpenAI backend.

The shared OpenAI-compatible wire contract (payload shape, Bearer auth,
choices parsing) is covered once per provider in
test_hosted_llm_openai_compat.py. This file keeps only OpenAI-specific
behavior: n in a single request.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import HostedLLMClient


class TestOpenAIBackend:
    """Tests for OpenAI API integration."""

    @pytest.fixture
    def client(self) -> HostedLLMClient:
        return HostedLLMClient(provider="openai", api_key="test-key")

    def test_openai_uses_n_parameter_single_call(self, client: HostedLLMClient) -> None:
        """OpenAI should use n param in single request (unlike Gemini/Groq)."""
        call_count = 0

        def count_calls(req, timeout=None):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "choices": [
                    {"message": {"content": f"choice {i}"}} for i in range(3)
                ]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=count_calls):
            results = client.generate("prompt", n=3)

        assert call_count == 1  # Single call with n=3
        assert len(results) == 3

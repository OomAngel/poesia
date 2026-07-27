"""Mock-based tests for HostedLLMClient OpenAI backend."""

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import HostedLLMClient


class TestOpenAIBackend:
    """Tests for OpenAI API integration."""

    @pytest.fixture
    def client(self) -> HostedLLMClient:
        return HostedLLMClient(provider="openai", api_key="test-key")

    def test_openai_request_payload_shape(self, client: HostedLLMClient) -> None:
        """Verify OpenAI request payload has correct structure."""
        captured_request = None

        def capture_request(req, timeout=None):
            nonlocal captured_request
            captured_request = req
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "choices": [{"message": {"content": "test output"}}]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.generate("Write a poem", n=2, temperature=0.7)

        assert captured_request is not None
        payload = json.loads(captured_request.data.decode("utf-8"))

        assert payload["model"] == "gpt-4o-mini"
        assert payload["messages"] == [{"role": "user", "content": "Write a poem"}]
        assert payload["n"] == 2
        assert payload["temperature"] == 0.7

    def test_openai_authorization_header(self, client: HostedLLMClient) -> None:
        """Verify Bearer token in Authorization header."""
        captured_headers = None

        def capture_request(req, timeout=None):
            nonlocal captured_headers
            captured_headers = dict(req.headers)
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "choices": [{"message": {"content": "output"}}]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.generate("prompt")

        assert captured_headers is not None
        assert captured_headers.get("Authorization") == "Bearer test-key"

    def test_openai_response_parsing_multiple_choices(self, client: HostedLLMClient) -> None:
        """Verify correct parsing of multiple choices in response."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [
                {"message": {"content": "  First choice  "}},
                {"message": {"content": "Second choice"}},
            ]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = client.generate("prompt", n=2)

        assert results == ["First choice", "Second choice"]

    def test_openai_uses_n_parameter_single_call(self, client: HostedLLMClient) -> None:
        """OpenAI should use n param in single request (unlike Gemini)."""
        call_count = 0

        def count_calls(req, timeout=None):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "choices": [{"message": {"content": f"choice {i}"}} for i in range(3)]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=count_calls):
            results = client.generate("prompt", n=3)

        assert call_count == 1  # Single call with n=3
        assert len(results) == 3

"""Mock-based tests for HostedLLMClient Gemini backend.

Tests JSON payload shapes, response parsing, and error handling without
requiring real API keys or network access.
"""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import HostedLLMClient


class TestGeminiBackend:
    """Tests for Gemini API integration."""

    @pytest.fixture
    def client(self) -> HostedLLMClient:
        return HostedLLMClient(provider="gemini", api_key="test-key")

    def test_gemini_request_payload_shape(self, client: HostedLLMClient) -> None:
        """Verify Gemini request payload has correct structure."""
        captured_request = None

        def capture_request(req, timeout=None):
            nonlocal captured_request
            captured_request = req
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": "test output"}]}}]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.generate("Write a poem", n=1, temperature=0.8)

        assert captured_request is not None
        payload = json.loads(captured_request.data.decode("utf-8"))

        # Verify payload structure
        assert "contents" in payload
        assert len(payload["contents"]) == 1
        assert "parts" in payload["contents"][0]
        assert payload["contents"][0]["parts"][0]["text"] == "Write a poem"
        assert "generationConfig" in payload
        assert payload["generationConfig"]["temperature"] == 0.8

    def test_gemini_url_includes_api_key(self, client: HostedLLMClient) -> None:
        """Verify API key is included in URL query param."""
        captured_url = None

        def capture_request(req, timeout=None):
            nonlocal captured_url
            captured_url = req.full_url
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": "output"}]}}]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.generate("prompt")

        assert captured_url is not None
        assert "key=test-key" in captured_url
        assert "generativelanguage.googleapis.com" in captured_url

    def test_gemini_response_parsing(self, client: HostedLLMClient) -> None:
        """Verify correct parsing of Gemini response format."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": [
                {"content": {"parts": [{"text": "  La luna brilla  "}]}}
            ]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = client.generate("prompt", n=1)

        assert results == ["La luna brilla"]  # Stripped whitespace

    def test_gemini_multiple_candidates_sequential(self, client: HostedLLMClient) -> None:
        """Verify n>1 makes n sequential calls (current implementation)."""
        call_count = 0

        def count_calls(req, timeout=None):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": f"output {call_count}"}]}}]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=count_calls):
            results = client.generate("prompt", n=3)

        assert call_count == 3
        assert len(results) == 3

    def test_gemini_empty_response_handling(self, client: HostedLLMClient) -> None:
        """Handle malformed/empty Gemini response gracefully."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": []  # Empty candidates
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = client.generate("prompt", n=1)

        # Should return empty string, not crash
        assert results == [""]

    def test_gemini_http_error_handling(self, client: HostedLLMClient) -> None:
        """Verify HTTP errors are wrapped with context."""
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="https://api.example.com",
            code=429,
            msg="Rate limit exceeded",
            hdrs={},
            fp=BytesIO(b'{"error": "quota exceeded"}'),
        )

        with patch("urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(RuntimeError) as exc_info:
                client.generate("prompt")

        assert "Gemini API HTTP Error 429" in str(exc_info.value)
        assert "quota exceeded" in str(exc_info.value)

"""Mock-based tests for HostedLLMClient Gemini backend.

Tests JSON payload shapes, response parsing, and error handling without
requiring real API keys or network access.
"""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from poesia.exceptions import LLMProviderError
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
            mock_response.read.return_value = json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "test output"}]}}]}
            ).encode("utf-8")
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
            mock_response.read.return_value = json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "output"}]}}]}
            ).encode("utf-8")
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
        mock_response.read.return_value = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "  La luna brilla  "}]}}]}
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            results = client.generate("prompt", n=1)

        assert results == ["La luna brilla"]  # Stripped whitespace

    def test_gemini_batched_candidates_single_call(self, client: HostedLLMClient) -> None:
        """Verify n<=8 uses single API call with candidateCount."""
        call_count = 0
        captured_payload = None

        def capture_single_call(req, timeout=None):
            nonlocal call_count, captured_payload
            call_count += 1
            captured_payload = json.loads(req.data.decode("utf-8"))
            mock_response = MagicMock()
            # Return 3 candidates in one response
            mock_response.read.return_value = json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "output 1"}]}},
                        {"content": {"parts": [{"text": "output 2"}]}},
                        {"content": {"parts": [{"text": "output 3"}]}},
                    ]
                }
            ).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_single_call):
            results = client.generate("prompt", n=3)

        # Should be a single call with candidateCount=3
        assert call_count == 1
        assert captured_payload["generationConfig"]["candidateCount"] == 3
        assert len(results) == 3
        assert results == ["output 1", "output 2", "output 3"]

    def test_gemini_large_n_batches_in_chunks(self, client: HostedLLMClient) -> None:
        """Verify n>8 batches into multiple calls."""
        call_count = 0
        captured_candidate_counts = []

        def count_batches(req, timeout=None):
            nonlocal call_count
            call_count += 1
            payload = json.loads(req.data.decode("utf-8"))
            n_requested = payload["generationConfig"]["candidateCount"]
            captured_candidate_counts.append(n_requested)

            mock_response = MagicMock()
            # Return requested number of candidates
            mock_response.read.return_value = json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": f"output {i}"}]}}
                        for i in range(n_requested)
                    ]
                }
            ).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=count_batches):
            results = client.generate("prompt", n=10)

        # Should make 2 calls: 8 + 2
        assert call_count == 2
        assert captured_candidate_counts == [8, 2]
        assert len(results) == 10

    def test_gemini_empty_response_handling(self, client: HostedLLMClient) -> None:
        """Handle malformed/empty Gemini response gracefully."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "candidates": []  # Empty candidates
            }
        ).encode("utf-8")
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
            with pytest.raises(LLMProviderError) as exc_info:
                client.generate("prompt")

        assert "Gemini API HTTP Error 429" in str(exc_info.value)
        assert "quota exceeded" in str(exc_info.value)

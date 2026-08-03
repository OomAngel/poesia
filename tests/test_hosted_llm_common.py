"""Mock-based tests for HostedLLMClient common functionality."""

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.exceptions import LLMProviderError
from poesia.generation.llm_client import HostedLLMClient


class TestProviderAutoDetection:
    """Tests for automatic provider detection from environment."""

    def test_auto_detects_gemini_from_env(self) -> None:
        """Provider auto-detects gemini when GEMINI_API_KEY is set."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "gemini-key"}, clear=True):
            client = HostedLLMClient(provider="auto")

        assert client.provider == "gemini"
        assert client.api_key == "gemini-key"
        assert client.model == "gemini-2.5-flash"

    def test_auto_detects_openai_from_env(self) -> None:
        """Provider auto-detects openai when OPENAI_API_KEY is set."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"}, clear=True):
            client = HostedLLMClient(provider="auto")

        assert client.provider == "openai"
        assert client.api_key == "openai-key"
        assert client.model == "gpt-4o-mini"

    def test_gemini_takes_precedence(self) -> None:
        """When both keys present, Gemini takes precedence."""
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "gemini-key",
            "OPENAI_API_KEY": "openai-key",
        }, clear=True):
            client = HostedLLMClient(provider="auto")

        assert client.provider == "gemini"

    def test_no_key_raises_on_generate(self) -> None:
        """Generate raises clear error when no API key available."""
        with patch.dict("os.environ", {}, clear=True):
            client = HostedLLMClient(provider="auto")

        with pytest.raises(LLMProviderError) as exc_info:
            client.generate("prompt")

        assert "requires an API key" in str(exc_info.value)


class TestRepairMethod:
    """Tests for the repair() convenience method."""

    @pytest.fixture
    def client(self) -> HostedLLMClient:
        return HostedLLMClient(provider="gemini", api_key="test-key")

    def test_repair_prompt_format(self, client: HostedLLMClient) -> None:
        """Verify repair prompt includes line and defect description."""
        captured_payload = None

        def capture_request(req, timeout=None):
            nonlocal captured_payload
            captured_payload = json.loads(req.data.decode("utf-8"))
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": "fixed line"}]}}]
            }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.repair("La luna brila", "spelling error")

        prompt = captured_payload["contents"][0]["parts"][0]["text"]
        assert "La luna brila" in prompt
        assert "spelling error" in prompt

    def test_repair_strips_quotes(self, client: HostedLLMClient) -> None:
        """Verify repair strips surrounding quotes from response."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": '"La luna brilla"'}]}}]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.repair("La luna brila", "spelling")

        assert result == "La luna brilla"

"""Mock-based tests for HostedLLMClient common functionality."""

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.exceptions import LLMProviderError
from poesia.generation.llm_client import HostedLLMClient


class TestProviderAutoDetection:
    """Tests for automatic provider detection from environment."""

    @pytest.mark.parametrize(
        ("env", "expected_provider", "expected_model"),
        [
            ({"GEMINI_API_KEY": "gemini-key"}, "gemini", "gemini-2.5-flash"),
            ({"OPENAI_API_KEY": "openai-key"}, "openai", "gpt-4o-mini"),
            ({"GROQ_API_KEY": "gsk_test"}, "groq", "qwen/qwen3.8-27b"),
        ],
        ids=["gemini", "openai", "groq"],
    )
    def test_auto_detects_provider_from_env(
        self, env: dict, expected_provider: str, expected_model: str
    ) -> None:
        """A provider is auto-detected when its key is the only one set."""
        with patch.dict("os.environ", env, clear=True):
            client = HostedLLMClient(provider="auto")
        assert client.provider == expected_provider
        assert client.api_key == list(env.values())[0]
        assert client.model == expected_model

    @pytest.mark.parametrize(
        ("env", "expected_provider"),
        [
            ({"GEMINI_API_KEY": "g", "GROQ_API_KEY": "gsk"}, "gemini"),
            ({"GEMINI_API_KEY": "g", "OPENAI_API_KEY": "o"}, "gemini"),
            ({"GROQ_API_KEY": "gsk", "OPENAI_API_KEY": "o"}, "groq"),
        ],
        ids=["gemini-over-groq", "gemini-over-openai", "groq-over-openai"],
    )
    def test_auto_detection_precedence(self, env: dict, expected_provider: str) -> None:
        """Precedence: Gemini → Groq → OpenAI when multiple keys are present."""
        with patch.dict("os.environ", env, clear=True):
            client = HostedLLMClient(provider="auto")
        assert client.provider == expected_provider

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
            mock_response.read.return_value = json.dumps(
                {"candidates": [{"content": {"parts": [{"text": "fixed line"}]}}]}
            ).encode("utf-8")
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
        mock_response.read.return_value = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": '"La luna brilla"'}]}}]}
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.repair("La luna brila", "spelling")

        assert result == "La luna brilla"

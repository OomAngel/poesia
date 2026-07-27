"""Mock-based tests for HostedLLMClient Grok (xAI) backend."""

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import HostedLLMClient


def _mock_response(content: str | list[str]) -> MagicMock:
    """Build a mock urllib response returning OpenAI-format choices."""
    if isinstance(content, str):
        choices = [{"message": {"content": content}}]
    else:
        choices = [{"message": {"content": c}} for c in content]
    mock = MagicMock()
    mock.read.return_value = json.dumps({"choices": choices}).encode("utf-8")
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestGrokConstruction:
    """HostedLLMClient construction for the grok provider."""

    def test_default_model(self) -> None:
        c = HostedLLMClient(provider="grok", api_key="key")
        assert c.model == "grok-3-mini"

    def test_provider_stored(self) -> None:
        c = HostedLLMClient(provider="grok", api_key="key")
        assert c.provider == "grok"

    def test_custom_model(self) -> None:
        c = HostedLLMClient(provider="grok", api_key="key", model="grok-4")
        assert c.model == "grok-4"


class TestGrokAutoDetection:
    """Auto-detection of grok provider from XAI_API_KEY."""

    def test_auto_detects_grok_from_env(self) -> None:
        with patch.dict("os.environ", {"XAI_API_KEY": "xai-key"}, clear=True):
            c = HostedLLMClient(provider="auto")
        assert c.provider == "grok"
        assert c.api_key == "xai-key"
        assert c.model == "grok-3-mini"

    def test_gemini_takes_precedence_over_grok(self) -> None:
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "g-key", "XAI_API_KEY": "xai-key",
        }, clear=True):
            c = HostedLLMClient(provider="auto")
        assert c.provider == "gemini"

    def test_grok_takes_precedence_over_openai(self) -> None:
        with patch.dict("os.environ", {
            "XAI_API_KEY": "xai-key", "OPENAI_API_KEY": "oai-key",
        }, clear=True):
            c = HostedLLMClient(provider="auto")
        assert c.provider == "grok"


class TestGrokHTTPShape:
    """Grok HTTP request format and response parsing."""

    @pytest.fixture
    def client(self) -> HostedLLMClient:
        return HostedLLMClient(provider="grok", api_key="xai-test-key")

    def test_hits_xai_base_url(self, client: HostedLLMClient) -> None:
        captured_url = None

        def capture(req, timeout=None):
            nonlocal captured_url
            captured_url = req.full_url
            return _mock_response("una línea")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("prompt")

        assert captured_url == "https://api.x.ai/v1/chat/completions"

    def test_payload_shape(self, client: HostedLLMClient) -> None:
        captured = None

        def capture(req, timeout=None):
            nonlocal captured
            captured = json.loads(req.data.decode("utf-8"))
            return _mock_response("out")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("Write a haiku", n=3, temperature=0.8)

        assert captured["model"] == "grok-3-mini"
        assert captured["messages"] == [{"role": "user", "content": "Write a haiku"}]
        assert captured["n"] == 3
        assert captured["temperature"] == 0.8

    def test_bearer_token_header(self, client: HostedLLMClient) -> None:
        captured_headers = None

        def capture(req, timeout=None):
            nonlocal captured_headers
            captured_headers = dict(req.headers)
            return _mock_response("out")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("prompt")

        assert captured_headers["Authorization"] == "Bearer xai-test-key"

    def test_response_parsing_multiple_choices(self, client: HostedLLMClient) -> None:
        with patch("urllib.request.urlopen", return_value=_mock_response(["  line one  ", "line two"])):
            results = client.generate("prompt", n=2)
        assert results == ["line one", "line two"]

    def test_http_error_labels_grok(self, client: HostedLLMClient) -> None:
        import urllib.error
        err = urllib.error.HTTPError(
            url="https://api.x.ai/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=MagicMock(read=MagicMock(return_value=b'{"error":"invalid key"}')),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(RuntimeError, match="Grok API HTTP Error 401"):
                client.generate("prompt")

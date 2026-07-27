"""Mock-based tests for HostedLLMClient Groq Cloud backend."""

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import HostedLLMClient


def _mock_response(content: str) -> MagicMock:
    """Build a mock urllib response returning a single OpenAI-format choice."""
    mock = MagicMock()
    mock.read.return_value = json.dumps({
        "choices": [{"message": {"content": content}}]
    }).encode("utf-8")
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestGroqConstruction:
    def test_default_model(self) -> None:
        c = HostedLLMClient(provider="groq", api_key="gsk_test")
        assert c.model == "llama-3.3-70b-versatile"

    def test_provider_stored(self) -> None:
        c = HostedLLMClient(provider="groq", api_key="gsk_test")
        assert c.provider == "groq"

    def test_custom_model(self) -> None:
        c = HostedLLMClient(provider="groq", api_key="gsk_test", model="llama-3.1-8b-instant")
        assert c.model == "llama-3.1-8b-instant"


class TestGroqAutoDetection:
    def test_auto_detects_groq_from_env(self) -> None:
        with patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test"}, clear=True):
            c = HostedLLMClient(provider="auto")
        assert c.provider == "groq"
        assert c.api_key == "gsk_test"
        assert c.model == "llama-3.3-70b-versatile"

    def test_gemini_takes_precedence_over_groq(self) -> None:
        with patch.dict("os.environ", {
            "GEMINI_API_KEY": "g-key", "GROQ_API_KEY": "gsk_test",
        }, clear=True):
            c = HostedLLMClient(provider="auto")
        assert c.provider == "gemini"

    def test_groq_takes_precedence_over_openai(self) -> None:
        with patch.dict("os.environ", {
            "GROQ_API_KEY": "gsk_test", "OPENAI_API_KEY": "oai-key",
        }, clear=True):
            c = HostedLLMClient(provider="auto")
        assert c.provider == "groq"


class TestGroqHTTPShape:
    @pytest.fixture
    def client(self) -> HostedLLMClient:
        return HostedLLMClient(provider="groq", api_key="gsk_test")

    def test_hits_groq_base_url(self, client: HostedLLMClient) -> None:
        captured_url = None

        def capture(req, timeout=None):
            nonlocal captured_url
            captured_url = req.full_url
            return _mock_response("una línea")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("prompt")

        assert captured_url == "https://api.groq.com/openai/v1/chat/completions"

    def test_payload_always_sends_n1(self, client: HostedLLMClient) -> None:
        """Groq requires n=1 — payload must always have n=1 even when caller asks for more."""
        captured_n_values: list[int] = []

        def capture(req, timeout=None):
            payload = json.loads(req.data.decode("utf-8"))
            captured_n_values.append(payload["n"])
            return _mock_response("out")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("prompt", n=3)

        assert all(v == 1 for v in captured_n_values), f"Expected all n=1, got {captured_n_values}"

    def test_payload_shape(self, client: HostedLLMClient) -> None:
        captured = None

        def capture(req, timeout=None):
            nonlocal captured
            captured = json.loads(req.data.decode("utf-8"))
            return _mock_response("out")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("Write a haiku", temperature=0.8)

        assert captured["model"] == "llama-3.3-70b-versatile"
        assert captured["messages"] == [{"role": "user", "content": "Write a haiku"}]
        assert captured["temperature"] == 0.8

    def test_bearer_token_header(self, client: HostedLLMClient) -> None:
        captured_headers = None

        def capture(req, timeout=None):
            nonlocal captured_headers
            captured_headers = dict(req.headers)
            return _mock_response("out")

        with patch("urllib.request.urlopen", side_effect=capture):
            client.generate("prompt")

        assert captured_headers["Authorization"] == "Bearer gsk_test"

    def test_n_greater_than_1_makes_sequential_calls(self, client: HostedLLMClient) -> None:
        """n>1 issues n separate HTTP calls (Groq does not support n>1 natively)."""
        responses = ["línea uno", "línea dos", "línea tres"]
        call_count = 0

        def capture(req, timeout=None):
            nonlocal call_count
            r = _mock_response(responses[call_count])
            call_count += 1
            return r

        with patch("urllib.request.urlopen", side_effect=capture):
            results = client.generate("prompt", n=3)

        assert call_count == 3
        assert results == ["línea uno", "línea dos", "línea tres"]

    def test_response_stripped(self, client: HostedLLMClient) -> None:
        with patch("urllib.request.urlopen", return_value=_mock_response("  primera línea  ")):
            results = client.generate("prompt")
        assert results == ["primera línea"]

    def test_http_error_labels_groq(self, client: HostedLLMClient) -> None:
        import urllib.error
        err = urllib.error.HTTPError(
            url="https://api.groq.com/openai/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=MagicMock(read=MagicMock(return_value=b'{"error":"invalid key"}')),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(RuntimeError, match="Groq API HTTP Error 401"):
                client.generate("prompt")

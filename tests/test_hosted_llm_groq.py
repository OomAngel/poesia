"""Mock-based tests for HostedLLMClient Groq Cloud backend."""

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.exceptions import LLMProviderError
from poesia.generation.llm_client import HostedLLMClient


def _mock_response(content: str) -> MagicMock:
    """Build a mock urllib response returning a single OpenAI-format choice."""
    mock = MagicMock()
    mock.read.return_value = json.dumps({"choices": [{"message": {"content": content}}]}).encode(
        "utf-8"
    )
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestGroqConstruction:
    def test_construction_defaults_and_overrides(self) -> None:
        c = HostedLLMClient(provider="groq", api_key="gsk_test")
        assert c.provider == "groq"
        assert c.model == "llama-3.3-70b-versatile"

        custom = HostedLLMClient(provider="groq", api_key="gsk_test", model="llama-3.1-8b-instant")
        assert custom.model == "llama-3.1-8b-instant"


class TestGroqHTTPShape:
    @pytest.fixture
    def client(self) -> HostedLLMClient:
        # Disable the deliberate 2.1s rate-limit pacing between sequential
        # calls — the HTTP shape tests are about payload/headers, not pacing.
        return HostedLLMClient(provider="groq", api_key="gsk_test", groq_pace_seconds=0)

    def test_groq_pace_is_configurable(self) -> None:
        """The 2.1s default pacing is a parameter, not a hardcoded sleep."""
        default = HostedLLMClient(provider="groq", api_key="gsk_test")
        assert default.groq_pace_seconds == 2.1
        fast = HostedLLMClient(provider="groq", api_key="gsk_test", groq_pace_seconds=0)
        assert fast.groq_pace_seconds == 0

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
            with pytest.raises(LLMProviderError, match="Groq API HTTP Error 401"):
                client.generate("prompt")

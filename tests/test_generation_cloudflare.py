"""Unit tests for CloudflareLLMClient (OpenAI-compatible Workers AI chat)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.exceptions import LLMProviderError
from poesia.generation.cloudflare import CloudflareLLMClient


def _client() -> CloudflareLLMClient:
    return CloudflareLLMClient(account_id="acct-test", api_token="tok-test")


@patch("urllib.request.urlopen")
def test_generate_returns_n_candidates_in_one_request(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"choices": [{"message": {"content": f"verso {i}"}} for i in range(3)]}
    ).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    client = _client()
    results = client.generate("Escribe un verso.", n=3)

    assert results == ["verso 0", "verso 1", "verso 2"]
    req = mock_urlopen.call_args[0][0]  # one request
    body = json.loads(req.data)
    assert body["n"] == 3
    assert body["model"] == client.DEFAULT_MODEL
    assert "acct-test" in req.full_url


def test_generate_requires_credentials() -> None:
    # Scrub the process env (the autouse conftest fixture already strips
    # provider vars, but do it explicitly here too) to prove the client
    # refuses to run without credentials, regardless of ambient shell state.
    with patch.dict("os.environ", {}, clear=True):
        client = CloudflareLLMClient(account_id="", api_token="")
        with pytest.raises(LLMProviderError, match="CLOUDFLARE_ACCOUNT_ID"):
            client.generate("hola")


@patch("urllib.request.urlopen")
def test_generate_http_error_raises_structured(mock_urlopen: MagicMock) -> None:
    import urllib.error

    class FakeHTTPError(urllib.error.HTTPError):
        def __init__(self) -> None:
            super().__init__("url", 500, "boom", None, None)  # type: ignore[arg-type]
            self._body = b"server error"

        def read(self) -> bytes:
            return self._body

    mock_urlopen.side_effect = FakeHTTPError()
    with pytest.raises(LLMProviderError, match="HTTP Error 500"):
        _client().generate("hola")


def test_repair_returns_cleaned_line() -> None:
    client = _client()
    with patch.object(client, "generate", return_value=["verso corregido"]):
        assert client.repair("verso malo", "too many syllables") == "verso corregido"

"""LLM_EXTRA reaches the request body of the OpenAI-compatible client.

Hosted reasoning models (Qwen 3.8 on OpenRouter) count hidden reasoning against max_tokens,
so a line request capped at 120 tokens can come back empty unless reasoning is switched off.
"""

from __future__ import annotations

import io
import json
from unittest.mock import patch

from poesia.generation.llm_client import OpenAICompatClient


def _response(text: str) -> io.BytesIO:
    body = {"choices": [{"message": {"content": text}}]}
    resp = io.BytesIO(json.dumps(body).encode("utf-8"))
    resp.__enter__ = lambda self=resp: self  # type: ignore[method-assign]
    resp.__exit__ = lambda *a: None  # type: ignore[method-assign]
    return resp


def test_llm_extra_is_merged_into_the_request(monkeypatch) -> None:
    monkeypatch.setenv("LLM_EXTRA", '{"reasoning": {"enabled": false}}')
    client = OpenAICompatClient(base_url="https://example.test/v1", model="m", api_key="k")
    sent = {}

    def fake_urlopen(req, timeout=None):
        sent.update(json.loads(req.data.decode("utf-8")))
        return _response("luna en la noche")

    with patch("urllib.request.urlopen", fake_urlopen):
        client._chat([{"role": "user", "content": "x"}], 0.7, max_tokens=120)
    assert sent["reasoning"] == {"enabled": False}
    assert sent["max_tokens"] == 120 and sent["model"] == "m"


def test_no_llm_extra_sends_nothing_more(monkeypatch) -> None:
    monkeypatch.delenv("LLM_EXTRA", raising=False)
    client = OpenAICompatClient(base_url="https://example.test/v1", model="m")
    assert client.extra == {}

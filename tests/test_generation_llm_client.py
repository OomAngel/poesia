"""Unit tests for HostedLLMClient and LLMClient implementations."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.generation.llm_client import HostedLLMClient, StubLLMClient


def test_stub_llm_client() -> None:
    """StubLLMClient generates short plausible lines based on theme extraction."""
    client = StubLLMClient()

    # Stub extracts theme and generates template-based lines
    candidates = client.generate("Theme: luna\nLanguage: es\nWrite a line", n=2)
    assert len(candidates) == 2
    # Should generate Spanish lines with "luna" theme, not echo prompt
    assert "luna" in candidates[0].lower()
    assert len(candidates[0].split()) <= 10  # Short lines, not full prompt

    # Repair adds a word
    repaired = client.repair("luna brillante", "syllables")
    assert "clara" in repaired  # Adds "clara" for syllable adjustment


def test_lora_client_batches_candidates() -> None:
    """LoRAClient draws all n candidates in ONE forward pass (batching)."""
    import torch

    from poesia.generation.llm_client import LoRAClient

    if not torch.cuda.is_available():
        pytest.skip("LoRA batching test needs CUDA (generate() targets .to('cuda'))")

    client = LoRAClient()

    class FakeModel:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def generate(self, **kwargs: object) -> torch.Tensor:
            self.calls.append(kwargs)
            input_ids = kwargs["input_ids"]  # (1, prompt_len)
            assert input_ids.shape[0] == 1  # one shared prompt, batched sampling
            n_seq = int(kwargs["num_return_sequences"])
            rows = []
            for i in range(n_seq):
                base = input_ids.repeat(1, 1)
                fill = torch.full((1, 3), i + 5, device=input_ids.device)
                rows.append(torch.cat([base, fill], dim=1))
            return torch.cat(rows, dim=0)

    class FakeEncoding(dict):
        """dict + attribute access + .to(), like transformers BatchEncoding."""

        @property
        def input_ids(self) -> torch.Tensor:
            return self["input_ids"]

        @property
        def attention_mask(self) -> torch.Tensor:
            return self["attention_mask"]

        def to(self, device: str) -> FakeEncoding:
            self["input_ids"] = self["input_ids"].to(device)
            self["attention_mask"] = self["attention_mask"].to(device)
            return self

    class FakeTokenizer:
        pad_token_id = 0

        def __call__(self, text: str, return_tensors: str = "pt") -> FakeEncoding:
            ids = torch.tensor([[1, 2, 3, 4]])
            return FakeEncoding({"input_ids": ids, "attention_mask": torch.ones_like(ids)})

        def decode(self, seq: torch.Tensor, skip_special_tokens: bool = True) -> str:
            return f"verso de prueba {int(seq[-1])}"

    client._model = FakeModel()  # type: ignore[attr-defined]
    client._tokenizer = FakeTokenizer()  # type: ignore[attr-defined]

    results = client.generate("Write line 1. Exactly 11 syllables.", n=3)

    assert len(client._model.calls) == 1  # batched: a single forward pass
    call = client._model.calls[0]
    assert call["num_return_sequences"] == 3
    assert call["input_ids"].shape[0] == 1
    assert len(results) == 3
    assert all(r.startswith("verso de prueba") for r in results)


def test_hosted_llm_client_missing_key() -> None:
    from poesia.exceptions import LLMProviderError

    client = HostedLLMClient(api_key="", provider="openai")
    with pytest.raises(LLMProviderError, match="requires an API key"):
        client.generate("hello")


@patch("urllib.request.urlopen")
def test_hosted_llm_client_openai_mock(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"choices": [{"message": {"content": "Generated poem line"}}]}
    ).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    client = HostedLLMClient(provider="openai", api_key="sk-test", model="gpt-4o-mini")
    res = client.generate("Write a line", n=1)

    assert len(res) == 1
    assert res[0] == "Generated poem line"


@patch("urllib.request.urlopen")
def test_hosted_llm_client_gemini_mock(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"candidates": [{"content": {"parts": [{"text": "Lluvia sobre la piedra"}]}}]}
    ).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    client = HostedLLMClient(provider="gemini", api_key="AIzaTestKey", model="gemini-2.5-flash")
    res = client.generate("Write a line", n=1)

    assert len(res) == 1
    assert res[0] == "Lluvia sobre la piedra"

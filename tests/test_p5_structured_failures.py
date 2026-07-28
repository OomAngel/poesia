"""P5 — Structured failure types and error visibility.

Tests that all errors in the system inherit from PoesiaError and that
specific error types are raised in the correct failure scenarios.
"""

from __future__ import annotations

import pytest

from poesia.exceptions import (
    EmbeddingError,
    EmbeddingValidationError,
    FormError,
    FormDefinitionError,
    IndexCompatibilityError,
    IndexError,
    LLMError,
    LLMProviderError,
    PhonologyBackendError,
    PhonologyError,
    PoesiaError,
)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_all_exceptions_inherit_poesia_error() -> None:
    exceptions = [
        EmbeddingError, EmbeddingValidationError,
        FormError, FormDefinitionError,
        IndexCompatibilityError, IndexError,
        LLMError, LLMProviderError,
        PhonologyBackendError, PhonologyError,
    ]
    for exc in exceptions:
        assert issubclass(exc, PoesiaError), f"{exc.__name__} not a PoesiaError"


def test_catch_all_poesia_errors() -> None:
    from poesia.memoria.embedding_validation import EmbeddingValidationError
    from poesia.memoria.graphrag import IndexCompatibilityError
    for exc in [
        EmbeddingValidationError("test"),
        IndexCompatibilityError("old", 384, "new", 768),
        LLMProviderError("test"),
        FormDefinitionError("test"),
        PhonologyBackendError("test"),
    ]:
        with pytest.raises(PoesiaError):
            raise exc


# ---------------------------------------------------------------------------
# Embedding errors: dual inheritance
# ---------------------------------------------------------------------------


def test_embedding_error_caught_by_poesia_error() -> None:
    from poesia.memoria.embedding_validation import EmbeddingValidationError as EVE
    with pytest.raises(PoesiaError):
        raise EVE("bad embedding")


def test_embedding_error_caught_by_value_error() -> None:
    from poesia.memoria.embedding_validation import EmbeddingValidationError as EVE
    with pytest.raises(ValueError):
        raise EVE("bad embedding")


# ---------------------------------------------------------------------------
# Index errors: dual inheritance
# ---------------------------------------------------------------------------


def test_index_error_caught_by_poesia_error() -> None:
    from poesia.memoria.graphrag import IndexCompatibilityError as ICE
    with pytest.raises(PoesiaError):
        raise ICE("old", 384, "new", 768)


def test_index_error_caught_by_runtime_error() -> None:
    from poesia.memoria.graphrag import IndexCompatibilityError as ICE
    with pytest.raises(RuntimeError):
        raise ICE("old-model", 384, "new-model", 768)


# ---------------------------------------------------------------------------
# LLM provider errors: structured attributes
# ---------------------------------------------------------------------------


def test_llm_provider_error_structured() -> None:
    err = LLMProviderError(
        "rate limited", provider="groq", status_code=429,
        response_body='{"error": "rate limit"}',
    )
    assert err.provider == "groq"
    assert err.status_code == 429
    assert err.response_body == '{"error": "rate limit"}'


def test_llm_provider_error_defaults() -> None:
    err = LLMProviderError("generic")
    assert err.provider is None
    assert err.status_code is None
    assert err.response_body is None


def test_llm_provider_error_caught_by_llm_error() -> None:
    with pytest.raises(LLMError):
        raise LLMProviderError("API Error")


# ---------------------------------------------------------------------------
# HostedLLMClient uses structured errors
# ---------------------------------------------------------------------------


def test_llm_client_raises_provider_error_without_key() -> None:
    from poesia.generation.llm_client import HostedLLMClient
    client = HostedLLMClient(provider="groq", api_key="")
    with pytest.raises(LLMProviderError) as excinfo:
        client.generate("test")
    assert "API key" in str(excinfo.value)
    assert excinfo.value.provider == "groq"


# ---------------------------------------------------------------------------
# LLMUsage dataclass
# ---------------------------------------------------------------------------


def test_llm_usage_defaults() -> None:
    from poesia.generation.llm_client import LLMUsage
    u = LLMUsage()
    assert u.prompt_tokens is None
    assert u.completion_tokens is None
    assert u.total_tokens is None
    assert u.latency_ms is None


def test_llm_usage_accepts_values() -> None:
    from poesia.generation.llm_client import LLMUsage
    u = LLMUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150, latency_ms=1234.5)
    assert u.prompt_tokens == 50
    assert u.completion_tokens == 100
    assert u.total_tokens == 150
    assert u.latency_ms == 1234.5

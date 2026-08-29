"""P5 — Structured failure types and error visibility.

Errors inherit from PoesiaError; the dual-inheritance exceptions are catchable
by both their contract bases (ValueError / RuntimeError); and the one
behavioral guarantee: a hosted client without a key raises a structured
LLMProviderError.
"""

from __future__ import annotations

import pytest

from poesia.exceptions import (
    EmbeddingError,
    EmbeddingValidationError,
    FormDefinitionError,
    FormError,
    IndexCompatibilityError,
    IndexError,
    LLMError,
    LLMProviderError,
    PhonologyBackendError,
    PhonologyError,
    PoesiaError,
)

_ALL_EXCEPTIONS = [
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
]


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_all_exceptions_inherit_poesia_error() -> None:
    for exc in _ALL_EXCEPTIONS:
        assert issubclass(exc, PoesiaError), f"{exc.__name__} not a PoesiaError"


@pytest.mark.parametrize(
    ("make_exc", "bases"),
    [
        (lambda: EmbeddingValidationError("bad embedding"), [PoesiaError, ValueError]),
        (lambda: IndexCompatibilityError("old", 384, "new", 768), [PoesiaError, RuntimeError]),
    ],
)
def test_specialized_errors_catchable_by_contract_bases(make_exc, bases) -> None:  # noqa: ANN001
    """Dual-inheritance exceptions are catchable by both their base classes."""
    exc = make_exc()
    for base in bases:
        with pytest.raises(base):
            raise exc


# ---------------------------------------------------------------------------
# LLM provider errors: structured attributes
# ---------------------------------------------------------------------------


def test_llm_provider_error_structured() -> None:
    err = LLMProviderError(
        "rate limited",
        provider="groq",
        status_code=429,
        response_body='{"error": "rate limit"}',
    )
    assert err.provider == "groq"
    assert err.status_code == 429
    assert err.response_body == '{"error": "rate limit"}'

    generic = LLMProviderError("generic")
    assert generic.provider is None
    assert generic.status_code is None
    assert generic.response_body is None


def test_llm_client_raises_provider_error_without_key() -> None:
    from unittest.mock import patch

    from poesia.generation.llm_client import HostedLLMClient

    # Isolate from real provider keys (e.g. from a loaded .env) — otherwise
    # api_key="" alone doesn't guarantee "no key" reaches a live provider if
    # something upstream regresses the explicit-empty-string handling.
    with patch.dict("os.environ", {}, clear=True):
        client = HostedLLMClient(provider="groq", api_key="")
        with pytest.raises(LLMProviderError) as excinfo:
            client.generate("test")
    assert "API key" in str(excinfo.value)
    assert excinfo.value.provider == "groq"

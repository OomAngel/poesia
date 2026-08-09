"""Structured exception hierarchy for PoesIA.

Every error the system can produce inherits from ``PoesiaError`` so that
callers can catch a single base type or specific subtypes for granular
handling. This replaces bare ``RuntimeError`` and ``ValueError`` raises
throughout the codebase.
"""

from __future__ import annotations


class PoesiaError(Exception):
    """Base exception for all PoesIA errors."""


# ── Embedding / Vector errors ───────────────────────────────────────────────


class EmbeddingError(PoesiaError):
    """Base for embedding-related failures."""


class EmbeddingValidationError(EmbeddingError, ValueError):
    """Raised when an embedding violates expected shape or value constraints.

    Dual-inherits ValueError so legacy ``except ValueError`` call sites and
    the P5 contract base keep catching it.
    """


class EmbeddingClientError(EmbeddingError):
    """Raised when the embedding client fails (network, model load, etc.)."""


# ── Index / Graph errors ────────────────────────────────────────────────────


class IndexError(PoesiaError):
    """Base for index/graph-related failures."""


class IndexCompatibilityError(IndexError, RuntimeError):
    """Raised when an embedding client is incompatible with the loaded index.

    Dual-inherits RuntimeError so legacy ``except RuntimeError`` call sites
    and the P5 contract base keep catching it.
    """


class IndexStaleError(IndexError):
    """Raised when the persisted graph index is stale relative to source data."""


# ── LLM / Generation errors ─────────────────────────────────────────────────


class LLMError(PoesiaError):
    """Base for LLM-related failures."""


class LLMProviderError(LLMError):
    """API / network / authentication failure from an LLM provider.

    Attributes:
        provider: Provider name (``\"groq\"``, ``\"gemini\"``, ``\"openai\"``).
        status_code: HTTP status code if applicable.
        response_body: Raw response body if available.
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class LLMTokenLimitError(LLMError):
    """Raised when the context exceeds the provider's token limit."""


class LLMContentFilterError(LLMError):
    """Raised when the provider's content filter blocks the response."""


# ── Form / Definition errors ────────────────────────────────────────────────


class FormError(PoesiaError):
    """Base for form definition errors."""


class FormDefinitionError(FormError):
    """Raised when a form name is not found in the registry."""


# ── Phonology errors ────────────────────────────────────────────────────────


class PhonologyError(PoesiaError):
    """Base for phonology backend errors."""


class PhonologyBackendError(PhonologyError):
    """Raised when a phonology backend cannot be loaded or used."""

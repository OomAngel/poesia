"""Embedding validation for RAG/LLM hardening (P0).

Provides boundary validation for embedding vectors to catch contract violations
early and make embedding failures explicit rather than silent.
"""

from __future__ import annotations

import math
from typing import Any


from poesia.exceptions import EmbeddingValidationError as _PoesiaEmbeddingError

class EmbeddingValidationError(_PoesiaEmbeddingError, ValueError):
    """Raised when an embedding violates expected shape or value constraints.

    Multiple inheritance: caught by ``except PoesiaError`` (generic handling)
    or ``except ValueError`` (legacy compatibility).
    """

    pass


def validate_embedding_vector(
    vector: Any,
    expected_dimension: int | None = None,
    context: str = "embedding",
) -> list[float]:
    """Validate that a value is a proper 1D embedding vector.

    Args:
        vector: The value to validate (should be list[float]).
        expected_dimension: If provided, validate the vector has this exact length.
        context: Description for error messages (e.g., "theme embedding").

    Returns:
        The validated vector (same as input if valid).

    Raises:
        EmbeddingValidationError: If validation fails.

    P0 validation criteria:
    - Must be a list (not nested, not scalar)
    - All elements must be numeric (int/float)
    - All elements must be finite (not NaN, not inf)
    - If expected_dimension provided, length must match
    """
    if not isinstance(vector, list):
        raise EmbeddingValidationError(
            f"{context}: expected list, got {type(vector).__name__}"
        )

    if not vector:
        raise EmbeddingValidationError(f"{context}: empty vector")

    # Check for nested lists (would indicate scalar/batch confusion)
    if isinstance(vector[0], list):
        raise EmbeddingValidationError(
            f"{context}: got nested list (shape {len(vector)} x {len(vector[0])}), "
            "expected flat 1D vector. This suggests embed() was called with a scalar "
            "string instead of embed_one()."
        )

    # Validate all elements are numeric and finite
    for i, val in enumerate(vector):
        if not isinstance(val, (int, float)):
            raise EmbeddingValidationError(
                f"{context}[{i}]: expected numeric value, got {type(val).__name__}"
            )
        if not math.isfinite(val):
            raise EmbeddingValidationError(
                f"{context}[{i}]: non-finite value ({val})"
            )

    # Validate dimension if specified
    if expected_dimension is not None and len(vector) != expected_dimension:
        raise EmbeddingValidationError(
            f"{context}: dimension mismatch, expected {expected_dimension}, "
            f"got {len(vector)}"
        )

    return vector


def validate_embedding_batch(
    vectors: Any,
    expected_dimension: int | None = None,
    context: str = "embedding batch",
) -> list[list[float]]:
    """Validate a batch of embedding vectors.

    Args:
        vectors: The value to validate (should be list[list[float]]).
        expected_dimension: If provided, validate all vectors have this dimension.
        context: Description for error messages.

    Returns:
        The validated vectors (same as input if valid).

    Raises:
        EmbeddingValidationError: If validation fails.
    """
    if not isinstance(vectors, list):
        raise EmbeddingValidationError(
            f"{context}: expected list, got {type(vectors).__name__}"
        )

    if not vectors:
        raise EmbeddingValidationError(f"{context}: empty batch")

    # Validate each vector
    for i, vec in enumerate(vectors):
        try:
            validate_embedding_vector(vec, expected_dimension, f"{context}[{i}]")
        except EmbeddingValidationError as e:
            # Re-raise with batch context
            raise EmbeddingValidationError(str(e)) from e

    return vectors


def check_dimension_compatibility(
    vec_a: list[float],
    vec_b: list[float],
    context: str = "dimension compatibility",
) -> None:
    """Check that two vectors have compatible dimensions for similarity.

    Args:
        vec_a: First vector.
        vec_b: Second vector.
        context: Description for error messages.

    Raises:
        EmbeddingValidationError: If dimensions don't match.
    """
    if len(vec_a) != len(vec_b):
        raise EmbeddingValidationError(
            f"{context}: dimension mismatch, "
            f"vector A has {len(vec_a)} dimensions, "
            f"vector B has {len(vec_b)} dimensions"
        )

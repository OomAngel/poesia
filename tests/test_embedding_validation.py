"""Tests for embedding validation (P0 RAG/LLM hardening)."""

from __future__ import annotations

import math

import pytest

from poesia.memoria.embedding_validation import (
    EmbeddingValidationError,
    check_dimension_compatibility,
    validate_embedding_batch,
    validate_embedding_vector,
)


def test_validate_embedding_vector_accepts_valid_flat_vector() -> None:
    """Valid 1D float vector passes validation."""
    vec = [0.1, 0.2, -0.3, 0.0, 1.0]
    result = validate_embedding_vector(vec)
    assert result == vec


def test_validate_embedding_vector_accepts_integers() -> None:
    """Integers are valid numeric values."""
    vec = [1, 2, 3]
    result = validate_embedding_vector(vec)
    assert result == vec


def test_validate_embedding_vector_rejects_nested_list() -> None:
    """Nested list (batch instead of scalar) is caught with clear message."""
    nested = [[0.1, 0.2], [0.3, 0.4]]
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector(nested)

    err_msg = str(exc_info.value)
    assert "nested list" in err_msg.lower()
    assert "embed()" in err_msg  # Suggests fix
    assert "embed_one()" in err_msg


def test_validate_embedding_vector_rejects_non_list() -> None:
    """Non-list values (e.g., scalar) are rejected."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector(0.5)  # type: ignore

    assert "expected list" in str(exc_info.value)


def test_validate_embedding_vector_rejects_empty() -> None:
    """Empty list is rejected."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector([])

    assert "empty" in str(exc_info.value)


def test_validate_embedding_vector_rejects_non_numeric() -> None:
    """Non-numeric elements are rejected."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector([0.1, "invalid", 0.3])  # type: ignore

    assert "expected numeric" in str(exc_info.value)


def test_validate_embedding_vector_rejects_nan() -> None:
    """NaN values are rejected."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector([0.1, float("nan"), 0.3])

    assert "non-finite" in str(exc_info.value)


def test_validate_embedding_vector_rejects_inf() -> None:
    """Infinite values are rejected."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector([0.1, float("inf"), 0.3])

    assert "non-finite" in str(exc_info.value)


def test_validate_embedding_vector_validates_dimension() -> None:
    """Dimension mismatch is caught when expected_dimension is provided."""
    vec = [0.1, 0.2, 0.3]

    # Should pass with correct dimension
    validate_embedding_vector(vec, expected_dimension=3)

    # Should fail with wrong dimension
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector(vec, expected_dimension=5)

    assert "dimension mismatch" in str(exc_info.value)
    assert "expected 5" in str(exc_info.value)
    assert "got 3" in str(exc_info.value)


def test_validate_embedding_vector_includes_context() -> None:
    """Context string appears in error messages."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector([], context="theme embedding")

    assert "theme embedding" in str(exc_info.value)


def test_validate_embedding_batch_accepts_valid_batch() -> None:
    """Valid batch of vectors passes."""
    batch = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    result = validate_embedding_batch(batch)
    assert result == batch


def test_validate_embedding_batch_rejects_empty_batch() -> None:
    """Empty batch is rejected."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_batch([])

    assert "empty batch" in str(exc_info.value)


def test_validate_embedding_batch_rejects_non_list() -> None:
    """Non-list batch is rejected."""
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_batch("not a list")  # type: ignore

    assert "expected list" in str(exc_info.value)


def test_validate_embedding_batch_validates_each_vector() -> None:
    """Each vector in batch is validated."""
    batch = [[0.1, 0.2], [float("nan"), 0.4]]

    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_batch(batch)

    err_msg = str(exc_info.value)
    assert "[1]" in err_msg  # Second vector (index 1)
    assert "non-finite" in err_msg


def test_validate_embedding_batch_enforces_dimension_consistency() -> None:
    """All vectors must have the same dimension when expected_dimension is set."""
    batch = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    # Should pass with correct dimension
    validate_embedding_batch(batch, expected_dimension=2)

    # Should fail if any vector has wrong dimension
    batch_mixed = [[0.1, 0.2], [0.3, 0.4, 0.5]]
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_batch(batch_mixed, expected_dimension=2)

    assert "dimension mismatch" in str(exc_info.value)


def test_check_dimension_compatibility_accepts_same_dimension() -> None:
    """Vectors with same dimension pass compatibility check."""
    vec_a = [0.1, 0.2, 0.3]
    vec_b = [0.4, 0.5, 0.6]
    # Should not raise
    check_dimension_compatibility(vec_a, vec_b)


def test_check_dimension_compatibility_rejects_mismatch() -> None:
    """Vectors with different dimensions fail compatibility check."""
    vec_a = [0.1, 0.2]
    vec_b = [0.3, 0.4, 0.5]

    with pytest.raises(EmbeddingValidationError) as exc_info:
        check_dimension_compatibility(vec_a, vec_b)

    err_msg = str(exc_info.value)
    assert "dimension mismatch" in err_msg
    assert "vector A has 2" in err_msg
    assert "vector B has 3" in err_msg


def test_check_dimension_compatibility_includes_context() -> None:
    """Context appears in error message."""
    vec_a = [0.1, 0.2]
    vec_b = [0.3, 0.4, 0.5]

    with pytest.raises(EmbeddingValidationError) as exc_info:
        check_dimension_compatibility(vec_a, vec_b, context="theme/query comparison")

    assert "theme/query comparison" in str(exc_info.value)


def test_scalar_batch_confusion_detection() -> None:
    """The specific P0 bug pattern is clearly detected.

    This is the critical test case from the hardening plan: when a string
    is passed to embed() instead of embed_one(), Python iterates over
    characters producing shape (len, dim) instead of (dim,).

    Example from the plan:
        embed("abc") -> shape (3, 384)
        embed_one("abc") -> shape (384,)
    """
    # Simulate what happens when embed() gets a scalar string
    # The string iterates as ['a', 'b', 'c']
    # Each character produces a 384-d vector
    # Result: nested list with shape (3, 384)
    malformed = [
        [0.1] * 384,  # Embedding of 'a'
        [0.2] * 384,  # Embedding of 'b'
        [0.3] * 384,  # Embedding of 'c'
    ]

    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector(malformed, expected_dimension=384)

    err_msg = str(exc_info.value).lower()
    assert "nested list" in err_msg
    assert "3 x 384" in err_msg
    assert "flat 1d vector" in err_msg
    assert "embed()" in err_msg
    assert "embed_one()" in err_msg

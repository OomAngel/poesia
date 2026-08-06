"""Tests for embedding validation (P0 RAG/LLM hardening).

Three pure functions, tested compactly with parametrization: valid input is
accepted unchanged; every invalid shape/value is rejected with a clear,
actionable message.
"""

from __future__ import annotations

import pytest

from poesia.memoria.embedding_validation import (
    EmbeddingValidationError,
    check_dimension_compatibility,
    validate_embedding_batch,
    validate_embedding_vector,
)


def test_validate_embedding_vector_accepts_valid_input() -> None:
    assert validate_embedding_vector([0.1, 0.2, -0.3, 0.0, 1.0]) == [0.1, 0.2, -0.3, 0.0, 1.0]
    assert validate_embedding_vector([1, 2, 3]) == [1, 2, 3]  # integers are numeric


@pytest.mark.parametrize(
    ("vector", "needle"),
    [
        ([[0.1, 0.2], [0.3, 0.4]], "nested list"),  # the scalar/batch confusion bug
        (0.5, "expected list"),
        ([], "empty"),
        ([0.1, "invalid", 0.3], "expected numeric"),
        ([0.1, float("nan"), 0.3], "non-finite"),
        ([0.1, float("inf"), 0.3], "non-finite"),
    ],
)
def test_validate_embedding_vector_rejects_bad_input(vector, needle) -> None:  # noqa: ANN001
    with pytest.raises(EmbeddingValidationError, match=needle):
        validate_embedding_vector(vector)  # type: ignore[arg-type]


def test_validate_embedding_vector_dimension_and_context() -> None:
    vec = [0.1, 0.2, 0.3]
    validate_embedding_vector(vec, expected_dimension=3)  # matches → no raise
    with pytest.raises(EmbeddingValidationError, match="dimension mismatch"):
        validate_embedding_vector(vec, expected_dimension=5)
    with pytest.raises(EmbeddingValidationError, match="theme embedding"):
        validate_embedding_vector([], context="theme embedding")


def test_scalar_batch_confusion_detection() -> None:
    """The exact P0 bug: embed('abc') → shape (3, 384) instead of (384,)."""
    malformed = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
    with pytest.raises(EmbeddingValidationError) as exc_info:
        validate_embedding_vector(malformed, expected_dimension=384)
    err = str(exc_info.value).lower()
    assert "nested list" in err and "3 x 384" in err
    assert "embed()" in err and "embed_one()" in err


def test_validate_embedding_batch() -> None:
    batch = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    assert validate_embedding_batch(batch) == batch
    validate_embedding_batch(batch, expected_dimension=2)  # matches → no raise

    with pytest.raises(EmbeddingValidationError, match="empty batch"):
        validate_embedding_batch([])
    with pytest.raises(EmbeddingValidationError, match="expected list"):
        validate_embedding_batch("not a list")  # type: ignore[arg-type]
    with pytest.raises(EmbeddingValidationError, match=r"\[1\].*non-finite"):
        validate_embedding_batch([[0.1, 0.2], [float("nan"), 0.4]])
    with pytest.raises(EmbeddingValidationError, match="dimension mismatch"):
        validate_embedding_batch([[0.1, 0.2], [0.3, 0.4, 0.5]], expected_dimension=2)


def test_check_dimension_compatibility() -> None:
    check_dimension_compatibility([0.1, 0.2, 0.3], [0.4, 0.5, 0.6])  # same → no raise
    with pytest.raises(EmbeddingValidationError, match="dimension mismatch"):
        check_dimension_compatibility([0.1, 0.2], [0.3, 0.4, 0.5])
    with pytest.raises(EmbeddingValidationError, match="theme/query comparison"):
        check_dimension_compatibility([0.1, 0.2], [0.3, 0.4, 0.5],
                                      context="theme/query comparison")

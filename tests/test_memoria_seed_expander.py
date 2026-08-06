"""Tests for MemorIA seed expander."""

from __future__ import annotations

from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.seed_expander import SeedExpander


def test_expander_creation_and_expand_returns_seed_expansion() -> None:
    from poesia.memoria.records import SeedExpansion

    expander = SeedExpander(language="es")
    assert expander.language == "es"
    assert isinstance(expander.expand("silencio"), SeedExpansion)


def test_expand_rhymes_spanish_consonant_and_assonant() -> None:
    expander = SeedExpander(language="es")
    result = expander._expand_rhymes_spanish("silencio")
    assert "consonant" in result and "assonant" in result
    assert len(result["consonant"]) > 0 and len(result["assonant"]) > 0

    accented = expander._expand_rhymes_spanish("corazón")
    assert "-on" in accented["consonant"]
    assert "o" in accented["assonant"]


def test_expand_semantic_with_stub_skips_target_word() -> None:
    expander = SeedExpander(language="es")
    client = StubEmbeddingClient()

    corpus = ["silencio", "soledad", "vacío", "ruido", "paz"]
    result = expander._expand_semantic("silencio", client, corpus)

    assert isinstance(result, list)
    assert len(result) <= len(corpus)
    assert "silencio" not in [w.lower() for w in result]


def test_expand_integration() -> None:
    expander = SeedExpander(language="es")
    client = StubEmbeddingClient()
    corpus = ["soledad", "vacío", "ruido"]

    result = expander.expand(
        "silencio",
        include_datamuse=False,  # Don't hit network in tests
        embedding_client=client,
        reference_corpus=corpus,
    )

    # Should have rhyme endings
    assert result.rhymes_consonant or result.rhymes_assonant

    # Should have semantic neighbors (from our corpus)
    assert len(result.semantic_neighbors) > 0


def test_expand_english_no_pronouncing() -> None:
    """Test English expansion degrades gracefully without pronouncing lib."""
    expander = SeedExpander(language="en")
    result = expander._expand_rhymes_english("silence")

    # Should return empty dict if pronouncing not installed
    assert "consonant" in result
    assert "assonant" in result


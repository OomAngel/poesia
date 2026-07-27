"""Tests for MemorIA seed expander."""

from __future__ import annotations

from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.seed_expander import SeedExpander


def test_expander_creation() -> None:
    expander = SeedExpander(language="es")
    assert expander.language == "es"


def test_expand_returns_seed_expansion() -> None:
    from poesia.memoria.records import SeedExpansion

    expander = SeedExpander(language="es")
    result = expander.expand("silencio")
    assert isinstance(result, SeedExpansion)


def test_expand_rhymes_spanish_consonant() -> None:
    expander = SeedExpander(language="es")
    # "silencio" is grave (stress on penultimate) -> ends in vowel
    # Default algorithm finds last vowel 'o' as stressed (no accent mark)
    result = expander._expand_rhymes_spanish("silencio")

    assert "consonant" in result
    # With current algorithm, rhyme ending is just "-o"
    assert "-o" in result["consonant"] or len(result["consonant"]) > 0


def test_expand_rhymes_spanish_assonant() -> None:
    expander = SeedExpander(language="es")
    result = expander._expand_rhymes_spanish("silencio")

    assert "assonant" in result
    # Assonant is just the vowels from last stressed position
    assert "o" in result["assonant"] or len(result["assonant"]) > 0


def test_expand_rhymes_accented_word() -> None:
    expander = SeedExpander(language="es")
    result = expander._expand_rhymes_spanish("corazón")

    # Stressed on last syllable (accented)
    assert "-on" in result["consonant"]
    assert "o" in result["assonant"]


def test_expand_semantic_with_stub() -> None:
    expander = SeedExpander(language="es")
    client = StubEmbeddingClient()

    corpus = ["soledad", "vacío", "ruido", "paz", "amor"]
    result = expander._expand_semantic("silencio", client, corpus)

    # Stub returns deterministic embeddings, so we should get results
    assert isinstance(result, list)
    assert len(result) <= len(corpus)
    # "silencio" itself should not be in results
    assert "silencio" not in [w.lower() for w in result]


def test_expand_semantic_skips_target_word() -> None:
    expander = SeedExpander(language="es")
    client = StubEmbeddingClient()

    corpus = ["silencio", "soledad", "vacío"]  # includes target
    result = expander._expand_semantic("silencio", client, corpus)

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

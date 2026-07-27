"""Tests for MemorIA extended record types."""

from __future__ import annotations

from datetime import datetime

from poesia.memoria.records import (
    FragmentRecord,
    InfluenceRecord,
    SeedExpansion,
    SeedRecord,
)


def test_fragment_record_creation() -> None:
    fragment = FragmentRecord(
        id="test-fragment",
        content="El que ve el sistema entero y el detalle que lo deshace.",
        language="es",
        tone=["watchful", "precise"],
        themes=["perception", "pattern"],
        tags=["self-knowledge"],
    )

    assert fragment.id == "test-fragment"
    assert fragment.language == "es"
    assert "watchful" in fragment.tone
    assert "perception" in fragment.themes


def test_fragment_record_defaults() -> None:
    fragment = FragmentRecord(
        id="minimal",
        content="Just content",
        language="en",
    )

    assert fragment.tone == []
    assert fragment.themes == []
    assert fragment.tags == []
    assert fragment.movement is None
    assert fragment.poet_anchor is None
    assert isinstance(fragment.created_at, datetime)


def test_seed_expansion_creation() -> None:
    expansion = SeedExpansion(
        synonyms=["callar", "mudez", "sigilo"],
        antonyms=["ruido", "estruendo"],
        rhymes_consonant={"-encio": ["silencio", "presencia"]},
        rhymes_assonant={"e-o": ["silencio", "tiempo", "viento"]},
        semantic_neighbors=["soledad", "vacío"],
        collocations=["romper el silencio", "guardar silencio"],
        etymology="Latin silentium",
        cross_language={"en": "silence", "nl": "stilte", "zh": "沉默"},
    )

    assert len(expansion.synonyms) == 3
    assert "ruido" in expansion.antonyms
    assert expansion.cross_language["zh"] == "沉默"


def test_seed_record_creation() -> None:
    seed = SeedRecord(
        id="silencio-cluster",
        root_word="silencio",
        language="es",
        tags=["absence", "communication"],
        expansion=SeedExpansion(
            synonyms=["callar", "mudez"],
            rhymes_assonant={"e-o": ["tiempo", "viento"]},
        ),
    )

    assert seed.root_word == "silencio"
    assert len(seed.expansion.synonyms) == 2
    assert "tiempo" in seed.expansion.rhymes_assonant["e-o"]


def test_seed_record_defaults() -> None:
    seed = SeedRecord(
        id="minimal",
        root_word="word",
        language="en",
    )

    assert seed.tags == []
    assert seed.notes is None
    assert seed.expansion.synonyms == []


def test_influence_record_creation() -> None:
    influence = InfluenceRecord(
        id="machado",
        name="Antonio Machado",
        language="es",
        movement="Generación del 98",
        era="1875-1939",
        tone=["spare", "meditative", "honest"],
        forms=["romance", "soneto"],
        exemplars=[
            "Caminante, son tus huellas el camino y nada más",
            "Hoy es siempre todavía",
        ],
    )

    assert influence.name == "Antonio Machado"
    assert influence.movement == "Generación del 98"
    assert "meditative" in influence.tone
    assert len(influence.exemplars) == 2


def test_influence_record_defaults() -> None:
    influence = InfluenceRecord(
        id="test",
        name="Test Poet",
        language="en",
    )

    assert influence.movement is None
    assert influence.tone == []
    assert influence.forms == []
    assert influence.exemplars == []
    assert influence.anti_patterns == []

"""Tests for MemorIA extended record types."""

from __future__ import annotations

from datetime import datetime

from poesia.memoria.records import (
    FragmentRecord,
    InfluenceRecord,
    SeedExpansion,
    SeedRecord,
)


def test_fragment_record_creation_and_defaults() -> None:
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

    minimal = FragmentRecord(id="minimal", content="Just content", language="en")
    assert minimal.tone == [] and minimal.themes == [] and minimal.tags == []
    assert minimal.movement is None and minimal.poet_anchor is None
    assert isinstance(minimal.created_at, datetime)


def test_seed_expansion_and_seed_record() -> None:
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

    minimal_seed = SeedRecord(id="minimal", root_word="word", language="en")
    assert minimal_seed.tags == [] and minimal_seed.notes is None
    assert minimal_seed.expansion.synonyms == []


def test_influence_record_creation_and_defaults() -> None:
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

    minimal = InfluenceRecord(id="test", name="Test Poet", language="en")
    assert minimal.movement is None
    assert minimal.tone == [] and minimal.forms == []
    assert minimal.exemplars == [] and minimal.anti_patterns == []

"""Tests for YAML-based influence loading."""

import pytest

from poesia.memoria.influence_loader import (
    clear_cache,
    get_influence_by_id,
    get_influences_by_language,
    get_influences_by_tone,
    load_influences,
)


@pytest.fixture(autouse=True)
def clear_influence_cache():
    """Clear the loader cache before each test."""
    clear_cache()
    yield
    clear_cache()


class TestLoadInfluences:
    """Tests for the main load_influences function."""

    def test_loads_all_influences(self) -> None:
        """Load all influences from data/influences.yaml."""
        influences = load_influences()
        # Should have Spanish + English + Dutch influences
        assert len(influences) >= 20

    def test_spanish_influences_have_correct_language(self) -> None:
        """Spanish section influences have language='es'."""
        influences = load_influences()
        machado = next((i for i in influences if i.id == "antonio_machado"), None)
        assert machado is not None
        assert machado.language == "es"
        assert machado.name == "Antonio Machado"

    def test_english_influences_have_correct_language(self) -> None:
        """English section influences have language='en'."""
        influences = load_influences()
        frost = next((i for i in influences if i.id == "robert_frost"), None)
        assert frost is not None
        assert frost.language == "en"

    def test_dutch_influences_have_correct_language(self) -> None:
        """Dutch section influences have language='nl'."""
        influences = load_influences()
        kloos = next((i for i in influences if i.id == "willem_kloos"), None)
        assert kloos is not None
        assert kloos.language == "nl"

    def test_influence_has_tone_list(self) -> None:
        """Influences have tone as list of strings."""
        influences = load_influences()
        machado = next((i for i in influences if i.id == "antonio_machado"), None)
        assert machado is not None
        assert isinstance(machado.tone, list)
        assert "spare" in machado.tone
        assert "meditative" in machado.tone

    def test_influence_has_exemplars(self) -> None:
        """Influences have exemplars list."""
        influences = load_influences()
        machado = next((i for i in influences if i.id == "antonio_machado"), None)
        assert machado is not None
        assert len(machado.exemplars) >= 1
        assert any("Caminante" in ex for ex in machado.exemplars)

    def test_influence_has_era(self) -> None:
        """Influences have era string."""
        influences = load_influences()
        machado = next((i for i in influences if i.id == "antonio_machado"), None)
        assert machado is not None
        assert machado.era == "1875-1939"

    def test_influence_has_movement(self) -> None:
        """Influences have movement string."""
        influences = load_influences()
        machado = next((i for i in influences if i.id == "antonio_machado"), None)
        assert machado is not None
        assert machado.movement == "Generación del 98"


class TestGetInfluenceById:
    """Tests for the get_influence_by_id lookup."""

    def test_finds_existing_influence(self) -> None:
        """Find an influence by its ID."""
        inf = get_influence_by_id("pablo_neruda")
        assert inf is not None
        assert inf.name == "Pablo Neruda"

    def test_returns_none_for_missing(self) -> None:
        """Return None for non-existent ID."""
        inf = get_influence_by_id("nonexistent_poet")
        assert inf is None


class TestGetInfluencesByLanguage:
    """Tests for filtering by language."""

    def test_filters_spanish(self) -> None:
        """Get only Spanish influences."""
        spanish = get_influences_by_language("es")
        assert len(spanish) >= 10
        assert all(i.language == "es" for i in spanish)

    def test_filters_english(self) -> None:
        """Get only English influences."""
        english = get_influences_by_language("en")
        assert len(english) >= 5
        assert all(i.language == "en" for i in english)


class TestGetInfluencesByTone:
    """Tests for filtering by tone."""

    def test_filters_melancholic(self) -> None:
        """Get influences with melancholic tone."""
        melancholic = get_influences_by_tone("melancholic")
        assert len(melancholic) >= 2
        assert all("melancholic" in [t.lower() for t in i.tone] for i in melancholic)

    def test_filters_case_insensitive(self) -> None:
        """Tone matching is case-insensitive."""
        upper = get_influences_by_tone("MELANCHOLIC")
        lower = get_influences_by_tone("melancholic")
        assert len(upper) == len(lower)

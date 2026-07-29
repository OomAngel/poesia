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


class TestGetInfluencesByMovement:
    """Tests for filtering by literary movement."""

    def test_filters_generacion_del_98(self) -> None:
        """Get influences from Generacion del 98."""
        from poesia.memoria.influence_loader import get_influences_by_movement
        results = get_influences_by_movement("Generación del 98")
        assert len(results) >= 1
        assert any(i.name == "Antonio Machado" for i in results)

    def test_filters_romanticism(self) -> None:
        """Get influences from Romanticism (matches both English and Spanish)."""
        from poesia.memoria.influence_loader import get_influences_by_movement
        results = get_influences_by_movement("Romanticism")
        assert len(results) >= 2
        assert any(i.name == "William Wordsworth" for i in results)
        assert any(i.name == "John Keats" for i in results)

    def test_case_insensitive_movement(self) -> None:
        """Movement matching is case-insensitive."""
        from poesia.memoria.influence_loader import get_influences_by_movement
        upper = get_influences_by_movement("ROMANTICISM")
        lower = get_influences_by_movement("romanticism")
        assert len(upper) == len(lower) > 0

    def test_returns_empty_for_unknown_movement(self) -> None:
        """Unknown movement returns empty list."""
        from poesia.memoria.influence_loader import get_influences_by_movement
        results = get_influences_by_movement("NonExistentMovementXYZ")
        assert len(results) == 0


class TestGetInfluencesByEra:
    """Tests for filtering by era/date range."""

    def test_filters_1900s(self) -> None:
        """Get influences active around 1900 (spanning turn of century)."""
        from poesia.memoria.influence_loader import get_influences_by_era
        results = get_influences_by_era("1890-1910")
        ids = [i.id for i in results]
        assert "antonio_machado" in ids  # 1875-1939
        assert "ruben_dario" in ids     # 1867-1916

    def test_filters_range(self) -> None:
        """Get influences active in a date range."""
        from poesia.memoria.influence_loader import get_influences_by_era
        results = get_influences_by_era("1850-1900")
        ids = [i.id for i in results]
        assert "gustavo_adolfo_becquer" in ids  # 1836-1870
        assert "manuel_acuna" in ids  # 1849-1873

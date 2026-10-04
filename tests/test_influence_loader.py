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

    def test_influence_record_shape(self) -> None:
        """A loaded influence carries language, tone, exemplars, era, movement."""
        influences = load_influences()
        machado = next((i for i in influences if i.id == "antonio_machado"), None)
        assert machado is not None
        assert machado.name == "Antonio Machado"
        assert machado.language == "es"
        assert isinstance(machado.tone, list) and "spare" in machado.tone
        assert len(machado.exemplars) >= 1 and any("Caminante" in ex for ex in machado.exemplars)
        assert machado.era == "1875-1939"
        assert machado.movement == "Generación del 98"

    def test_english_and_dutch_language_sections(self) -> None:
        """English and Dutch sections carry their language."""
        influences = load_influences()
        frost = next((i for i in influences if i.id == "robert_frost"), None)
        kloos = next((i for i in influences if i.id == "willem_kloos"), None)
        assert frost is not None and frost.language == "en"
        assert kloos is not None and kloos.language == "nl"


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
    @pytest.mark.parametrize(("lang", "min_count"), [("es", 10), ("en", 5)])
    def test_filters_by_language(self, lang: str, min_count: int) -> None:
        """Get only influences of one language."""
        results = get_influences_by_language(lang)
        assert len(results) >= min_count
        assert all(i.language == lang for i in results)


class TestGetInfluencesByTone:
    def test_filters_by_tone_case_insensitive(self) -> None:
        """Tone matching filters and is case-insensitive."""
        melancholic = get_influences_by_tone("melancholic")
        assert len(melancholic) >= 2
        assert all("melancholic" in [t.lower() for t in i.tone] for i in melancholic)
        upper = get_influences_by_tone("MELANCHOLIC")
        assert len(upper) == len(melancholic)


class TestGetInfluencesByMovement:
    def test_filters_by_movement(self) -> None:
        """Movement filtering matches known movements (case-insensitive)."""
        from poesia.memoria.influence_loader import get_influences_by_movement

        generacion_98 = get_influences_by_movement("Generación del 98")
        assert len(generacion_98) >= 1
        assert any(i.name == "Antonio Machado" for i in generacion_98)

        romanticism = get_influences_by_movement("Romanticism")
        assert len(romanticism) >= 2
        assert any(i.name == "William Wordsworth" for i in romanticism)
        assert any(i.name == "John Keats" for i in romanticism)
        assert len(get_influences_by_movement("ROMANTICISM")) == len(romanticism)

    def test_unknown_movement_returns_empty(self) -> None:
        """Unknown movement returns empty list."""
        from poesia.memoria.influence_loader import get_influences_by_movement

        assert get_influences_by_movement("NonExistentMovementXYZ") == []


class TestGetInfluencesByEra:
    def test_filters_by_era_range(self) -> None:
        """Era filtering spans the turn of the century."""
        from poesia.memoria.influence_loader import get_influences_by_era

        around_1900 = get_influences_by_era("1890-1910")
        ids_1900 = {i.id for i in around_1900}
        assert "antonio_machado" in ids_1900  # 1875-1939
        assert "ruben_dario" in ids_1900  # 1867-1916

        earlier = get_influences_by_era("1850-1900")
        ids_earlier = {i.id for i in earlier}
        assert "gustavo_adolfo_becquer" in ids_earlier  # 1836-1870
        assert "manuel_acuna" in ids_earlier  # 1849-1873


class TestAddInfluence:
    """add_influence writes into data/influences.yaml without disturbing existing text."""

    @staticmethod
    def _copy(tmp_path):
        import shutil
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "data" / "influences.yaml"
        dst = tmp_path / "influences.yaml"
        shutil.copy(src, dst)
        return dst

    def test_appends_into_the_language_section_and_loads_back(self, tmp_path) -> None:
        from poesia.memoria.influence_loader import add_influence, clear_cache, load_influences
        from poesia.memoria.records import InfluenceRecord

        path = self._copy(tmp_path)
        add_influence(
            InfluenceRecord(
                id="mary_oliver", name="Mary Oliver", language="en", tone=["attentive", "wild"]
            ),
            yaml_path=path,
        )
        clear_cache()
        loaded = {i.id: i for i in load_influences(path)}
        assert loaded["mary_oliver"].language == "en"
        assert loaded["mary_oliver"].tone == ["attentive", "wild"]
        assert len(loaded) == 25

    def test_existing_lines_are_kept_in_order(self, tmp_path) -> None:
        from poesia.memoria.influence_loader import add_influence
        from poesia.memoria.records import InfluenceRecord

        path = self._copy(tmp_path)
        before = path.read_text(encoding="utf-8").splitlines()
        add_influence(
            InfluenceRecord(id="x_poet", name="X Poet", language="es", tone=["calm"]),
            yaml_path=path,
        )
        after = iter(path.read_text(encoding="utf-8").splitlines())
        assert all(line in after for line in before)  # every original line, same order

    def test_duplicate_and_unknown_language_are_refused(self, tmp_path) -> None:
        from poesia.memoria.influence_loader import add_influence
        from poesia.memoria.records import InfluenceRecord

        path = self._copy(tmp_path)
        with pytest.raises(ValueError, match="already exists"):
            add_influence(
                InfluenceRecord(id="antonio_machado", name="Antonio Machado", language="es"),
                yaml_path=path,
            )
        with pytest.raises(ValueError, match="unknown language"):
            add_influence(
                InfluenceRecord(id="li_bai", name="Li Bai", language="zh"), yaml_path=path
            )

"""Tests for GalerIA style anchoring: influences, retrieval, and merge.

The influence parsing and auto-embed behaviors live in their own test files
(test_influence_loader.py, test_memoria_graphrag.py); this file keeps the
style-derivation logic that is unique to GalerIA.
"""

from __future__ import annotations

from poesia.memoria.records import InfluenceRecord


class TestStyleAnchoring:
    """Tests for GalerIA style anchoring from influences (Phase 4C)."""

    def test_style_from_influences_returns_keywords(self) -> None:
        """style_from_influences should return visual keywords."""
        from poesia.galeria.style_anchoring import style_from_influences

        influences = [
            InfluenceRecord(
                id="machado",
                name="Antonio Machado",
                language="es",
                movement="Generación del 98",
                tone=["meditative", "austere"],
            )
        ]
        style = style_from_influences(influences)
        assert style  # Non-empty

    def test_style_from_influences_handles_empty(self) -> None:
        """style_from_influences should handle empty list."""
        from poesia.galeria.style_anchoring import style_from_influences

        assert style_from_influences([]) == ""


class TestStyleFromRetrieval:
    """GalerIA style anchoring from retrieval (--style-from-retrieval)."""

    def test_derives_sensory_and_noun_keywords(self) -> None:
        """style_from_retrieval should map imagery + senses to visual keywords."""
        from poesia.galeria.style_anchoring import style_from_retrieval

        style = style_from_retrieval(
            ["La luna brilla sobre el agua fría.\nLa noche callada escucha el viento."],
            language="es",
        )
        assert style
        keywords = style.split(", ")
        assert any(k in keywords for k in ("luna", "agua", "noche", "viento"))

    def test_handles_empty_and_appends_theme_and_max(self) -> None:
        """Empty input returns empty; theme is appended; keyword cap respected."""
        from poesia.galeria.style_anchoring import style_from_retrieval

        assert style_from_retrieval([]) == ""
        style = style_from_retrieval(["agua"], language="es", theme="luna")
        assert "luna" in style.split(", ")

        texts = ["La luna y el sol brillan. El agua y el viento. La noche y el día."] * 3
        capped = style_from_retrieval(texts, language="es", max_keywords=3)
        assert len(capped.split(", ")) <= 3


class TestDeriveStyleMerge:
    """derive_style merges influence + retrieval + base styles."""

    def test_merges_all_three(self) -> None:
        from poesia.galeria.pipeline import derive_style

        inf = InfluenceRecord(
            id="machado",
            name="Antonio Machado",
            language="es",
            movement="Generación del 98",
            tone=["meditative"],
        )
        merged = derive_style("base", [inf], "retrieved keywords")
        assert merged
        assert "austere landscape" in merged
        assert "retrieved keywords" in merged
        assert merged.endswith("base")

    def test_base_only_and_all_empty(self) -> None:
        from poesia.galeria.pipeline import derive_style

        assert derive_style("base") == "base"
        assert derive_style(None) is None

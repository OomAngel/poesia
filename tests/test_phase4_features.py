"""Tests for Phase 4 features: Real LLM, richer influences, style anchoring, auto-embed."""

import pytest

from poesia.memoria.records import InfluenceRecord


class TestInfluenceParser:
    """Tests for richer influence profile parsing (Phase 4B)."""

    def test_load_influences_parses_movement(self) -> None:
        """Influence parser should extract movement from registry."""
        from poesia.cli import _load_influences
        influences = _load_influences()
        machado = next((i for i in influences if "Machado" in i.name), None)
        assert machado is not None
        assert machado.movement == "Generación del 98"

    def test_load_influences_parses_era(self) -> None:
        """Influence parser should extract era (years) from registry."""
        from poesia.cli import _load_influences
        influences = _load_influences()
        machado = next((i for i in influences if "Machado" in i.name), None)
        assert machado is not None
        assert machado.era == "1875-1939"

    def test_load_influences_parses_tone(self) -> None:
        """Influence parser should extract tone list from registry."""
        from poesia.cli import _load_influences
        influences = _load_influences()
        machado = next((i for i in influences if "Machado" in i.name), None)
        assert "meditative" in machado.tone

    def test_load_influences_detects_language(self) -> None:
        """Influence parser should set language based on section headers."""
        from poesia.cli import _load_influences
        influences = _load_influences()
        keats = next((i for i in influences if "Keats" in i.name), None)
        assert keats is not None
        assert keats.language == "en"
        kloos = next((i for i in influences if "Kloos" in i.name), None)
        assert kloos is not None
        assert kloos.language == "nl"


class TestStyleAnchoring:
    """Tests for GalerIA style anchoring from influences (Phase 4C)."""

    def test_style_from_influences_returns_keywords(self) -> None:
        """style_from_influences should return visual keywords."""
        from poesia.galeria.style_anchoring import style_from_influences
        influences = [
            InfluenceRecord(
                id="machado", name="Antonio Machado", language="es",
                movement="Generación del 98", tone=["meditative", "austere"],
            )
        ]
        style = style_from_influences(influences)
        assert style  # Non-empty

    def test_style_from_influences_handles_empty(self) -> None:
        """style_from_influences should handle empty list."""
        from poesia.galeria.style_anchoring import style_from_influences
        assert style_from_influences([]) == ""


class TestAutoEmbed:
    """Tests for auto-embed on ingest (Phase 4D)."""

    def test_ingest_auto_embeds_when_client_provided(self) -> None:
        """GraphRAGRetriever.ingest should auto-embed when client provided."""
        from poesia.memoria.embeddings import StubEmbeddingClient
        from poesia.memoria.graphrag import GraphRAGRetriever
        from poesia.memoria.library import PoemRecord

        retriever = GraphRAGRetriever(storage_path=":memory:")
        records = [PoemRecord(id="test1", theme="moonlight", form="haiku", language="en", lines=["test"])]
        retriever.ingest(records, embedding_client=StubEmbeddingClient())
        node_data = dict(retriever._graph.nodes(data=True))
        assert node_data["test1"].get("embedding")

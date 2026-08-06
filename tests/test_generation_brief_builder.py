"""Tests for BriefBuilder and GenerationBrief."""

from __future__ import annotations

from poesia.forms.definitions import SONETO_ES
from poesia.generation.brief_builder import BriefBuilder, GenerationBrief
from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.records import FragmentRecord, InfluenceRecord


def test_generation_brief_creation_and_prompt() -> None:
    brief = GenerationBrief(
        form_spec=SONETO_ES,
        theme="departure",
        tone=["melancholic", "tender"],
    )
    assert brief.form_spec.name == "soneto"
    assert brief.theme == "departure"
    assert "melancholic" in brief.tone

    prompt = brief.to_prompt()
    assert "soneto" in prompt.lower()
    assert "FORM" in prompt and "11" in prompt  # syllables per line
    assert "departure" in prompt and "THEME" in prompt



def test_brief_builder_creation() -> None:
    builder = BriefBuilder()
    assert builder._fragments == []
    assert builder._influences == []


def test_brief_builder_build_minimal() -> None:
    builder = BriefBuilder()
    brief = builder.build(
        form="soneto",
        theme="silence",
        level="minimal",
    )

    assert brief.form_spec.name == "soneto"
    assert brief.theme == "silence"
    assert brief.level == "minimal"


def test_brief_builder_with_tone() -> None:
    builder = BriefBuilder()
    brief = builder.build(
        form="soneto",
        theme="departure",
        tone=["melancholic", "tender"],
    )

    assert "melancholic" in brief.tone
    assert "tender" in brief.tone


def test_brief_builder_with_seeds() -> None:
    builder = BriefBuilder()
    brief = builder.build(
        form="soneto",
        theme="silence",
        seeds=["silencio", "partir"],
    )

    assert "silencio" in brief.seeds_expanded
    assert "partir" in brief.seeds_expanded


def test_brief_builder_with_fragments() -> None:
    frag1 = FragmentRecord(
        id="frag-1",
        content="El silencio pesa más que las palabras.",
        language="es",
    )
    frag2 = FragmentRecord(
        id="frag-2",
        content="La alegría del amanecer.",
        language="es",
    )

    client = StubEmbeddingClient()
    builder = BriefBuilder(embedding_client=client, fragments=[frag1, frag2])

    brief = builder.build(form="soneto", theme="silence")

    # Should retrieve fragments (with stub, order is deterministic by hash)
    assert len(brief.fragments) > 0


def test_brief_builder_with_influences() -> None:
    machado = InfluenceRecord(
        id="machado",
        name="Antonio Machado",
        language="es",
        tone=["spare", "meditative", "honest"],
    )
    neruda = InfluenceRecord(
        id="neruda",
        name="Pablo Neruda",
        language="es",
        tone=["sensual", "expansive"],
    )

    builder = BriefBuilder(influences=[machado, neruda])
    brief = builder.build(
        form="soneto",
        theme="departure",
        tone=["meditative"],  # Should match Machado
    )

    assert len(brief.influences) > 0
    # Machado should be matched due to "meditative"
    matched_names = [inf.name for inf in brief.influences]
    assert "Antonio Machado" in matched_names


def test_brief_builder_add_fragments() -> None:
    builder = BriefBuilder()
    assert len(builder._fragments) == 0

    frag = FragmentRecord(id="test", content="Test content", language="es")
    builder.add_fragments([frag])

    assert len(builder._fragments) == 1


def test_brief_to_prompt_full() -> None:
    """Test a fuller brief renders correctly."""
    frag = FragmentRecord(
        id="station-departure",
        content="En la estación, vi partir el tren.",
        language="es",
        tone=["melancholic"],
    )
    machado = InfluenceRecord(
        id="machado",
        name="Antonio Machado",
        language="es",
        tone=["spare", "meditative"],
    )

    client = StubEmbeddingClient()
    builder = BriefBuilder(
        embedding_client=client,
        fragments=[frag],
        influences=[machado],
    )

    brief = builder.build(
        form="soneto",
        theme="departure",
        tone=["meditative"],
        seeds=["silencio"],
        level="maximal",
    )

    prompt = brief.to_prompt()

    # Should contain all sections
    assert "FORM" in prompt
    assert "THEME" in prompt
    assert "departure" in prompt
    assert "silencio" in prompt or "SEEDS" in prompt
    # Maximal level should include influences
    assert "INFLUENCES" in prompt or "Machado" in prompt

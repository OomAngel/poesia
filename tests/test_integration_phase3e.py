"""Integration tests for Phase 3E: BriefBuilder wired into generation loop."""

from __future__ import annotations

import pytest

from poesia.generation.brief_builder import BriefBuilder
from poesia.generation.candidate_generator import CandidateGenerator
from poesia.generation.constrained_loop import ConstrainedLoop
from poesia.generation.llm_client import StubLLMClient
from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.records import FragmentRecord, InfluenceRecord


@pytest.fixture
def stub_llm() -> StubLLMClient:
    return StubLLMClient()


@pytest.fixture
def stub_embedding_client() -> StubEmbeddingClient:
    return StubEmbeddingClient()


@pytest.fixture
def sample_fragments() -> list[FragmentRecord]:
    return [
        FragmentRecord(id="frag_1", content="Rain on ancient stones", language="en", tags=["nature"]),
        FragmentRecord(id="frag_2", content="Building from nothing", language="en", tags=["creation"]),
    ]


@pytest.fixture
def sample_influences() -> list[InfluenceRecord]:
    return [
        InfluenceRecord(id="vallejo", name="César Vallejo", language="es", tone=["anguished"]),
        InfluenceRecord(id="dickinson", name="Emily Dickinson", language="en", tone=["intimate"]),
    ]


@pytest.fixture
def brief_builder(stub_embedding_client, sample_fragments, sample_influences) -> BriefBuilder:
    return BriefBuilder(
        embedding_client=stub_embedding_client,
        fragments=sample_fragments,
        influences=sample_influences,
    )


class TestCandidateGeneratorWithBrief:
    """Tests for CandidateGenerator accepting GenerationBrief."""

    def test_generate_with_brief(self, stub_llm, brief_builder) -> None:
        """When a brief is provided, the generator should use its prompt."""
        generator = CandidateGenerator(stub_llm)
        brief = brief_builder.build(form="romance", theme="lluvia", tone=["intimate"])
        candidates = generator.generate_lines(theme="lluvia", language="es", n_candidates=4, brief=brief)
        assert len(candidates) == 4

    def test_generate_without_brief(self, stub_llm) -> None:
        """Without a brief, falls back to legacy simple prompt."""
        generator = CandidateGenerator(stub_llm)
        candidates = generator.generate_lines(theme="lluvia", language="es", n_candidates=4, brief=None)
        assert len(candidates) == 4


class TestConstrainedLoopWithBrief:
    """Tests for ConstrainedLoop with BriefBuilder integration."""

    def test_loop_builds_brief_when_builder_provided(self, stub_llm, brief_builder) -> None:
        """Loop should build and use a brief when builder is provided."""
        loop = ConstrainedLoop(language="es", form="romance", llm=stub_llm, brief_builder=brief_builder)
        result = loop.run(theme="lluvia de otoño", tone=["intimate"], seeds=["lluvia"], brief_level="standard")
        assert result.brief is not None
        assert result.brief.theme == "lluvia de otoño"
        assert result.brief.tone == ["intimate"]

    def test_loop_works_without_brief_builder(self, stub_llm) -> None:
        """Loop should work fine without any brief builder (legacy mode)."""
        # Just verify we can construct the loop without a builder
        # (Full phonology requires rantanplan/pronouncing libraries)
        loop = ConstrainedLoop(language="es", form="soneto", llm=stub_llm)
        assert loop._brief_builder is None
        assert loop.form_spec.name == "soneto"
        assert loop.form_spec.total_lines == 14

    def test_loop_result_includes_brief(self, stub_llm, brief_builder) -> None:
        """LoopResult should include the brief for inspection."""
        loop = ConstrainedLoop(language="es", form="romance", llm=stub_llm, brief_builder=brief_builder)
        result = loop.run(theme="lluvia", tone=["anguished"])
        assert result.brief is not None
        assert result.brief.form_spec.name == "romance"


class TestEndToEndBriefFlow:
    """End-to-end tests for the complete brief → generation flow."""

    def test_brief_to_prompt_renders_all_sections(self, brief_builder) -> None:
        """Brief.to_prompt() should render all relevant sections."""
        brief = brief_builder.build(form="soneto", theme="el tiempo", tone=["intimate"], level="maximal")
        prompt = brief.to_prompt()
        assert "## FORM" in prompt
        assert "## THEME" in prompt
        assert "el tiempo" in prompt

    def test_minimal_brief_is_shorter(self, brief_builder) -> None:
        """Minimal brief should produce a shorter prompt when influences exist."""
        # Build with tone to trigger influence matching (vallejo has "anguished" tone)
        brief_min = brief_builder.build(form="soneto", theme="otoño", tone=["anguished"], level="minimal")
        brief_max = brief_builder.build(form="soneto", theme="otoño", tone=["anguished"], level="maximal")
        # Maximal includes INFLUENCES section, minimal does not
        prompt_min = brief_min.to_prompt()
        prompt_max = brief_max.to_prompt()
        assert "## INFLUENCES" not in prompt_min
        assert "## INFLUENCES" in prompt_max
        assert len(prompt_min) < len(prompt_max)

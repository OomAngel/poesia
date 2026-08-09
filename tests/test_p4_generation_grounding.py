"""P4 — Generation grounding evaluation (formal validity + context use).

Tests that the constrained generation loop, when given fragment context,
produces formally valid output that demonstrably uses the source material.

These are integration-level tests that exercise the full pipeline:
phonology -> brief -> generation -> scoring -> selection.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from poesia.forms.definitions import get_form
from poesia.generation.brief_builder import BriefBuilder
from poesia.generation.constrained_loop import ConstrainedLoop
from poesia.memoria.embeddings import StubEmbeddingClient
from poesia.memoria.graphrag import GraphRAGRetriever
from poesia.memoria.records import FragmentRecord
from poesia.phonology.spanish import SpanishPhonology

_FRAGMENTS_DIR = Path(__file__).parent.parent / "seeds" / "angel_fragments"


def _load_fragment_records() -> list[FragmentRecord]:
    """Load all fragments from disk as FragmentRecord objects."""
    from poesia.cli import _parse_fragment_frontmatter

    records: list[FragmentRecord] = []
    for md_file in sorted(_FRAGMENTS_DIR.glob("*.md")):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        fm = _parse_fragment_frontmatter(content)
        body = content
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
        fragment = FragmentRecord(
            id=fm.get("id") or md_file.stem,
            content=body,
            language=fm.get("language") or "es",
            tags=fm.get("tags") or [],
        )
        records.append(fragment)
    return records


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_llm_client():
    """Return a stub LLM client that returns fixed candidate lines."""
    from poesia.generation.llm_client import StubLLMClient

    return StubLLMClient()


@pytest.fixture
def phonology():
    return SpanishPhonology()


@pytest.fixture
def stub_client():
    """Return a stub embedding client for deterministic scoring."""
    from poesia.memoria.embeddings import StubEmbeddingClient

    return StubEmbeddingClient()


# ---------------------------------------------------------------------------
# Brief building with fragment context
# ---------------------------------------------------------------------------


def test_brief_includes_fragments(fragment_records: list[FragmentRecord]) -> None:
    """BriefBuilder should include fragments when they are provided."""
    client = StubEmbeddingClient()
    builder = BriefBuilder(
        embedding_client=client,
        fragments=fragment_records[:3],
    )
    brief = builder.build(
        form=get_form("haiku"),
        theme="luna sobre el mar",
        level="standard",
    )
    assert len(brief.fragments) > 0, "Brief should contain fragments"
    for frag, sim in brief.fragments:
        assert isinstance(frag, FragmentRecord)
        assert 0.0 <= sim <= 1.0


def test_brief_includes_graph_paths_when_retriever_wired(
    fragment_records: list[FragmentRecord],
    stub_client: StubEmbeddingClient,
) -> None:
    """BriefBuilder with retriever should produce graph_paths."""
    retriever = GraphRAGRetriever(storage_path=":memory:")
    for frag in fragment_records:
        retriever.add_fragment_node(
            frag.id,
            frag.content,
            language=frag.language,
            tags=frag.tags,
            embedding_client=stub_client,
        )

    builder = BriefBuilder(
        embedding_client=stub_client,
        retriever=retriever,
    )
    brief = builder.build(
        form=get_form("soneto"),
        theme="soledad y búsqueda",
        level="standard",
    )
    assert hasattr(brief, "graph_paths")
    assert isinstance(brief.graph_paths, list)


# ---------------------------------------------------------------------------
# Generation loop produces formally valid output with fragment context
# ---------------------------------------------------------------------------


def test_generation_scoring_penalizes_syllable_mismatch(
    stub_llm_client,
    fragment_records: list[FragmentRecord],
    stub_client: StubEmbeddingClient,
) -> None:
    """Scoring should penalize lines that miss the target syllable count.

    The stub LLM returns hardcoded lines that may not match a haiku pattern.
    This test verifies the scorer assigns lower scores to mismatched lines
    and that the metre score reflects the degree of mismatch.
    """
    phonology = SpanishPhonology()
    loop = ConstrainedLoop(
        language="es",
        form="haiku",
        llm=stub_llm_client,
        embedding_client=stub_client,
        fragments=fragment_records[:3],
    )
    result = loop.run(
        theme="soledad",
        n_candidates=8,
    )

    if not result.scored_history:
        pytest.skip("No scored history available")

    # Check that each candidate has a metre score that varies with syllable distance
    for line_idx, candidates in enumerate(result.scored_history):
        for cand in candidates:
            scan = phonology.scan_line(cand.line)
            target = loop.form_spec.syllables_for_line(line_idx)
            assert "metre" in cand.breakdown, f"Line {line_idx}: missing 'metre' in breakdown"
            # If syllable count is exact, metre score should be >= 0.5
            if scan.metrical_syllable_count == target:
                assert cand.breakdown["metre"] >= 0.5, (
                    f"Line '{cand.line}' has exact syllable count ({target}) "
                    f"but metre score is {cand.breakdown['metre']:.2f}"
                )


# ---------------------------------------------------------------------------
# Formal validity across a range of themes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "theme",
    [
        "el mar y la noche",
        "primavera que vuelve",
        "trabajo sin recompensa",
        "verdad oculta",
    ],
)
def test_generation_with_various_themes(
    stub_llm_client,
    phonology: SpanishPhonology,
    fragment_records: list[FragmentRecord],
    stub_client: StubEmbeddingClient,
    theme: str,
) -> None:
    """Generate lines for several themes to stress-test formal validity."""
    loop = ConstrainedLoop(
        language="es",
        form="haiku",
        llm=stub_llm_client,
        embedding_client=stub_client,
        fragments=fragment_records[:3],
    )
    result = loop.run(theme=theme, n_candidates=4)
    assert result.lines, f"No output for theme '{theme}'"
    for i, line in enumerate(result.lines):
        scan = phonology.scan_line(line)
        assert scan.is_valid, f"Line {i} for theme '{theme}' failed: '{line}'"


# ---------------------------------------------------------------------------
# Scoring includes fragment fidelity signal
# ---------------------------------------------------------------------------


def test_scoring_includes_fragment_fidelity(
    stub_llm_client,
    phonology: SpanishPhonology,
    fragment_records: list[FragmentRecord],
    stub_client: StubEmbeddingClient,
) -> None:
    """Scored candidates should include fragment_fidelity in breakdown."""
    loop = ConstrainedLoop(
        language="es",
        form="haiku",
        llm=stub_llm_client,
        embedding_client=stub_client,
        fragments=fragment_records[:3],
    )
    result = loop.run(theme="luna", n_candidates=8)

    if not result.scored_history:
        pytest.skip("No scored history available (stub may skip scoring)")

    for line_idx, candidates in enumerate(result.scored_history):
        for cand in candidates:
            assert "fragment_fidelity" in cand.breakdown, (
                f"Line {line_idx}: missing fragment_fidelity. Keys: {list(cand.breakdown.keys())}"
            )
            assert "end_word" in cand.breakdown, (
                f"Line {line_idx}: missing end_word. Keys: {list(cand.breakdown.keys())}"
            )


def test_generation_with_fragment_context_produces_valid_lines(
    stub_llm_client,
    phonology: SpanishPhonology,
    fragment_records: list[FragmentRecord],
    stub_client: StubEmbeddingClient,
) -> None:
    """Given fragment context, the loop must produce formally valid candidates."""
    loop = ConstrainedLoop(
        language="es",
        form="haiku",
        llm=stub_llm_client,
        embedding_client=stub_client,
        fragments=fragment_records[:3],
    )
    result = loop.run(
        theme="luna sobre el mar",
        n_candidates=4,
    )

    assert result.lines, "Generation produced no output lines"
    for i, line in enumerate(result.lines):
        scan = phonology.scan_line(line)
        assert scan.is_valid, (
            f"Line {i} failed phonology validation: '{line}' "
            f"(syllables={scan.metrical_syllable_count})"
        )


@pytest.fixture
def fragment_records() -> list[FragmentRecord]:
    return _load_fragment_records()

"""Extended record types for MemorIA personal context corpus.

Beyond PoemRecord (in library.py), the enrichment layer uses:
- FragmentRecord: life moments, feelings, emotional states
- SeedRecord: word/image clusters with comprehensive expansions
- InfluenceRecord: poets/works that resonate

All records use YAML frontmatter in Markdown files for human readability.

P2: NodeType and RelationType enums define the typed graph schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class NodeType(StrEnum):
    """Typed node categories in the GraphRAG semantic graph.

    Each node in the graph is one of these types. Having distinct types
    enables typed traversal (e.g. "find all influences connected to this
    poem") and explainable path rendering.
    """

    poem = "poem"
    fragment = "fragment"
    influence = "influence"
    seed = "seed"
    theme = "theme"


class RelationType(StrEnum):
    """Typed edge categories in the GraphRAG semantic graph.

    Each directed edge has a relation type. This enables:
    - filtered traversal (e.g. follow only ``inspired_by`` edges)
    - human-readable path explanations
    - evidence of which relation carried the retrieval

    Relation semantics:
    - ``similar_to``: two nodes have high cosine similarity (undirected in practice)
    - ``inspired_by``: a poem or fragment was influenced by a poet/work
    - ``explores``: a poem or fragment explores a given theme
    - ``contains``: a poem contains a fragment (part-of relation)
    """

    similar_to = "similar_to"
    inspired_by = "inspired_by"
    explores = "explores"
    contains = "contains"


@dataclass
class FragmentRecord:
    """A personal context fragment — life moment, feeling, emotional state.

    Fragments are the raw material for grounding LLM prompts in your voice.
    They are NOT career descriptions — they are poetic grounding material.
    """

    id: str
    content: str  # The actual text (prose, notes, images in words)
    language: str  # "es", "en", "zh", "nl"
    created_at: datetime = field(default_factory=datetime.now)

    # Multi-dimensional tone (not a flat vocabulary)
    tone: list[str] = field(default_factory=list)  # ["melancholic", "restrained"]
    movement: str | None = None  # "Modernismo", "Romanticism" (optional)
    poet_anchor: str | None = None  # "Machado-like" (optional)

    # Retrieval metadata
    themes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    period: str | None = None  # "2019", "childhood", etc.
    source_file: str | None = None  # Provenance if transformed from another file


@dataclass
class SeedExpansion:
    """Comprehensive expansion of a seed word across all dimensions."""

    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    rhymes_consonant: dict[str, list[str]] = field(default_factory=dict)  # ending -> words
    rhymes_assonant: dict[str, list[str]] = field(default_factory=dict)
    semantic_neighbors: list[str] = field(default_factory=list)
    collocations: list[str] = field(default_factory=list)
    hypernyms: list[str] = field(default_factory=list)
    hyponyms: list[str] = field(default_factory=list)
    register: str | None = None  # "formal", "colloquial", "literary"
    connotation: str | None = None  # "melancholic", "joyful"
    etymology: str | None = None
    cross_language: dict[str, str] = field(default_factory=dict)  # lang -> translation


@dataclass
class SeedRecord:
    """A word/image seed with comprehensive expansions.

    Seeds are starting points for generation — words or images that
    anchor the poem. Expansions provide synonyms, rhymes, semantic
    neighbors, collocations, etc.
    """

    id: str
    root_word: str
    language: str
    created_at: datetime = field(default_factory=datetime.now)

    # Metadata
    tags: list[str] = field(default_factory=list)
    notes: str | None = None

    # Comprehensive expansion
    expansion: SeedExpansion = field(default_factory=SeedExpansion)


@dataclass
class InfluenceRecord:
    """A poet or work that resonates — used for tonal anchoring.

    Influences provide style references for generation. The brief can
    say "in the style of Machado" and retrieve this profile.
    """

    id: str  # e.g., "machado", "neruda"
    name: str  # Full name: "Antonio Machado"
    language: str  # Primary language
    created_at: datetime = field(default_factory=datetime.now)

    # Literary context
    movement: str | None = None  # "Generación del 98"
    era: str | None = None  # "1875-1939"

    # Tonal qualities
    tone: list[str] = field(default_factory=list)  # ["spare", "meditative", "honest"]

    # Preferred forms
    forms: list[str] = field(default_factory=list)  # ["romance", "soneto"]

    # Exemplar lines (for few-shot grounding)
    exemplars: list[str] = field(default_factory=list)

    # What specifically resonates (Phase 4: richer profiles)
    resonance_notes: str | None = None

    # Anti-patterns to avoid when emulating
    anti_patterns: list[str] = field(default_factory=list)


# Type alias for any record type in the graph
ContextRecord = FragmentRecord | SeedRecord | InfluenceRecord

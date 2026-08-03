"""MemorIA — collections, Graph RAG retrieval, and personal context corpus.

*Memoria* (memory). The personal knowledge layer for PoesIA:

- **Library**: Markdown poem storage with SQLite index (`library.py`)
- **GraphRAGRetriever**: NetworkX-backed semantic retrieval (`graphrag.py`)
- **EmbeddingClient**: Protocol + implementations for embeddings (`embeddings.py`)
- **Record types**: Fragment, Seed, Influence records (`records.py`)
- **Influence loader**: YAML-based influence loading (`influence_loader.py`)

The Graph RAG layer uses semantic embeddings to retrieve personal context
(fragments, seeds, influences) for grounding LLM generation prompts.
"""

from poesia.memoria.influence_loader import (
    get_influence_by_id,
    get_influences_by_era,
    get_influences_by_language,
    get_influences_by_movement,
    get_influences_by_tone,
    load_influences,
)
from poesia.memoria.library import Library, PoemRecord
from poesia.memoria.records import (
    FragmentRecord,
    InfluenceRecord,
    SeedExpansion,
    SeedRecord,
)

__all__ = [
    "Library",
    "PoemRecord",
    "FragmentRecord",
    "SeedRecord",
    "SeedExpansion",
    "InfluenceRecord",
    "load_influences",
    "get_influence_by_id",
    "get_influences_by_era",
    "get_influences_by_language",
    "get_influences_by_movement",
    "get_influences_by_tone",
]

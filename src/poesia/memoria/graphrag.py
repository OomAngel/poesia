"""Graph RAG retrieval layer — Phase 3, not yet implemented.

Intended scope once built:
    - Corpus ingestion: poems tagged by poet, period, form, theme (promoted
      from `library.py`'s flat PoemRecord storage).
    - Graph construction: poet nodes, influence edges, thematic/semantic
      neighborhood edges (via sentence-transformers embeddings).
    - Retrieval: given a theme/style anchor, pull grounding excerpts to
      condition LLM generation (few-shot exemplars) without copying verbatim.
    - KenLM stylistic prior: cheap n-gram scoring of candidate lines against
      a poet- or period-specific corpus, layered on top of graph retrieval.

Storage backend decision (networkx in-memory graph vs. neo4j) is deliberately
deferred — see docs/PACKAGES_SURVEYED.md for the tradeoff notes. Do not
import from this module until that decision has landed.
"""

from __future__ import annotations


class GraphRAGRetriever:
    """Placeholder for the Phase 3 Graph RAG retrieval interface.

    Not implemented. Exists so the intended public surface (`retrieve`,
    `ingest`) is visible to readers of the codebase before the real work
    begins, per the project's "plan proactively, build incrementally" norm.
    """

    def ingest(self, records) -> None:  # noqa: ANN001 - Phase 3 type TBD
        raise NotImplementedError("Graph RAG ingestion is Phase 3 work.")

    def retrieve(self, theme: str, k: int = 5):  # noqa: ANN201 - Phase 3 type TBD
        raise NotImplementedError("Graph RAG retrieval is Phase 3 work.")

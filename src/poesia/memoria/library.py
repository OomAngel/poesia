"""Phase 0-1: a flat personal poem library (no graph, no retrieval yet).

Stores completed poems with minimal metadata so they can be listed, searched
by naive substring/tag match, and later fed into the Phase 3 Graph RAG corpus
without a data migration — the `PoemRecord` shape is intentionally the same
shape a graph node would eventually wrap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PoemRecord:
    """A single saved poem with the metadata needed for later retrieval."""

    lines: list[str]
    language: str
    form: str
    theme: str
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)


class Library:
    """In-memory (Phase 0) personal poem collection.

    Phase 1+: persist to disk (JSON/SQLite); Phase 3: promote to a graph
    store for Graph RAG retrieval. The public interface below is designed to
    stay stable across that migration.
    """

    def __init__(self) -> None:
        self._records: list[PoemRecord] = []

    def add(self, record: PoemRecord) -> None:
        """Add a completed poem to the library."""
        self._records.append(record)

    def list_all(self) -> list[PoemRecord]:
        """Return all saved poems, most recent first."""
        return sorted(self._records, key=lambda r: r.created_at, reverse=True)

    def search(self, query: str) -> list[PoemRecord]:
        """Naive substring search across theme, tags and line text.

        Phase 3 upgrade path: replace with semantic search over
        sentence-transformers embeddings once the Graph RAG layer lands.
        """
        q = query.lower()
        return [
            r
            for r in self._records
            if q in r.theme.lower()
            or any(q in tag.lower() for tag in r.tags)
            or any(q in line.lower() for line in r.lines)
        ]

"""Phase 1: human-readable Markdown poem library with SQLite background index.

Stores completed poems as plain text Markdown files with YAML frontmatter in
`~/.poesia/poems/` (or a custom path) alongside an SQLite index (`library.db`)
for fast search.
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class PoemProvenance:
    """Provenance metadata for reproducibility and lineage tracking (P1/P5 hardening).

    P5 additions:
    - ``provider``: the LLM provider name (groq, gemini, openai, stub)
    - ``n_candidates``: number of candidates requested per line
    - ``temperature``: generation temperature (if available)
    - ``latency_ms``: approximate generation time in milliseconds
    - ``token_count``: approximate token count (if reported by provider)
    """

    model: str | None = None  # LLM model used (e.g., "gemini-1.5-flash")
    embedding_model: str | None = None  # Embedding model (e.g., "multilingual-e5-small")
    provider: str | None = None  # P5: provider name (groq, gemini, openai, stub)
    brief_level: str | None = None  # "minimal", "standard", or "maximal"
    seeds: list[str] = field(default_factory=list)  # Seed words used
    tone: list[str] = field(default_factory=list)  # Tone descriptors
    fragments_used: list[str] = field(default_factory=list)  # IDs of context fragments
    influences_used: list[str] = field(default_factory=list)  # IDs of influences matched
    n_candidates: int | None = None  # P5: candidates requested per line
    temperature: float | None = None  # P5: generation temperature
    latency_ms: int | None = None  # P5: approximate generation time
    total_tokens: int | None = None  # P5: total tokens used (from provider)


@dataclass
class PoemRecord:
    """A single saved poem with the metadata needed for later retrieval."""

    lines: list[str]
    language: str
    form: str
    theme: str
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    id: str | None = None
    provenance: PoemProvenance | None = None  # P1: generation provenance


class Library:
    """Markdown + SQLite personal poem collection.

    Saves poems as .md files with YAML frontmatter for 100% human readability
    and indexes them into SQLite for fast querying by form, tag, theme, or text.
    """

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        if storage_dir is None:
            storage_dir = Path.home() / ".poesia" / "poems"
        elif str(storage_dir) != ":memory:":
            storage_dir = Path(storage_dir)

        self.storage_dir = storage_dir
        self.is_memory = str(storage_dir) == ":memory:"

        if not self.is_memory:
            os.makedirs(self.storage_dir, exist_ok=True)
            db_path = str(self.storage_dir / "library.db")
        else:
            db_path = ":memory:"

        self._conn = sqlite3.connect(db_path)
        self._init_db()
        if not self.is_memory:
            self._sync_md_files()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS poems (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    language TEXT NOT NULL,
                    form TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )

    def add(self, record: PoemRecord) -> None:
        """Add a completed poem to the library, saving to disk and SQLite."""
        if not record.id:
            timestamp = record.created_at.strftime("%Y%m%d_%H%M%S_%f")
            sanitized = re.sub(r"[^\w\-]", "_", record.theme.lower())[:30].strip("_")
            record.id = f"{timestamp}_{sanitized}"

        filename = f"{record.id}.md"
        tags_str = ", ".join(record.tags)
        content_str = "\n".join(record.lines)
        created_str = record.created_at.isoformat()

        if not self.is_memory:
            filepath = self.storage_dir / filename

            # Build frontmatter with optional provenance (P1 hardening)
            frontmatter_lines = [
                "---",
                f"id: {record.id}",
                f"language: {record.language}",
                f"form: {record.form}",
                f"theme: {record.theme}",
                f"created_at: {created_str}",
                f"tags: [{tags_str}]",
            ]

            if record.provenance:
                prov = record.provenance
                if prov.model:
                    frontmatter_lines.append(f"model: {prov.model}")
                if prov.provider:
                    frontmatter_lines.append(f"provider: {prov.provider}")
                if prov.embedding_model:
                    frontmatter_lines.append(f"embedding_model: {prov.embedding_model}")
                if prov.brief_level:
                    frontmatter_lines.append(f"brief_level: {prov.brief_level}")
                if prov.seeds:
                    frontmatter_lines.append(f"seeds: [{', '.join(prov.seeds)}]")
                if prov.tone:
                    frontmatter_lines.append(f"tone: [{', '.join(prov.tone)}]")
                if prov.fragments_used:
                    frontmatter_lines.append(f"fragments_used: [{', '.join(prov.fragments_used)}]")
                if prov.influences_used:
                    frontmatter_lines.append(f"influences_used: [{', '.join(prov.influences_used)}]")
                if prov.n_candidates is not None:
                    frontmatter_lines.append(f"n_candidates: {prov.n_candidates}")
                if prov.temperature is not None:
                    frontmatter_lines.append(f"temperature: {prov.temperature}")
                if prov.latency_ms is not None:
                    frontmatter_lines.append(f"latency_ms: {prov.latency_ms}")
                if prov.total_tokens is not None:
                    frontmatter_lines.append(f"total_tokens: {prov.total_tokens}")

            frontmatter_lines.append("---")
            md_content = "\n".join(frontmatter_lines) + f"\n\n{content_str}\n"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)

        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO poems (id, filename, language, form, theme, created_at, tags, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    filename,
                    record.language,
                    record.form,
                    record.theme,
                    created_str,
                    tags_str,
                    content_str,
                ),
            )

    def list_all(self) -> list[PoemRecord]:
        """Return all saved poems, most recent first."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT id, language, form, theme, created_at, tags, content FROM poems ORDER BY created_at DESC"
        )
        records: list[PoemRecord] = []
        for row in cursor.fetchall():
            pid, lang, form, theme, created_str, tags_str, content = row
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            lines = content.split("\n")
            created_at = datetime.fromisoformat(created_str)
            records.append(
                PoemRecord(
                    lines=lines,
                    language=lang,
                    form=form,
                    theme=theme,
                    created_at=created_at,
                    tags=tags,
                    id=pid,
                )
            )
        return records

    def get(self, poem_id: str) -> PoemRecord | None:
        """Fetch a single poem by its ID.

        Args:
            poem_id: The unique poem identifier.

        Returns:
            PoemRecord if found, None otherwise.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """SELECT id, language, form, theme, created_at, tags, content
               FROM poems WHERE id = ?""",
            (poem_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        pid, lang, form, theme, created_at, tags_str, content = row
        record = PoemRecord(
            id=pid,
            language=lang,
            form=form,
            theme=theme,
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
            tags=[t.strip() for t in tags_str.split(",") if t.strip()],
            lines=content.split("\n") if content else [],
            content=content or "",
        )
        return record

    def search(self, query: str) -> list[PoemRecord]:
        """Substring search across theme, tags and line text using SQLite index."""
        q = f"%{query.lower()}%"
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, language, form, theme, created_at, tags, content
            FROM poems
            WHERE LOWER(theme) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(content) LIKE ?
            ORDER BY created_at DESC
            """,
            (q, q, q),
        )
        records: list[PoemRecord] = []
        for row in cursor.fetchall():
            pid, lang, form, theme, created_str, tags_str, content = row
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            lines = content.split("\n")
            created_at = datetime.fromisoformat(created_str)
            records.append(
                PoemRecord(
                    lines=lines,
                    language=lang,
                    form=form,
                    theme=theme,
                    created_at=created_at,
                    tags=tags,
                    id=pid,
                )
            )
        return records

    def _sync_md_files(self) -> None:
        """Scan directory for .md files and populate SQLite index if missing."""
        if not isinstance(self.storage_dir, Path):
            return

        for filepath in self.storage_dir.glob("*.md"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    text = f.read()

                match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
                if not match:
                    continue

                frontmatter_text, body = match.groups()
                meta: dict[str, str] = {}
                for line in frontmatter_text.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()

                pid = meta.get("id", filepath.stem)
                lang = meta.get("language", "es")
                form = meta.get("form", "unknown")
                theme = meta.get("theme", "")
                created_str = meta.get("created_at", datetime.now().isoformat())

                tags_raw = meta.get("tags", "[]").strip("[]")
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                lines = body.strip().split("\n")

                created_at = datetime.fromisoformat(created_str)

                with self._conn:
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO poems (id, filename, language, form, theme, created_at, tags, content)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pid,
                            filepath.name,
                            lang,
                            form,
                            theme,
                            created_str,
                            ", ".join(tags),
                            "\n".join(lines),
                        ),
                    )
            except Exception:
                continue


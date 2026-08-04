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
    title: str = ""  # Short human-readable title (LLM-suggested or curated)
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    id: str | None = None
    provenance: PoemProvenance | None = None  # P1: generation provenance
    content: str = ""  # convenience mirror of ``lines``; kept in sync by __post_init__

    def __post_init__(self) -> None:
        # ``lines`` and ``content`` are two views of the same text. Some call
        # sites construct with only ``lines`` (add), others with only ``content``
        # (get/search). Keep both in sync so neither is ever stale.
        if not self.content and self.lines:
            self.content = "\n".join(self.lines)
        elif not self.lines and self.content:
            self.lines = self.content.split("\n")


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
            db_path = str(Path(self.storage_dir) / "library.db")
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
                    title TEXT NOT NULL DEFAULT '',
                    theme TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
        # Migration: pre-existing databases lack the ``title`` column.
        try:
            with self._conn:
                self._conn.execute("ALTER TABLE poems ADD COLUMN title TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Column already exists (fresh DB or already migrated)

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
            filepath = Path(self.storage_dir) / filename

            # Build frontmatter with optional provenance (P1 hardening)
            frontmatter_lines = [
                "---",
                f"id: {record.id}",
                f"language: {record.language}",
                f"form: {record.form}",
            ]
            if record.title:
                frontmatter_lines.append(f"title: {record.title}")
            frontmatter_lines.append(f"theme: {record.theme}")
            frontmatter_lines.append(f"created_at: {created_str}")
            frontmatter_lines.append(f"tags: [{tags_str}]")

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
                    frontmatter_lines.append(
                        f"influences_used: [{', '.join(prov.influences_used)}]"
                    )
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
                INSERT OR REPLACE INTO poems (id, filename, language, form, title, theme, created_at, tags, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    filename,
                    record.language,
                    record.form,
                    record.title,
                    record.theme,
                    created_str,
                    tags_str,
                    content_str,
                ),
            )

    def attach_image(self, poem_id: str, image_rel_path: str) -> None:
        """Record an illustration path in a poem's YAML frontmatter.

        GalerIA writes illustrated sheets next to saved poems (``illustrations/
        <id>.png``); this keeps the link discoverable from the poem file itself.
        The path is stored relative to the poem's Markdown file so the pair stays
        portable together.

        Args:
            poem_id: The poem's id (== the Markdown filename stem).
            image_rel_path: Path to the illustration, relative to the poem file.

        Raises:
            FileNotFoundError: The poem's Markdown file does not exist.
            ValueError: The poem file has no parseable YAML frontmatter.
        """
        if self.is_memory:
            return
        filepath = Path(self.storage_dir) / f"{poem_id}.md"
        if not filepath.exists():
            raise FileNotFoundError(f"Poem file not found: {filepath}")

        text = filepath.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            raise ValueError(f"Poem {poem_id} has no YAML frontmatter.")

        front, body = match.groups()
        lines = front.split("\n")
        image_line = f"image: {image_rel_path}"
        if any(line.strip().startswith("image:") for line in lines):
            lines = [image_line if line.strip().startswith("image:") else line for line in lines]
        else:
            lines.append(image_line)

        new_text = f"---\n{chr(10).join(lines)}\n---\n{body}"
        filepath.write_text(new_text, encoding="utf-8")

    def list_all(self) -> list[PoemRecord]:
        """Return all saved poems, most recent first."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT id, language, form, title, theme, created_at, tags, content FROM poems ORDER BY created_at DESC"
        )
        records: list[PoemRecord] = []
        for row in cursor.fetchall():
            pid, lang, form, title, theme, created_str, tags_str, content = row
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            lines = content.split("\n")
            created_at = datetime.fromisoformat(created_str)
            records.append(
                PoemRecord(
                    lines=lines,
                    language=lang,
                    form=form,
                    title=title,
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
            """SELECT id, language, form, title, theme, created_at, tags, content
               FROM poems WHERE id = ?""",
            (poem_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        pid, lang, form, title, theme, created_at, tags_str, content = row
        record = PoemRecord(
            id=pid,
            language=lang,
            form=form,
            title=title,
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
            SELECT id, language, form, title, theme, created_at, tags, content
            FROM poems
            WHERE LOWER(theme) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(content) LIKE ?
            ORDER BY created_at DESC
            """,
            (q, q, q),
        )
        records: list[PoemRecord] = []
        for row in cursor.fetchall():
            pid, lang, form, title, theme, created_str, tags_str, content = row
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            lines = content.split("\n")
            created_at = datetime.fromisoformat(created_str)
            records.append(
                PoemRecord(
                    lines=lines,
                    language=lang,
                    form=form,
                    title=title,
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
                title = meta.get("title", "")
                theme = meta.get("theme", "")
                created_str = meta.get("created_at", datetime.now().isoformat())

                tags_raw = meta.get("tags", "[]").strip("[]")
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                lines = body.strip().split("\n")

                with self._conn:
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO poems (id, filename, language, form, title, theme, created_at, tags, content)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pid,
                            filepath.name,
                            lang,
                            form,
                            title,
                            theme,
                            created_str,
                            ", ".join(tags),
                            "\n".join(lines),
                        ),
                    )
            except Exception:
                continue

"""Load influences from structured YAML (data/influences.yaml).

Replaces the regex-based Markdown parsing in cli.py with a clean YAML loader.
The YAML schema is typed and validated at load time.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from poesia.memoria.records import InfluenceRecord

# Language code mapping from section names
_SECTION_LANG_MAP = {
    "spanish": "es",
    "english": "en",
    "dutch": "nl",
}


def _parse_influence(data: dict[str, Any], language: str) -> InfluenceRecord:
    """Parse a single influence entry from YAML dict."""
    return InfluenceRecord(
        id=data["id"],
        name=data["name"],
        language=language,
        era=data.get("era"),
        movement=data.get("movement"),
        tone=data.get("tone", []),
        forms=data.get("forms", []),
        exemplars=data.get("exemplars", []),
    )


@lru_cache(maxsize=1)
def load_influences(yaml_path: Path | None = None) -> list[InfluenceRecord]:
    """Load all influences from data/influences.yaml.

    Args:
        yaml_path: Override path for testing. Defaults to data/influences.yaml.

    Returns:
        List of InfluenceRecord objects.

    Raises:
        FileNotFoundError: If the YAML file doesn't exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    if yaml_path is None:
        # Default: data/influences.yaml relative to package root
        yaml_path = Path(__file__).parent.parent.parent.parent / "data" / "influences.yaml"

    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    influences: list[InfluenceRecord] = []

    for section, lang_code in _SECTION_LANG_MAP.items():
        if section in data:
            for entry in data[section]:
                influences.append(_parse_influence(entry, lang_code))

    return influences


def get_influence_by_id(influence_id: str) -> InfluenceRecord | None:
    """Look up a single influence by ID."""
    for inf in load_influences():
        if inf.id == influence_id:
            return inf
    return None


def get_influences_by_language(language: str) -> list[InfluenceRecord]:
    """Get all influences for a specific language code."""
    return [inf for inf in load_influences() if inf.language == language]


def get_influences_by_tone(tone: str) -> list[InfluenceRecord]:
    """Get all influences that have a specific tone."""
    tone_lower = tone.lower()
    return [inf for inf in load_influences() if tone_lower in [t.lower() for t in inf.tone]]


def get_influences_by_movement(movement: str) -> list[InfluenceRecord]:
    """Get all influences matching a literary movement (case-insensitive, accent-insensitive).

    Args:
        movement: Movement name to search for, e.g. "Generacion del 98", "Romanticism".

    Returns:
        List of influence records whose movement field contains the query.
    """
    import unicodedata

    def _strip_accents(s: str) -> str:
        """Remove diacritics/accents from a string for matching."""
        return "".join(
            c for c in unicodedata.normalize("NFKD", s)
            if not unicodedata.combining(c)
        )

    q = _strip_accents(movement.lower())
    return [
        inf for inf in load_influences()
        if inf.movement and q in _strip_accents(inf.movement.lower())
    ]


def get_influences_by_era(era_query: str) -> list[InfluenceRecord]:
    """Get all influences within a date range (year-based).

    Args:
        era_query: A year or range like "1900" or "1800-1900".

    Returns:
        List of influence records whose era overlaps the query.
    """
    from poesia.exceptions import PoesiaError

    def _parse_year_range(era_str: str) -> tuple[int, int]:
        """Parse an era string like '1875-1939' or '1770-1850' into (start, end)."""
        parts = era_str.replace(" ", "").split("-")
        try:
            return int(parts[0]), int(parts[1]) if len(parts) > 1 else int(parts[0])
        except (ValueError, IndexError):
            return (0, 9999)

    def _parse_query(q: str) -> tuple[int, int]:
        """Parse a query like '1900' or '1800-1900' into (start, end)."""
        parts = q.replace(" ", "").split("-")
        try:
            return int(parts[0]), int(parts[1]) if len(parts) > 1 else int(parts[0])
        except (ValueError, IndexError):
            raise PoesiaError(f"Invalid era query: '{q}'. Use '1900' or '1800-1900'.")

    q_start, q_end = _parse_query(era_query)
    results = []
    for inf in load_influences():
        if inf.era:
            i_start, i_end = _parse_year_range(inf.era)
            # Check overlap: ranges intersect
            if i_start <= q_end and i_end >= q_start:
                results.append(inf)
    return results


def clear_cache() -> None:
    """Clear the cached influences (for testing)."""
    load_influences.cache_clear()

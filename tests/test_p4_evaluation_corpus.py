"""P4 — Evaluation corpus verification: multilingual fragment collection.

Confirms the corpus is properly structured, frontmatter-parsable,
and contains adequate coverage in both ES and EN for retrieval evaluation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from poesia.cli import _parse_fragment_frontmatter

_FRAGMENTS_DIR = Path(__file__).parent.parent / "seeds" / "angel_fragments"


def _load_all_fragments() -> list[dict]:
    """Load all markdown fragment files and parse their frontmatter.

    Returns:
        List of (filename, frontmatter_dict) tuples.
    """
    results: list[dict] = []
    for md_file in sorted(_FRAGMENTS_DIR.glob("*.md")):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        fm = _parse_fragment_frontmatter(content)
        fm["_file"] = md_file.name
        fm["_raw"] = content
        results.append(fm)
    return results


# ---------------------------------------------------------------------------
# Corpus size and language distribution
# ---------------------------------------------------------------------------


def test_corpus_has_minimum_fragments() -> None:
    """The evaluation corpus must have at least 15 fragments total."""
    fragments = _load_all_fragments()
    assert len(fragments) >= 15, (
        f"Expected >= 15 fragments in corpus, got {len(fragments)}"
    )


@pytest.mark.parametrize(("lang", "min_count"), [("es", 10), ("en", 10)])
def test_corpus_language_coverage(lang: str, min_count: int) -> None:
    """Both ES and EN must have enough fragments for retrieval evaluation."""
    fragments = _load_all_fragments()
    by_lang = [f for f in fragments if f.get("language") == lang]
    assert len(by_lang) >= min_count, (
        f"Expected >= {min_count} {lang} fragments, got {len(by_lang)}"
    )
    assert {f.get("language") for f in fragments} >= {"es", "en"}, (
        "Corpus must contain both ES and EN fragments"
    )


# ---------------------------------------------------------------------------
# Frontmatter integrity
# ---------------------------------------------------------------------------


def test_all_fragments_are_well_formed() -> None:
    """Every fragment has parseable frontmatter, tags/tone/themes, and content."""
    for md_file in _FRAGMENTS_DIR.glob("*.md"):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        fm = _parse_fragment_frontmatter(content)

        assert fm.get("id"), f"{md_file.name}: missing 'id' in frontmatter"
        assert fm.get("type"), f"{md_file.name}: missing 'type' in frontmatter"
        assert fm.get("language"), f"{md_file.name}: missing 'language' in frontmatter"
        assert fm.get("tags"), f"{md_file.name}: missing tags"
        assert fm.get("tone"), f"{md_file.name}: missing tone"
        assert fm.get("themes"), f"{md_file.name}: missing themes"

        parts = content.strip().split("---", 2)
        body = parts[2].strip() if len(parts) >= 3 else content.strip()
        assert len(body) > 20, (
            f"{md_file.name}: body too short ({len(body)} chars)"
        )


# ---------------------------------------------------------------------------
# Cross-lingual theme coverage
# ---------------------------------------------------------------------------


def test_shared_themes_and_tags_across_languages() -> None:
    """Themes and tags should overlap between ES and EN for cross-lingual eval."""
    fragments = _load_all_fragments()
    es_themes: set[str] = set()
    en_themes: set[str] = set()
    es_tags: set[str] = set()
    en_tags: set[str] = set()
    for f in fragments:
        if f.get("language") == "es":
            es_themes |= set(f.get("themes", []))
            es_tags |= set(f.get("tags", []))
        elif f.get("language") == "en":
            en_themes |= set(f.get("themes", []))
            en_tags |= set(f.get("tags", []))

    shared_themes = es_themes & en_themes
    assert len(shared_themes) >= 5, (
        f"Expected >= 5 shared themes between ES and EN, found {len(shared_themes)}"
    )
    shared_tags = es_tags & en_tags
    assert len(shared_tags) >= 3, (
        f"Expected >= 3 shared tags between ES and EN, found {len(shared_tags)}"
    )

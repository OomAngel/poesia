"""P4 — Evaluation corpus verification: multilingual fragment collection.

Confirms the corpus is properly structured, frontmatter-parsable,
and contains adequate coverage in both ES and EN for retrieval evaluation.
"""

from __future__ import annotations

from pathlib import Path

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


def test_corpus_has_spanish_fragments() -> None:
    """At least 10 Spanish (es) fragments must exist."""
    fragments = _load_all_fragments()
    es = [f for f in fragments if f.get("language") == "es"]
    assert len(es) >= 10, (
        f"Expected >= 10 ES fragments, got {len(es)}"
    )


def test_corpus_has_english_fragments() -> None:
    """At least 10 English (en) fragments must exist."""
    fragments = _load_all_fragments()
    en = [f for f in fragments if f.get("language") == "en"]
    assert len(en) >= 10, (
        f"Expected >= 10 EN fragments, got {len(en)}"
    )


def test_corpus_is_multilingual() -> None:
    """The corpus must contain both ES and EN fragments."""
    fragments = _load_all_fragments()
    languages = {f.get("language") for f in fragments}
    assert "es" in languages, "No Spanish fragments in corpus"
    assert "en" in languages, "No English fragments in corpus"


# ---------------------------------------------------------------------------
# Frontmatter integrity
# ---------------------------------------------------------------------------


def test_all_fragments_have_valid_frontmatter() -> None:
    """Every fragment file must have parseable YAML frontmatter."""
    for md_file in _FRAGMENTS_DIR.glob("*.md"):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        fm = _parse_fragment_frontmatter(content)
        assert fm.get("id"), f"{md_file.name}: missing 'id' in frontmatter"
        assert fm.get("type"), f"{md_file.name}: missing 'type' in frontmatter"
        assert fm.get("language"), f"{md_file.name}: missing 'language' in frontmatter"


def test_all_fragments_have_tags_and_tone() -> None:
    """Every fragment must have at least one tag and one tone descriptor."""
    for md_file in _FRAGMENTS_DIR.glob("*.md"):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        fm = _parse_fragment_frontmatter(content)
        assert fm.get("tags"), f"{md_file.name}: missing tags"
        assert fm.get("tone"), f"{md_file.name}: missing tone"
        assert fm.get("themes"), f"{md_file.name}: missing themes"


def test_all_fragments_have_content() -> None:
    """Every fragment must have non-empty body content."""
    for md_file in _FRAGMENTS_DIR.glob("*.md"):
        if md_file.name == "README.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        body = content.strip()
        # Strip frontmatter: remove everything up to the second ---
        parts = body.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
        assert len(body) > 20, (
            f"{md_file.name}: body too short ({len(body)} chars)"
        )


# ---------------------------------------------------------------------------
# Cross-lingual theme coverage
# ---------------------------------------------------------------------------


def test_shared_themes_across_languages() -> None:
    """Themes should overlap between ES and EN for cross-lingual retrieval eval."""
    fragments = _load_all_fragments()
    es_themes: set[str] = set()
    en_themes: set[str] = set()
    for f in fragments:
        themes = set(f.get("themes", []))
        if f.get("language") == "es":
            es_themes |= themes
        elif f.get("language") == "en":
            en_themes |= themes

    shared = es_themes & en_themes
    assert len(shared) >= 5, (
        f"Expected >= 5 shared themes between ES and EN, found {len(shared)}: {shared}"
    )


def test_common_tags_across_languages() -> None:
    """Some tags should appear in both languages (e.g. 'perception', 'loss')."""
    fragments = _load_all_fragments()
    es_tags: set[str] = set()
    en_tags: set[str] = set()
    for f in fragments:
        tags = set(f.get("tags", []))
        if f.get("language") == "es":
            es_tags |= tags
        elif f.get("language") == "en":
            en_tags |= tags

    shared = es_tags & en_tags
    assert len(shared) >= 3, (
        f"Expected >= 3 shared tags between ES and EN, found {len(shared)}: {shared}"
    )

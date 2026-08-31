"""Tests for scripts/fetch_gutenberg_poems.py's text-splitting heuristics."""

from __future__ import annotations

from scripts.fetch_gutenberg_poems import (
    _BOILERPLATE_PHRASE_RE,
    BookSpec,
    _clean_line,
    _is_prose_block,
    build_records,
    extract_body,
    process_book,
    split_into_poems,
)


def test_split_into_poems_finds_title_and_body() -> None:
    body = "\n".join(
        [
            "SUCCESS.",
            "",
            "Success is counted sweetest",
            "By those who ne'er succeed to reach it",
            "",
            "II.",
            "",
            "The soul selects her own society",
            "Then shuts the door on everyone forever",
        ]
    )
    poems = split_into_poems(body)
    assert [title for title, _ in poems] == ["SUCCESS.", "II."]
    assert "Success is counted sweetest" in poems[0][1]


def test_split_into_poems_rejects_wrapped_prose_block() -> None:
    body = "\n".join(
        [
            "A TITLE",
            "",
            "This is a short line of verse that is long enough to pass",
            "and here is a second line of verse to round it out nicely",
            "",
            "INTRODUCTION",
            "",
            "This introductory paragraph is written in ordinary prose and wraps"
            " naturally across the page at a fairly wide column width, unlike"
            " verse.",
            "It continues onto a second line that is also long enough to trip"
            " the prose-detection heuristic reliably in this test.",
            "A short closer.",
        ]
    )
    poems = split_into_poems(body)
    titles = [title for title, _ in poems]
    assert "A TITLE" in titles
    # The prose block under INTRODUCTION should be dropped entirely, leaving
    # no poem body long enough to pass MIN_POEM_CHARS.
    assert "INTRODUCTION" not in titles


def test_split_into_poems_drops_boilerplate_and_bare_numbers() -> None:
    body = "\n".join(
        [
            "A TITLE",
            "",
            "134",
            "Some real verse line here that is long enough to count",
            "Another real verse line here that is long enough to count",
            "This work is distributed by Project Gutenberg under its license",
        ]
    )
    poems = split_into_poems(body)
    assert len(poems) == 1
    text = poems[0][1]
    assert "134" not in text.split("\n")
    assert "Project Gutenberg" not in text


def test_clean_line_strips_footnote_markers_and_syllable_counts() -> None:
    assert _clean_line("Y en el silencio eterno[334]") == "Y en el silencio eterno"
    assert _clean_line("A line with a trailing count   11") == "A line with a trailing count"


def test_is_prose_block_requires_at_least_three_lines() -> None:
    assert not _is_prose_block(["one long enough line to look wide but too few lines total here"])


def test_is_prose_block_true_for_wide_wrapped_lines() -> None:
    lines = [
        "This line is deliberately padded out to exceed the wrap width threshold.",
        "So is this second line, padded out the same way to exceed that width.",
        "Short closer.",
    ]
    assert _is_prose_block(lines)


def test_is_prose_block_false_for_short_verse_lines() -> None:
    lines = [
        "Bajo la luna",
        "caminan las sombras",
        "en el jardín",
    ]
    assert not _is_prose_block(lines)


def test_boilerplate_phrase_regex_catches_legal_text_not_common_words() -> None:
    assert _BOILERPLATE_PHRASE_RE.search("Project Gutenberg's terms of use")
    # Unlike generate_synthetic_repair_pairs._BOILERPLATE_RE, ordinary English
    # words must not be flagged, since this corpus is now bilingual.
    assert not _BOILERPLATE_PHRASE_RE.search("The rose and the thorn")


def test_extract_body_returns_none_without_markers() -> None:
    assert extract_body("no markers here at all") is None


def test_extract_body_slices_between_start_and_end_markers() -> None:
    raw = (
        "front matter\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\n"
        "the actual poem body\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\n"
        "license text"
    )
    body = extract_body(raw)
    assert body is not None
    assert "the actual poem body" in body
    assert "license text" not in body
    assert "front matter" not in body


def test_build_records_uses_language_name_and_metadata() -> None:
    spec = BookSpec(1, "Test Author", "test_tag", "es", "verify")
    records = build_records(spec, [("Un Título", "línea uno\nlínea dos")])
    assert records == [
        {
            "prompt": "Write a Spanish poem: Un Título",
            "completion": "línea uno\nlínea dos",
            "author": "Test Author",
            "source": "test_tag",
            "title": "Un Título",
            "form": "unknown",
            "language": "es",
        }
    ]


def test_process_book_falls_back_to_single_poem_when_no_title_found(monkeypatch, tmp_path) -> None:
    raw = (
        "Title: A Single Long Poem\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\n"
        "This poem never has a standalone short title line of its own\n"
        "so the title-based splitter finds nothing to latch onto here\n"
        "and every line just keeps flowing into the next one endlessly\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\n"
    )
    spec = BookSpec(1, "Test Author", "test_fallback", "en", "EXAMPLE")

    monkeypatch.setattr("scripts.fetch_gutenberg_poems.fetch_raw_text", lambda book_id: raw)
    monkeypatch.setattr("scripts.fetch_gutenberg_poems.OUTPUT_DIR", tmp_path)

    count = process_book(spec, dry_run=False)

    assert count == 1
    out_file = tmp_path / "test_fallback.jsonl"
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "A Single Long Poem" in content


def test_process_book_skips_on_verify_substr_mismatch(monkeypatch, tmp_path) -> None:
    raw = "*** START OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\nbody\n*** END OF THE PROJECT GUTENBERG EBOOK EXAMPLE ***\n"
    spec = BookSpec(1, "Test Author", "test_mismatch", "en", "NotInHeader")

    monkeypatch.setattr("scripts.fetch_gutenberg_poems.fetch_raw_text", lambda book_id: raw)
    monkeypatch.setattr("scripts.fetch_gutenberg_poems.OUTPUT_DIR", tmp_path)

    count = process_book(spec, dry_run=False)

    assert count == 0
    assert not (tmp_path / "test_mismatch.jsonl").exists()

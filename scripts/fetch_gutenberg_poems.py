#!/usr/bin/env python3
"""Download and structure new poetry collections from Project Gutenberg.

Extends seeds/poetry_corpus/training_data_structured/ with additional
public-domain poetry books, in both Spanish (the corpus' primary language)
and English (previously entirely absent). Follows the download/provenance
convention documented in docs/CORPUS_SOURCES.md:

    curl -sL https://www.gutenberg.org/cache/epub/{ID}/pg{ID}.txt

Splitting a raw Gutenberg text into individual poems is a heuristic, not an
exact parse (there is no structured markup to rely on) — see "Known
limitations" in docs/CORPUS_SOURCES.md for what this does and doesn't catch
cleanly. Two signals do most of the work:

1. A standalone short line (a title, a roman numeral, "SONETOS", etc.)
   between blank lines starts a new poem; everything up to the next such
   line is its body.
2. A candidate body block is rejected as prose (front matter, editorial
   introductions, footnotes) if most of its lines run up against the
   ~70-character plain-text wrap width — verse lines break naturally and
   rarely do this, wrapped prose paragraphs almost always do.

Usage:
    python scripts/fetch_gutenberg_poems.py            # fetch the full manifest
    python scripts/fetch_gutenberg_poems.py --only garcilaso whitman
    python scripts/fetch_gutenberg_poems.py --dry-run  # download+parse, don't write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

OUTPUT_DIR = Path("seeds/poetry_corpus/training_data_structured")
RAW_CACHE_DIR = Path("/tmp/gutenberg_raw_cache")

# Phrase-level Gutenberg/legal boilerplate — deliberately NOT single common
# words (unlike scripts/generate_synthetic_repair_pairs.py's _BOILERPLATE_RE,
# which only needs to catch English words leaking into a Spanish corpus).
# Here the corpus is bilingual, so "the"/"and" would false-positive on every
# real English poem line.
_BOILERPLATE_PHRASE_RE = re.compile(
    r"project gutenberg|gutenberg license|trademark|copyright law|"
    r"electronic works?|distributed proofread|www\.gutenberg|"
    r"terms of use|this ebook is for the use",
    re.IGNORECASE,
)
_FOOTNOTE_MARKER_RE = re.compile(r"\[\d+\]")
_BARE_NUMBER_LINE_RE = re.compile(r"^\d+$")  # stray stanza/verse numbering (e.g. Martín Fierro)
_TRAILING_SYLLABLE_COUNT_RE = re.compile(r"\s{2,}\d+\s*$")
_START_MARKER_RE = re.compile(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*")
_END_MARKER_RE = re.compile(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*")

PROSE_WRAP_WIDTH = 58
PROSE_LINE_FRACTION = 0.6
MIN_POEM_LINES = 2
MIN_POEM_CHARS = 60


@dataclass
class BookSpec:
    book_id: int
    author: str
    tag: str
    language: str  # "es" | "en"
    verify_substr: str  # must appear in the raw header to confirm the right book
    # Some Gutenberg editions bundle unrelated prose (legends, essays,
    # introductions) alongside the actual verse. When set, only the text
    # from this exact standalone line onward is considered.
    section_start: str | None = None
    # Some editions append a critical/variorum apparatus (footnotes, editor
    # notes in other languages) after the actual poems end. When set, text
    # from this literal substring onward is dropped.
    section_end: str | None = None


MANIFEST: list[BookSpec] = [
    # --- Spanish ---
    BookSpec(
        53552,
        "Gustavo Adolfo Bécquer",
        "gutenberg_becquer_obras",
        "es",
        "Bécquer",
        section_start="RIMAS",  # the rest of this edition is prose (Leyendas), not verse
    ),
    BookSpec(15781, "José de Espronceda", "gutenberg_espronceda_estudiante", "es", "Espronceda"),
    BookSpec(68131, "Garcilaso de la Vega", "gutenberg_garcilaso_obras", "es", "Garcilaso"),
    BookSpec(74087, "Sor Juana Inés de la Cruz", "gutenberg_sor_juana_selectas", "es", "Juana"),
    BookSpec(49914, "Lope de Stúñiga", "gutenberg_stuniga_cancionero", "es", "iga"),
    BookSpec(
        43950, "Various (Cancionero de Uppsala)", "gutenberg_cancionero_uppsala", "es", "Cancionero"
    ),
    BookSpec(14765, "José Hernández", "gutenberg_martin_fierro_1", "es", "Hernández"),
    BookSpec(15066, "José Hernández", "gutenberg_martin_fierro_2", "es", "Hernández"),
    BookSpec(16319, "José Campo Arana", "gutenberg_campo_arana_impresiones", "es", "Campo"),
    BookSpec(
        25807,
        "Edgar Allan Poe (trad. Pérez Bonalde, Torres, Lasplaces)",
        "gutenberg_poe_poemas_es",
        "es",
        "Poe",
    ),
    BookSpec(
        49333,
        "Jorge Manrique",
        "gutenberg_manrique_coplas",
        "es",
        "Manrique",
        section_start="COPLAS",  # skips the editor's French-language critical preface
        section_end="Titre: _A._ Torna el actor y faze fin",  # skips the variorum apparatus after copla 40
    ),
    BookSpec(
        70984,
        "Rosalía de Castro",
        "gutenberg_rosalia_castro_sar",
        "es",
        "Castro",
        section_start="ORILLAS DEL SAR",  # skips Murguía's prose prologue
    ),
    BookSpec(29497, "Tomás de Iriarte", "gutenberg_iriarte_fabulas", "es", "Iriarte"),
    BookSpec(
        55206,
        "Félix María Samaniego",
        "gutenberg_samaniego_fabulas",
        "es",
        "Samaniego",
        section_start="LIBRO PRIMERO",  # skips editor bio/vocabulary front matter
    ),
    BookSpec(64058, "María Goyri (comp.)", "gutenberg_goyri_fabulas_cuentos", "es", "Goyri"),
    # --- English ---
    BookSpec(12242, "Emily Dickinson", "gutenberg_dickinson_poems", "en", "Dickinson"),
    BookSpec(1057, "Oscar Wilde", "gutenberg_wilde_poems", "en", "Wilde"),
    BookSpec(79363, "William Blake", "gutenberg_blake_poems", "en", "Blake"),
    BookSpec(12843, "Ralph Waldo Emerson", "gutenberg_emerson_poems", "en", "Emerson"),
    BookSpec(1279, "Robert Burns", "gutenberg_burns_poems", "en", "Burns"),
    BookSpec(23684, "John Keats", "gutenberg_keats_1820", "en", "Keats"),
    BookSpec(1322, "Walt Whitman", "gutenberg_whitman_leaves", "en", "Whitman"),
    BookSpec(8601, "Alfred Lord Tennyson", "gutenberg_tennyson_early", "en", "Tennyson"),
    BookSpec(9574, "John Greenleaf Whittier", "gutenberg_whittier_poems", "en", "Whittier"),
    BookSpec(28041, "Robert Browning", "gutenberg_browning_selections", "en", "Browning"),
    BookSpec(38877, "W. B. Yeats", "gutenberg_yeats_poems", "en", "Yeats"),
    BookSpec(1065, "Edgar Allan Poe", "gutenberg_poe_raven", "en", "Poe"),
]


def fetch_raw_text(book_id: int) -> str:
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_CACHE_DIR / f"pg{book_id}.txt"
    if not cache_path.exists():
        url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        cache_path.write_bytes(data)
        time.sleep(1)  # be polite to gutenberg.org between fetches
    return cache_path.read_text(encoding="utf-8", errors="replace")


def extract_body(raw_text: str) -> str | None:
    start = _START_MARKER_RE.search(raw_text)
    end = _END_MARKER_RE.search(raw_text)
    if not start or not end or start.end() >= end.start():
        return None
    return raw_text[start.end() : end.start()]


def _is_prose_block(lines: list[str]) -> bool:
    if len(lines) < 3:
        return False
    # The last line of a wrapped paragraph is typically short — ignore it.
    body = lines[:-1]
    wide = sum(1 for line in body if len(line.strip()) >= PROSE_WRAP_WIDTH)
    return (wide / len(body)) >= PROSE_LINE_FRACTION


def _clean_line(line: str) -> str:
    line = _FOOTNOTE_MARKER_RE.sub("", line)
    line = _TRAILING_SYLLABLE_COUNT_RE.sub("", line)
    return line.strip()


def split_into_poems(body: str) -> list[tuple[str, str]]:
    raw_lines = body.split("\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in raw_lines:
        if raw_line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(raw_line)
    if current:
        blocks.append(current)

    poems: list[tuple[str, str]] = []
    title: str | None = None
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal title, body_lines
        if title is not None and body_lines:
            cleaned = [_clean_line(l) for l in body_lines]
            cleaned = [
                l
                for l in cleaned
                if l and not _BOILERPLATE_PHRASE_RE.search(l) and not _BARE_NUMBER_LINE_RE.match(l)
            ]
            text = "\n".join(cleaned).strip()
            if len(cleaned) >= MIN_POEM_LINES and len(text) >= MIN_POEM_CHARS:
                poems.append((title, text))
        title = None
        body_lines = []

    for block in blocks:
        stripped0 = block[0].strip()
        is_title_like = (
            len(block) == 1
            and 0 < len(stripped0) <= 60
            # A trailing period is common for titles/roman numerals ("II.",
            # "SUCCESS.") so it's deliberately not excluded here — only
            # punctuation that marks a mid-sentence prose fragment is.
            and stripped0[-1] not in ",;:?!"
            and not _BOILERPLATE_PHRASE_RE.search(stripped0)
            # Footnote/variant-apparatus entries ("[2] _A._ maestro.") look
            # like short titles but aren't — reject them explicitly.
            and not _FOOTNOTE_MARKER_RE.match(stripped0)
        )
        if is_title_like:
            flush()
            title = _clean_line(stripped0)
            continue
        if title is None:
            continue  # front matter before the first detected title
        if _is_prose_block(block):
            continue
        body_lines.extend(block)
    flush()
    return poems


def build_records(spec: BookSpec, poems: list[tuple[str, str]]) -> list[dict]:
    lang_name = "Spanish" if spec.language == "es" else "English"
    records = []
    for title, text in poems:
        records.append(
            {
                "prompt": f"Write a {lang_name} poem: {title}",
                "completion": text,
                "author": spec.author,
                "source": spec.tag,
                "title": title,
                "form": "unknown",
                "language": spec.language,
            }
        )
    return records


def process_book(spec: BookSpec, dry_run: bool) -> int:
    try:
        raw = fetch_raw_text(spec.book_id)
    except Exception as exc:  # noqa: BLE001 - report and move on
        print(f"  ERROR fetching {spec.book_id}: {exc}")
        return 0

    if spec.verify_substr not in raw[:4000]:
        print(f"  SKIP {spec.tag}: expected '{spec.verify_substr}' not found in header — wrong ID?")
        return 0

    body = extract_body(raw)
    if body is None:
        print(f"  SKIP {spec.tag}: could not find START/END Gutenberg markers")
        return 0

    if spec.section_start is not None:
        marker = re.search(rf"^{re.escape(spec.section_start)}\s*$", body, re.MULTILINE)
        if marker is None:
            print(f"  SKIP {spec.tag}: section_start {spec.section_start!r} not found")
            return 0
        body = body[marker.start() :]

    if spec.section_end is not None:
        end_idx = body.find(spec.section_end)
        if end_idx == -1:
            print(f"  SKIP {spec.tag}: section_end {spec.section_end!r} not found")
            return 0
        body = body[:end_idx]

    poems = split_into_poems(body)
    if not poems:
        # No standalone title line anywhere (e.g. a single-poem book like
        # "The Raven") — fall back to treating the whole body as one poem,
        # titled from Gutenberg's own metadata.
        title_match = re.search(r"^Title:\s*(.+)$", raw, re.MULTILINE)
        fallback_title = title_match.group(1).strip() if title_match else spec.tag
        cleaned = [_clean_line(l) for l in body.split("\n")]
        cleaned = [l for l in cleaned if l and not _BOILERPLATE_PHRASE_RE.search(l)]
        text = "\n".join(cleaned).strip()
        if len(cleaned) >= MIN_POEM_LINES and len(text) >= MIN_POEM_CHARS:
            poems = [(fallback_title, text)]

    records = build_records(spec, poems)
    print(f"  {spec.tag}: {len(records)} poems extracted")

    if not dry_run and records:
        out_path = OUTPUT_DIR / f"{spec.tag}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="Substrings to filter MANIFEST tags")
    parser.add_argument(
        "--dry-run", action="store_true", help="Fetch and parse, but don't write JSONL"
    )
    args = parser.parse_args()

    specs = MANIFEST
    if args.only:
        specs = [s for s in specs if any(sub in s.tag for sub in args.only)]
        if not specs:
            print("No manifest entries matched --only", file=sys.stderr)
            sys.exit(1)

    total = 0
    for spec in specs:
        total += process_book(spec, args.dry_run)
    print(
        f"\nTotal poems extracted: {total}"
        + (" (dry run, nothing written)" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()

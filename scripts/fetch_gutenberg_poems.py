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

Italian books (``LINKING_MANIFEST``) are for the page's linking index only, not training:
``--linking-only`` writes them to seeds/poetry_corpus/linking_only/, which build_corpus.py
does not read, so adding them leaves the training corpus unchanged.

Usage:
    python scripts/fetch_gutenberg_poems.py            # fetch the full manifest
    python scripts/fetch_gutenberg_poems.py --linking-only   # Italian, for linking
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
LINKING_ONLY_DIR = Path("seeds/poetry_corpus/linking_only")
LANGUAGE_NAMES = {"es": "Spanish", "en": "English", "it": "Italian"}
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
    language: str  # "es" | "en" | "it"
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
    # 2026-10-04 round: the remaining original Spanish verse in the Gutenberg
    # catalogue (pg_catalog.csv, language es, poetry subjects); the other
    # untaken entries are prose or translations.
    BookSpec(
        47650,
        "Rubén Darío",
        "gutenberg_dario_prosas_profanas",
        "es",
        "PROSAS PROFANAS",
        section_start="ERA UN AIRE SUAVE...",  # skips the "Palabras liminares" prose preface
        section_end="ÍNDICE",
    ),
    BookSpec(
        51711,
        "Rubén Darío",
        "gutenberg_dario_canto_errante",
        "es",
        "CANTO ERRANTE",
        section_start="EL CANTO ERRANTE",  # first unindented one; skips the "Dilucidaciones" essay
        section_end="INDICE",
    ),
    BookSpec(
        63378,
        "Luis G. Urbina",
        "gutenberg_urbina_corazon_juglar",
        "es",
        "Urbina",
        section_start="         LAMINA ANTIGUA",  # skips the dedication
        section_end="INDICE",
    ),
    BookSpec(
        16201,
        "Various (comp. Eduardo Martín de la Cámara)",
        "gutenberg_parnaso_filipino",
        "es",
        "Parnaso Filipino",
        section_end="FIN",  # the prose prologue is dropped by the prose filter
    ),
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
    BookSpec(
        8774,
        "William Wordsworth",
        "gutenberg_wordsworth_poems_v1",
        "en",
        "Wordsworth",
        section_start="TO THE DAISY.",  # skips the italicized front-matter table of contents
        section_end="_NOTES to the FIRST VOLUME_",  # skips the trailing editor's-notes apparatus
    ),
    BookSpec(
        2002,
        "Elizabeth Barrett Browning",
        "gutenberg_ebb_sonnets_portuguese",
        "en",
        "Barrett Browning",
    ),
    BookSpec(
        16950,
        "Christina Rossetti",
        "gutenberg_rossetti_goblin_market",
        "en",
        "Rossetti",
        section_start="GOBLIN MARKET",  # skips the front-matter table of contents
    ),
    BookSpec(
        10031,
        "Edgar Allan Poe",
        "gutenberg_poe_complete",
        "en",
        "Poe",
        section_start="THE RAVEN.",  # skips the TOC + prose memoir of Poe's life
        section_end="PROSE POEMS.",  # this "complete works" edition also bundles Poe's prose
    ),
    # Shelley's, Longfellow's, and Coleridge's "Complete Poetical Works" editions
    # (4800; 1365; 29090/29091/29092) were evaluated and dropped: unlike the books
    # above, they bundle full dramatic works (plays) and, in Coleridge's case, a
    # footnoted-variorum apparatus, interspersed throughout the whole text rather
    # than confined to a front/back block that section_start/section_end could cut.
    # Random sampling found the heuristic splitter misdetecting stage directions
    # and play dialogue as "poems" at 20-50% rates (worse for Longfellow, whose
    # "Complete Poetical Works" is even more play-heavy), far above the noise
    # tolerance accepted elsewhere in this corpus. Skipped rather than force a bad
    # fix; a hand-curated lyric-only selection from each could be revisited later.
]


# Italian, for the page's linking index only (--linking-only; never training). Chosen
# 2026-10-07 from pg_catalog.csv (language it, poetry subjects, author searches): lyric
# collections by authors who died by 1955; Aleramo and Palazzeschi (died after 1955) and
# Pascarella (Roman dialect) left out; Pellico's "Poesie scelte" (17671) is a tragedy, not lyrics.
LINKING_MANIFEST: list[BookSpec] = [
    BookSpec(55236, "Giacomo Leopardi", "gutenberg_leopardi_canti", "it", "Leopardi"),
    BookSpec(36060, "Ada Negri", "gutenberg_negri_dal_profondo", "it", "Negri"),
    BookSpec(36061, "Ada Negri", "gutenberg_negri_maternita", "it", "Negri"),
    BookSpec(36063, "Ada Negri", "gutenberg_negri_tempeste", "it", "Negri"),
    BookSpec(36239, "Ada Negri", "gutenberg_negri_fatalita", "it", "Negri"),
    BookSpec(36792, "Ada Negri", "gutenberg_negri_esilio", "it", "Negri"),
    BookSpec(58615, "Annie Vivanti", "gutenberg_vivanti_lirica", "it", "Vivanti"),
    BookSpec(59903, "Vittorio Betteloni", "gutenberg_betteloni_nuovi_versi", "it", "Betteloni"),
    BookSpec(60549, "Giuseppe Montanelli", "gutenberg_montanelli_liriche", "it", "Montanelli"),
    BookSpec(
        61548, "Amalia Guglielminetti", "gutenberg_guglielminetti_seduzioni", "it", "Guglielminetti"
    ),
    BookSpec(
        62563,
        "Mario Rapisardi",
        "gutenberg_rapisardi_ricordanze",
        "it",
        "Rapisardi",
        section_end="INTERMEZZO.",  # then a verse drama (Francesca da Rimini), not lyrics
    ),
    BookSpec(19428, "Luigi Gualdo", "gutenberg_gualdo_nostalgie", "it", "Gualdo"),
    BookSpec(17905, "Emilio De Marchi", "gutenberg_de_marchi_vecchie_cadenze", "it", "De Marchi"),
    BookSpec(27825, "Gabriele D'Annunzio", "gutenberg_dannunzio_isaotta", "it", "Annunzio"),
    BookSpec(58648, "Gabriele D'Annunzio", "gutenberg_dannunzio_elegie_romane", "it", "Annunzio"),
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


# Shown to people (linking), so stricter than training: front matter, speaker labels of
# dramatic passages and verse lines taken for titles are dropped, asterisk titles blanked.
_FRONT_MATTER_TITLE_RE = re.compile(
    r"indice|propriet[àa] letteraria|prefazione|\bnota\b|dedica|riservati|\btip\.|"
    r"trascrittore|editori|notizia intorno|\bpag\.|personaggi|tragedia|scena|interlocutori|"
    r"\batto\b|prologo|\bvoce\b|\bcoro\b|cantando|»",  # dramatic passages; contents lines
    re.IGNORECASE,
)


def clean_for_display(spec: BookSpec, poems: list[tuple[str, str]]) -> list[tuple[str, str]]:
    counts: dict[str, int] = {}
    for title, _ in poems:
        counts[title.upper()] = counts.get(title.upper(), 0) + 1
    surname = spec.author.split()[-1].upper()
    kept = []
    for title, text in poems:
        if not any(c.isalpha() for c in title) or title.startswith("("):
            kept.append(("", text))  # "* * *", "—————", "[1887-1891]", "(Villa Cesarini)"
            continue
        bare = title.strip("_ .")
        if (
            _FRONT_MATTER_TITLE_RE.search(title)
            or surname in title.upper()
            or title.startswith("_")  # italic verse lines and speaker labels, not titles
            or (counts[title.upper()] >= 2 and not re.fullmatch(r"[IVXLC]+", bare))
            or (len(bare) > 30 and (bare[:1].islower() or title.rstrip("_ ")[-1:] in ".!?;,—"))
            or "Pag." in text
        ):
            continue
        kept.append((title, text))
    return kept


def build_records(spec: BookSpec, poems: list[tuple[str, str]]) -> list[dict]:
    lang_name = LANGUAGE_NAMES[spec.language]
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


def process_book(
    spec: BookSpec, dry_run: bool, out_dir: Path = OUTPUT_DIR, display: bool = False
) -> int:
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

    if display:
        poems = clean_for_display(spec, poems)
    records = build_records(spec, poems)
    print(f"  {spec.tag}: {len(records)} poems extracted")

    if not dry_run and records:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{spec.tag}.jsonl"
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
    parser.add_argument(
        "--linking-only",
        action="store_true",
        help=f"Fetch LINKING_MANIFEST (Italian) into {LINKING_ONLY_DIR}, outside training",
    )
    args = parser.parse_args()

    specs = LINKING_MANIFEST if args.linking_only else MANIFEST
    out_dir = LINKING_ONLY_DIR if args.linking_only else OUTPUT_DIR
    if args.only:
        specs = [s for s in specs if any(sub in s.tag for sub in args.only)]
        if not specs:
            print("No manifest entries matched --only", file=sys.stderr)
            sys.exit(1)

    total = 0
    for spec in specs:
        total += process_book(spec, args.dry_run, out_dir, display=args.linking_only)
    print(
        f"\nTotal poems extracted: {total}"
        + (" (dry run, nothing written)" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()

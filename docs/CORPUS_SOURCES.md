# PoesIA Corpus — Sources & Provenance

> **Status:** Active · **Last updated:** 2026-08-31

## Overview

The poetry corpus lives in `seeds/poetry_corpus/`. Structured training data is in
`training_data_structured/` (JSONL with `prompt`/`completion` + metadata).

**Total unique poems: ~12,680** (across 55+ structured files; dedup pending).
**Language split: ~9,300 Spanish, ~3,373 English** (English added 2026-08-31 — the
corpus was 100% Spanish before this).

## Sources

### Gutenberg (Project Gutenberg — public domain)

| Book ID | Work | Author(s) | Poems | Source tag |
|---------|------|-----------|-------|------------|
| 65880 | Las cien mejores poesías de la lengua castellana | 37 canonical poets | 92 | gutenberg_cien_poesias |
| 68525 | Poesías completas | Antonio Machado | 165 | gutenberg_machado |
| 75703 | Libro de poemas | Federico García Lorca | 69 | gutenberg_lorca_libro |
| 72665 | Romancero gitano | Federico García Lorca | 28 | gutenberg_lorca_romancero |
| 50341 | Cantos de Vida y Esperanza | Rubén Darío | 57 | gutenberg_dario_cantos |
| 51569 | Poema del Otoño y otros | Rubén Darío | 36 | gutenberg_dario_otono |
| 53867 | Lira Póstuma | Rubén Darío | 44 | gutenberg_dario_lira_postuma |
| 51458 | Canto a la Argentina | Rubén Darío | 15 | gutenberg_dario_canto_argentina |
| 35407 | Rimas | Bartolomé Mitre | 97 | gutenberg_mitre_rimas |
| 47184 | Antología portorriqueña | Various | 78 | gutenberg_antologia_portorriquena |
| 57648 | Romancero selecto del Cid | Anónimo | 49 | gutenberg_cid |
| 55480 | Granada, poema oriental I | José Zorrilla | 29 | gutenberg_zorrilla_granada1 |
| 58275 | Granada, poema oriental II | José Zorrilla | 26 | gutenberg_zorrilla_granada2 |
| 63823 | Nuevas poesías | Almafuerte | 25 | gutenberg_almafuerte |
| 61415 | Místicas | María Raquel Adler | 20 | gutenberg_adler_misticas |
| 58103 | 20 poemas para ser leídos en el tranvía | Oliverio Girondo | 23 | gutenberg_girondo_20 |

**Gutenberg subtotal (original batch): ~853 poems**

### Gutenberg — 2026-08-31 expansion (`scripts/fetch_gutenberg_poems.py`)

Fetched via the same download convention, but split into poems automatically
(title-line detection + prose-block rejection — see "Known limitations" below)
rather than hand-curated, so per-book counts include some heuristic noise.

| Book ID | Work | Author(s) | Poems | Language | Source tag |
|---------|------|-----------|-------|----------|------------|
| 53552 | Obras escogidas (Rimas only) | Gustavo Adolfo Bécquer | 81 | es | gutenberg_becquer_obras |
| 15781 | El estudiante de Salamanca | José de Espronceda | 82 | es | gutenberg_espronceda_estudiante |
| 68131 | Obras | Garcilaso de la Vega | 163 | es | gutenberg_garcilaso_obras |
| 74087 | Poesías selectas | Sor Juana Inés de la Cruz | 260 | es | gutenberg_sor_juana_selectas |
| 49914 | Cancionero | Lope de Stúñiga | 313 | es | gutenberg_stuniga_cancionero |
| 43950 | Cancionero de Uppsala | Various | 69 | es | gutenberg_cancionero_uppsala |
| 14765 | Martín Fierro (Ida) | José Hernández | 14 | es | gutenberg_martin_fierro_1 |
| 15066 | Martín Fierro (Vuelta) | José Hernández | 46 | es | gutenberg_martin_fierro_2 |
| 16319 | Impresiones y paisajes | José Campo Arana | 80 | es | gutenberg_campo_arana_impresiones |
| 25807 | Poemas (trad. Pérez Bonalde et al.) | Edgar Allan Poe | 49 | es | gutenberg_poe_poemas_es |
| 49333 | Coplas por la muerte de su padre | Jorge Manrique | 40 | es | gutenberg_manrique_coplas |
| 70984 | En las orillas del Sar | Rosalía de Castro | 178 | es | gutenberg_rosalia_castro_sar |
| 29497 | Fábulas literarias | Tomás de Iriarte | 75 | es | gutenberg_iriarte_fabulas |
| 55206 | Fábulas | Félix María Samaniego | 204 | es | gutenberg_samaniego_fabulas |
| 64058 | Fábulas y cuentos en verso | Various (comp. María Goyri) | 150 | es | gutenberg_goyri_fabulas_cuentos |
| 12242 | Poems | Emily Dickinson | 451 | en | gutenberg_dickinson_poems |
| 1057 | Poems | Oscar Wilde | 129 | en | gutenberg_wilde_poems |
| 79363 | Poems | William Blake | 172 | en | gutenberg_blake_poems |
| 12843 | Poems | Ralph Waldo Emerson | 262 | en | gutenberg_emerson_poems |
| 1279 | Poems | Robert Burns | 677 | en | gutenberg_burns_poems |
| 23684 | Poems (1820) | John Keats | 218 | en | gutenberg_keats_1820 |
| 1322 | Leaves of Grass | Walt Whitman | 305 | en | gutenberg_whitman_leaves |
| 8601 | Early poems | Alfred Lord Tennyson | 359 | en | gutenberg_tennyson_early |
| 9574 | Poems | John Greenleaf Whittier | 146 | en | gutenberg_whittier_poems |
| 28041 | Selections | Robert Browning | 218 | en | gutenberg_browning_selections |
| 38877 | Poems | W. B. Yeats | 435 | en | gutenberg_yeats_poems |
| 1065 | The Raven | Edgar Allan Poe | 1 | en | gutenberg_poe_raven |

**2026-08-31 expansion subtotal: 5,177 poems (1,804 Spanish + 3,373 English)**, spanning
sonnets/silvas (Garcilaso), rimas (Bécquer), coplas de pie quebrado (Manrique),
romance/cancionero verse (Stúñiga, Uppsala), gauchesque octosyllables (Martín
Fierro), and verse fables (Iriarte, Samaniego, Goyri) on the Spanish side. Note:
per-book counts for Garcilaso, Stúñiga, Tennyson, and Emerson were revised down
slightly from an earlier pass after a bugfix (see "Known limitations" below) —
these are corrected, final counts.

### Wikisource (es.wikisource.org)

| Author | Poems | Source tag |
|--------|-------|------------|
| Sor Juana Inés de la Cruz | 23 | wikisource_sor_juana |
| Manuel Acuña | 37 | wikisource_acuna |

**Wikisource subtotal: ~60 poems** (fetched via MediaWiki API; rate-limit friendly pacing)

### Repo / curated

| Source | Poems | Source tag |
|--------|-------|------------|
| sonetos_curated (remaining) | 146 | sonetos_ingested_extra |

**Mexican poets in corpus: 601 poems** across 15 authors (Nervo 142, López Velarde 139,
Sor Juana 76, Gutiérrez Nájera 52, Acuña 67, Sabines 38, Paz 32, Díaz Mirón 12, Urbina 9...)

## Re-fetch / extension commands

```bash
# Gutenberg download pattern
curl -sL https://www.gutenberg.org/cache/epub/{ID}/pg{ID}.txt -o /tmp/gutenberg_{ID}.txt

# Wikisource fetch (MediaWiki API)
# See scripts/ patterns — search es.wikisource.org Categoría: for more authors
```

## Known limitations

- Machado titles not extracted (740/743 are "Poema") — recover from Gutenberg TOC
- Some files contain publisher/editorial pages captured as poems (cleanup in progress)
- No dedup across files yet (next training run should use the dedup'd build)
- Copyright: Octavio Paz (†1998), Sabines (†1999) NOT public domain in Mexico (life+100);
  present in corpus but not for commercial training
- The 2026-08-31 Gutenberg expansion uses a generic title-line + prose-rejection
  heuristic (`scripts/fetch_gutenberg_poems.py`) instead of per-book hand curation,
  so it occasionally misfires: a table-of-contents block can be captured as a
  pseudo-poem (seen in `gutenberg_tennyson_early`) and a dedication letter can slip
  through as a "poem" (seen in `gutenberg_martin_fierro_1`). Spot-checked across
  several files at various sizes and judged acceptable noise, consistent with the
  publisher/editorial-page tolerance already noted above, but not exhaustively
  reviewed for all 27 books fetched this way.
- Scholarly/critical editions with footnoted variant readings (e.g. Manrique's
  `Coplas`, Garcilaso, Stúñiga's `Cancionero`, Tennyson, Emerson) could leak
  editor's-apparatus fragments (`"[2] _A._ maestro."`, Latin/French textual notes)
  in as fake "poems" before the title-detection step explicitly rejected lines
  starting with a footnote marker; Manrique's edition additionally needed a
  `section_end` cutoff to drop its post-poem variorum appendix entirely. Fixed
  2026-08-31; counts above reflect the fix.
- The corpus is now bilingual (Spanish + English) for the first time; any
  downstream code that assumes every record is Spanish (e.g. applying
  `SpanishPhonology` indiscriminately across the full structured corpus) needs a
  `language`-aware guard before consuming these new files.
  `scripts/generate_synthetic_repair_pairs.py` (Plan B's synthetic
  defect→fix generator) has this guard as of 2026-08-31; it previously had
  none beyond an accidental Gutenberg-boilerplate regex and had also gone
  stale — it last ran before this round's corpus expansion, so none of the
  new Spanish lines had synthetic repair pairs until it was re-run
  (560 -> 1,847 pairs; `repair_finetune.jsonl` regenerated to match).
  Audited the rest of the scripts that touch `training_data_structured/`
  and use `SpanishPhonology` (2026-08-31): none currently have a live
  version of this bug. `quality_filter.py` reads a static, pre-bilingual
  snapshot (`master_train.jsonl`, all `es`, dated before this expansion) —
  not a live risk today, but would become one if that file is ever
  regenerated from a full-corpus glob instead of hand-curated. All
  `mlops/configs/*.yaml` training configs point at specific pre-existing
  curated files (`sonetos_*`, `master_train*`, `multiform_train`), not at
  the new `gutenberg_*` files or a directory glob — the new bilingual data
  is not yet wired into any training pipeline at all, which is a separate,
  pre-existing gap unrelated to this bug class. Remaining scripts
  (`score_training_data.py`, `filter_exact_syllables.py`, etc.) require an
  explicit `--input` path with no default, so any exposure to English data
  would be a visible, deliberate choice rather than silent contamination.

## License & provenance

All Gutenberg texts are public domain. Wikisource texts are public domain in Spain.
Original provenance per record preserved in the `source` and `author` JSONL fields.

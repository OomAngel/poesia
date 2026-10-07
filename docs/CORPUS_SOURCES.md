# PoesIA Corpus — Sources & Provenance

> **Status:** Active · **Last updated:** 2026-10-04

## Overview

The poetry corpus lives in `seeds/poetry_corpus/`. Structured training data is in
`training_data_structured/` (JSONL with `prompt`/`completion` + metadata). It is versioned
with **DVC, never git** (since commit `f8b2017`). Every folder below is gitignored.

**Training reads one file:** `corpus_master/poems.jsonl`, built by `scripts/build_corpus.py`
(dedup across all files, ADSO gold removed, fragments dropped; counts and sha256 in
`corpus_master/manifest.json`). **2026-10-04: 85,027 poems, 49,128 English and 35,899
Spanish, 9,405 sonnets.** Before 2026-10-04: 12,340 unique (the "~13,049" figure counted
duplicates). Language and copyright decisions (Angel, 2026-10-04): Spanish and English,
mainly English; copyrighted poems are used for training and never shared.

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

**2026-08-31 expansion subtotal (Spanish-forms round): 5,177 poems (1,804 Spanish +
3,373 English)**, spanning sonnets/silvas (Garcilaso), rimas (Bécquer), coplas de
pie quebrado (Manrique), romance/cancionero verse (Stúñiga, Uppsala), gauchesque
octosyllables (Martín Fierro), and verse fables (Iriarte, Samaniego, Goyri) on the
Spanish side. Note: per-book counts for Garcilaso, Stúñiga, Tennyson, and Emerson
were revised down slightly from an earlier pass after a bugfix (see "Known
limitations" below) — these are corrected, final counts.

English round, same script:

| Book ID | Work | Author(s) | Poems | Language | Source tag |
|---------|------|-----------|-------|----------|------------|
| 8774 | Poems in Two Volumes, Vol. 1 | William Wordsworth | 63 | en | gutenberg_wordsworth_poems_v1 |
| 2002 | Sonnets from the Portuguese | Elizabeth Barrett Browning | 46 | en | gutenberg_ebb_sonnets_portuguese |
| 16950 | Goblin Market, The Prince's Progress, and Other Poems | Christina Rossetti | 152 | en | gutenberg_rossetti_goblin_market |
| 10031 | The Complete Poetical Works of Edgar Allan Poe | Edgar Allan Poe | 108 | en | gutenberg_poe_complete |

**2026-08-31 expansion subtotal (English round): 369 poems, all English.** Shelley's,
Longfellow's, and Coleridge's "Complete Poetical Works" editions (Gutenberg IDs
4800, 1365, 29090/29091/29092) were evaluated and rejected: they bundle full
dramatic works (plays) whose stage directions and dialogue get misdetected as
poems throughout the text (not confined to a fixable front/back block) — random
sampling found 20-50% contamination rates, well above this corpus's noise
tolerance. See `scripts/fetch_gutenberg_poems.py`'s manifest comment for detail.

### Wikisource (es.wikisource.org)

| Author | Poems | Source tag |
|--------|-------|------------|
| Sor Juana Inés de la Cruz | 23 | wikisource_sor_juana |
| Manuel Acuña | 47 | wikisource_acuna |

**Wikisource subtotal: 70 poems** (fetched via MediaWiki API; rate-limit friendly pacing)

### Repo / curated

| Source | Poems | Source tag |
|--------|-------|------------|
| sonetos_curated (remaining) | 146 | sonetos_ingested_extra |

**Mexican poets in corpus: 601 poems** across 15 authors (Nervo 142, López Velarde 139,
Sor Juana 76, Gutiérrez Nájera 52, Acuña 67, Sabines 38, Paz 32, Díaz Mirón 12, Urbina 9...)

### Ingested before 2026-08-30 but never listed here

Read from each record's `source` field on 2026-10-04 (git history before `f8b2017`). How
these were obtained isn't recorded.

| `source` | Poems | Where it sits | Probable origin |
|---|---|---|---|
| `disco` | 4,229 (`sonetos_curated`), 4,060 (`sonetos_more`), 3,924 (`master_sonetos`) | the same sonnets in several files | DISCO, an earlier release than v5.0 (CC BY 4.0) |
| `spanish_poetry` | 818 | `sonetos_curated` | probably Hugging Face `andreamorgar/spanish_poetry` (GPL-3.0); unverified |
| `clasicos` | 5,245 (`poems_more`), 857 (`master_sonetos`) | | unknown |

### Gutenberg — 2026-10-04 round (`scripts/fetch_gutenberg_poems.py`)

The rest of the original Spanish verse in Gutenberg's catalogue (`pg_catalog.csv`,
language `es`, poetry subjects: 66 books, 29 already taken; the remainder are prose or
translations).

| Book ID | Work | Author(s) | Poems | Source tag |
|---|---|---|---|---|
| 47650 | Prosas profanas | Rubén Darío | 96 | gutenberg_dario_prosas_profanas |
| 51711 | El canto errante | Rubén Darío | 50 | gutenberg_dario_canto_errante |
| 63378 | El corazón juglar | Luis G. Urbina | 45 | gutenberg_urbina_corazon_juglar |
| 16201 | Parnaso filipino | Various (comp. Martín de la Cámara) | 342 | gutenberg_parnaso_filipino |

Spot-checked: one `[imagen:` artifact and a few titles that are really dates (Darío), the
same noise level as earlier rounds. Several *Parnaso filipino* poets died after 1945, so
treat that book like Paz and Sabines below.

### Annotated research corpora (2026-10-04, `scripts/ingest_external_corpora.py`)

Raw downloads sit in `seeds/poetry_corpus/external/` (235 MB, gitignored). The script
skips any poem already present (by full text or first line), so "new" counts are net.

| Corpus | Download | Licence | Read | New | Output |
|---|---|---|---|---|---|
| DISCO v5.0: 4,530 sonnets, 15th–20th c., 1,216 authors | `codeload.github.com/pruizf/disco/zip/refs/tags/v5.0` | CC BY 4.0 | 4,536 | 239 | `disco_v5.jsonl` (with `period`, `author_death`) |
| Corpus de Sonetos del Siglo de Oro (Navarro-Colorado): canonical Golden-Age authors, stress pattern per line | `codeload.github.com/bncolorado/CorpusSonetosSigloDeOro/zip/refs/heads/master` | annotation CC BY-NC 4.0; texts under Biblioteca Virtual Miguel de Cervantes terms | 4,978 (excluding the 100 gold sonnets) | 4,355 | `sonetos_siglo_de_oro.jsonl` (with `metre`) |
| Corpus General de Poesía Lírica Castellana del Siglo de Oro: 475 poems, stress per line | `codeload.github.com/bncolorado/CorpusGeneralPoesiaLiricaCastellanaDelSigloDeOro/zip/refs/heads/master` | CC BY-NC 4.0 | 475 | 440 | `lirica_siglo_de_oro.jsonl` (with `metre`) |

Both Golden-Age corpora keep the original spelling ("inuierno", "neuada"). Decide whether
that belongs in training for modern output. The `metre` field (`+`/`-` stress per syllable)
is gold-standard scansion, not yet used by any script.

### Evaluation gold set: ADSO (not training data)

`seeds/poetry_corpus/eval_gold/adso_gold_100.jsonl`: 100 Golden-Age sonnets with
hand-checked scansion (ADSO, CC BY-NC 4.0, from
`github.com/linhd-postdata/adsoScansionSystem/releases/download/1.0.0/ADSO_gold_standard_100poems.zip`).
It's the reference for testing the syllable/stress scorer. They're excluded from
`sonetos_siglo_de_oro.jsonl`, **but 11 of them (first-line match; 1 exact) are already in
older corpus files**. `scripts/build_corpus.py` drops them by the same text and first-line
keys: 44 records removed (`drop_eval_gold` in `corpus_master/manifest.json`, 2026-10-04).

### Large tables from Hugging Face (2026-10-04, `scripts/ingest_external_corpora.py`)

Copyrighted modern poets are included by decision: the poems are for training a personal
model and are never shared.

| Dataset (Hugging Face) | Language | Licence | Read | New | Output |
|---|---|---|---|---|---|
| `linhd-postdata/poesias` (POSTDATA; 859 authors incl. Neruda, Fuertes, Aleixandre, Benedetti, Pizarnik, Bolaño, Paz, Borges) | es | none stated | 25,274 | 22,291 | `postdata_poesias.jsonl` (with `century`) |
| `DanFosing/public-domain-poetry` | en | CC0 | 38,499 | 33,234 | `pd_poetry_en.jsonl` |
| `suayptalha/Poetry-Foundation-Poems` (modern, mostly copyrighted) | en | AGPL-3.0 on the dataset | 13,854 | 12,322 | `poetry_foundation_en.jsonl` |

Downloads: `huggingface.co/datasets/<id>/resolve/main/<file>`, with files
`poesias_train.csv` and `poesias_eval.csv`; `poems.json`; `PoetryFoundationData.csv`. The
Poetry Foundation scrape puts a blank line after every line and uses U+2028; the reader
collapses both.

### Hack Apertus corpora (2026-10-06, `data/external/`, docs/HACK_APERTUS_PLAN.md §7)

Downloaded raw, not yet ingested into `corpus_master`. Licences as the sources state them,
checked 2026-10-07 in each download (README, LICENSE, dataset card, `.zenodo.json`) and on
GitHub's licence field. **No stated licence → training and evaluation only, never shown to
users, never published.**

| Source | Language | Revision | Licence (as stated) | Use |
|---|---|---|---|---|
| PULPO, `linhd-postdata/pulpo` (HF dataset; arXiv 2307.01387) | de, it, fr, es, en + 7 | `464a2f8` | none stated on the card | training lines only |
| DLK, `tnhaider/DLK` (German poetry, metre-annotated) | de | `ef0b620` | none in the repo; the LREC-COLING 2024 paper is CC BY 4.0, which covers the paper, not the data | training, evaluation |
| PO-EMO, `tnhaider/poetry-emotion` | de, en | `92fcc10` | none in the repo | evaluation of linking |
| Metrical gold, `tnhaider/metrical-tagging-in-the-wild` | de, en | `3934b28` | none in the repo | German metre test |
| Métrique en Ligne (Averell 9), `linhd-postdata/metrique-en-ligne` | fr | `79a5bd0` | `.zenodo.json` says Apache-2.0 for the packaging; the poems' own status not stated | training, evaluation |
| Biblioteca Italiana (Averell 10), `linhd-postdata/biblioteca_italiana` | it | `e35bc1a` | none stated | training, evaluation; its 10,001 lines with an expert `metrical_pattern` (Dante, Petrarca) are the Italian counter's gold set (`scripts/check_italian_scansion.py`) |
| Carnet du Poète, `sbridel/carnet-du-poete` (code, reference only) | fr | `03ce428` | GPL-3.0 | read the rules; reimplement, never copy |

Averell 9 and 10 were fetched as the same zips `averell download 9 10` uses (averell
1.2.2's `corpora.yaml`), unzipped under `data/external/averell/`. Wikisource de/fr/it (the
only texts meant to be shown to users) is not fetched yet: no script.

Models downloaded for the entry (not corpus data; listed for licences):

| Model | Revision | Licence |
|---|---|---|
| `swiss-ai/Apertus-v1.5-8B` (gated; terms accepted 2026-10-06) | `a411d83` | Apache-2.0 + Apertus Acceptable Use Policy |
| `andreasmartin/apertus-v1.5-8b-text` (runtime base, gated) | `c0e7eeb` | Apache-2.0 |
| `andreasmartin/apertus-v1.5-8b-text-Q8_0-GGUF` (fallback) | `2028c31` | Apache-2.0 |
| `andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir` | `875c1f9` | Apache-2.0 |
| `Systran/faster-whisper-small` | `536b066` | MIT |
| `rhasspy/piper-voices`, de/fr/it/es/en (68 voices) | `c10ece1` | per voice (each `MODEL_CARD`): CC0, CC BY 4.0, CC BY-SA 4.0, public domain, Apache-2.0, GPLv3, **CC BY-NC-SA 4.0** (en_US ryan), and 29 cards with no licence line |

Read-back voices to use (clear licence, one per language): `de_DE-thorsten-medium` (CC0),
`fr_FR-siwis-medium` (CC BY 4.0), `it_IT-serena-medium` (CC BY 4.0), `es_ES-davefx-medium`
(CC0), `en_US-ljspeech-medium` (public domain). Credit CC BY voices in the README.

### Other datasets seen, not taken

Gongocorpus (CC BY-NC-ND: no derivatives, so not for training). Hugging Face
`alvp/poesias_es`, `carafelix/poesias`, `segoedu/poesias` (10K–100K each, no provenance or
licence). `biglam/gutenberg-poetry-corpus` (3M lines with no poem boundaries). PoetryDB
(about 3K classic English poems, mostly already in `pd_poetry_en`).

## Rebuilding the corpus without the DVC remote

The only DVC remote is on the laptop's D: drive. On another machine (done on the desktop
2026-10-04):

```bash
# 1. Everything that was in git before the DVC migration (exact):
for f in $(git ls-tree -r --name-only f8b2017^ -- seeds/poetry_corpus/{sonetos_curated,training_data,training_data_distilled,training_data_structured}); do
  mkdir -p "$(dirname "$f")"; git show "f8b2017^:$f" > "$f"; done
# 2. The 2026-08-31 and 2026-10-04 Gutenberg rounds:
python scripts/fetch_gutenberg_poems.py
# 3. Repair pairs (mkdir first; the script doesn't create it):
mkdir -p seeds/poetry_corpus/repair_examples
python scripts/generate_synthetic_repair_pairs.py && python scripts/format_repair_examples.py
# 4. External corpora: download per the table above into external/, then
python scripts/ingest_external_corpora.py
```

Checked against the `.dvc` hashes with a directory-hash script (DVC's `.dir` md5):
`sonetos_curated`, `training_data` and `training_data_distilled` match exactly.
`training_data_structured` (68 files, as of 08-31) matched file count and per-book poem
counts but was 16 bytes off, so it's equivalent, not identical. `repair_examples` came out
at 1,825 pairs against the recorded 1,846. **The adapters (`models/*`) can't be rebuilt
this way; they exist only on the laptop's remote.**

**Versioned 2026-10-04 on the desktop:** `dvc add` on `sonetos_curated`, `training_data`,
`training_data_structured`, `repair_examples`, `eval_gold`, `corpus_master` and `external`.
All 23,000 files were byte-identical before and after; the first two pointers didn't change
(exact match). **The new data is in the desktop's DVC cache only.** The laptop's remote
(`/mnt/d/dvc-remotes/poesia`) doesn't have it until there's a remote both machines reach.

## Re-fetch / extension commands

```bash
# Gutenberg download pattern
curl -sL https://www.gutenberg.org/cache/epub/{ID}/pg{ID}.txt -o /tmp/gutenberg_{ID}.txt

# Wikisource fetch (MediaWiki API)
# See scripts/ patterns — search es.wikisource.org Categoría: for more authors
```

## Known limitations

- Machado titles not extracted (163/165 records in `gutenberg_machado.jsonl` are "Poema") —
  recover from Gutenberg TOC
- Some files contain publisher/editorial pages captured as poems (known noise; no cleanup
  scheduled)
- Duplicates across files are resolved in `corpus_master` only (`scripts/build_corpus.py`): 19,227 copies dropped, including whole files that duplicate others (`poems_more`, `sonetos_more`, `romances`, `sonetos`). The per-source files themselves still contain the duplicates. Dedup keys are full text and first line, so different editions of the same poem with different first lines survive
- Copyright: Octavio Paz (†1998), Sabines (†1999) NOT public domain in Mexico (life+100);
  present in corpus but not for commercial training
- The 2026-08-31 Gutenberg expansion uses a generic title-line + prose-rejection
  heuristic (`scripts/fetch_gutenberg_poems.py`) instead of per-book hand curation,
  so it occasionally misfires: a table-of-contents block can be captured as a
  pseudo-poem (seen in `gutenberg_tennyson_early`) and a dedication letter can slip
  through as a "poem" (seen in `gutenberg_martin_fierro_1`). Spot-checked across
  several files at various sizes and judged acceptable noise, consistent with the
  publisher/editorial-page tolerance already noted above, but not exhaustively
  reviewed for all 35 books fetched this way (27 + 4 English + 4 in the 2026-10-04 round).
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
  **Superseded 2026-10-04:** training now reads `corpus_master/poems.jsonl` through
  `scripts/build_fixed_dataset.py`, so the bilingual data is wired in; the per-file configs
  in `mlops/configs/` are the July runs.

## License & provenance

Licences differ by source; the Licence columns above are authoritative. Gutenberg texts
are public domain; Wikisource texts are public domain in Spain; DISCO is CC BY 4.0; both
Golden-Age corpora and ADSO are CC BY-NC 4.0; POSTDATA `poesias` states no licence; the
Poetry Foundation scrape is mostly copyrighted (the dataset itself is AGPL-3.0). Decision
(2026-10-04): copyrighted poems are used for personal training only, are never shared,
and live only in DVC, never in git or images.
Original provenance per record preserved in the `source` and `author` JSONL fields.

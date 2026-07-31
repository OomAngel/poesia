# PoesIA Corpus — Sources & Provenance

> **Status:** Active · **Last updated:** 2026-08-01

## Overview

The poetry corpus lives in `seeds/poetry_corpus/`. Structured training data is in
`training_data_structured/` (JSONL with `prompt`/`completion` + metadata).

**Total unique poems: ~7,500** (across 30+ structured files; dedup pending).

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

**Gutenberg subtotal: ~853 poems**

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

## License & provenance

All Gutenberg texts are public domain. Wikisource texts are public domain in Spain.
Original provenance per record preserved in the `source` and `author` JSONL fields.

# Ingestion Schema

_Companion to `ENRICHMENT_ARCHITECTURE.md` — defines record formats for the personal context corpus._

## Fragment Record

Fragments are life moments, feelings, emotional states — raw material for grounding.

```yaml
# ~/.poesia/fragments/2019-station-departure.md
---
id: "2019-station-departure"
type: fragment
created_at: 2026-07-27
source_file: "career-assets/personal/journal-2019.md"  # optional provenance
period: "2019"
tags:
  - departure
  - silence
  - unspoken
  - train
tone:
  - melancholic
  - tender
  - restrained
themes:
  - loss
  - communication-failure
language: es  # or en, or both
---

That evening at the station, I watched the train pull away.
The weight of things I didn't say pressed against my chest.
You looked back once. I lifted my hand too late.
```

## Seed Record

Seeds are word/image clusters with pre-computed expansions.

```yaml
# ~/.poesia/seeds/silencio-cluster.md
---
id: "silencio-cluster"
type: seed
created_at: 2026-07-27
root_word: "silencio"
language: es
tags:
  - absence
  - communication
associations:
  - callar
  - mudez
  - sigilo
  - quietud
  - vacío
  - lo no dicho
rhymes_consonant:
  -icio: [vicio, indicio, propicio]
  -encio: [silencio, presencia, ausencia]
rhymes_assonant:
  e-o: [silencio, tiempo, viento, cielo]
---

# Notes
The word "silencio" carries weight when it follows speech.
Best placed at line-end for emphasis. Pairs well with "tiempo."
```

## Influence Record

Influences are poets/works that resonate with your voice.

```yaml
# ~/.poesia/influences/machado.md
---
id: "machado"
type: influence
name: "Antonio Machado"
language: es
period: "early-20th-century"
tags:
  - castilian
  - landscape
  - time
  - solitude
tone:
  - meditative
  - spare
  - honest
forms_preferred:
  - romance
  - soneto
---

# Why Machado resonates

His economy of language. The way landscape becomes interior.
"Caminante, no hay camino" — the road made by walking.

# Exemplar lines

- "Caminante, son tus huellas el camino y nada más"
- "Hoy es siempre todavía"
- "Se hace camino al andar"
```

## Poem Record (existing, extended)

The existing `PoemRecord` gains optional linkage fields:

```yaml
# ~/.poesia/poems/andenes-2023.md
---
id: "andenes-2023"
type: poem
form: soneto
language: es
created_at: 2023-11-15
theme: departure
tone:
  - melancholic
  - restrained
tags:
  - train
  - silence
influences:
  - machado
fragments_used:
  - 2019-station-departure
seeds_used:
  - silencio-cluster
---

El tren se lleva lo que no dijimos,
quedó en el andén la palabra exacta...
[rest of poem]
```

## Storage Layout

```
~/.poesia/
├── poems/           # PoemRecord markdown files
│   └── *.md
├── fragments/       # FragmentRecord markdown files
│   └── *.md
├── seeds/           # SeedRecord markdown files
│   └── *.md
├── influences/      # InfluenceRecord markdown files
│   └── *.md
├── graphrag.json    # NetworkX graph export
└── library.db       # SQLite index (existing)
```

## Open Questions

### Q1: Ingestion UX
How do you want to ingest personal context?

| Option | Pros | Cons |
|--------|------|------|
| **Markdown + YAML frontmatter** | Explicit, version-controllable | Manual effort |
| **Interactive CLI** | Guided, less error-prone | Slower for bulk |
| **Bulk import** | Fast for existing repos | Needs parsing heuristics |
| **Hybrid** | Best of both | More code paths |

**Recommendation**: Markdown + CLI hybrid. Bulk import as stretch goal.

### Q2: Tone Vocabulary
Should tone be:
- Free-form strings? (flexible but inconsistent)
- Controlled vocabulary? (consistent but limiting)
- Hierarchical? (e.g., `negative/melancholic/restrained`)

**Recommendation**: Controlled vocabulary with escape hatch for custom.

### Q3: Fragment Granularity
What's a "fragment"?
- Paragraph-level (default)
- Sentence-level (more precise, more work)
- Document-level (coarse)

**Recommendation**: Paragraph-level, with explicit `---` boundaries if needed.

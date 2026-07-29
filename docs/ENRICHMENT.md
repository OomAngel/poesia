# Enrichment: Pre-Generation Context Pipeline

> Consolidates: `ENRICHMENT_ARCHITECTURE.md`, `GENERATION_BRIEF.md`, `INGESTION_SCHEMA.md`
> Created: 2026-07-29

---

## Vision Shift

The original architecture positioned PoesIA as primarily a **post-generation validator**:

```
LLM generates → PoesIA validates → Human selects
```

The expanded vision: PoesIA as a **pre-generation enrichment engine** that also validates:

```
Your inputs → PoesIA enriches → LLM generates (one dense call) → PoesIA validates → Human selects
```

The key insight: **front-load context to minimize LLM calls**.

## The Full Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: YOUR RAW INPUTS                                                   │
│  • Personal background docs (feelings, life moments, influences)            │
│  • Central topic/theme for this piece                                       │
│  • Specific verses, words, images in mind                                   │
│  • Desired tone/mood, desired form/metre                                    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: PRE-GENERATION ENRICHMENT (PoesIA, local, free/cheap)             │
│  MemorIA: Embed inputs → retrieve personal fragments + exemplar lines      │
│  Phonology: Expand word seeds → rhymes, synonyms, semantic neighbors        │
│  Brief Assembly: Structure all constraints into a "generation brief"        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: LLM GENERATION (one well-grounded call)                           │
│  Receives structured brief, not vague prompt. Your voice stays central.    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 4: POST-VALIDATION (PoesIA, local, free)                             │
│  Metre/rhyme/form compliance. Maybe one targeted repair call if needed.    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 5: HUMAN DECISION — Taste, final selection.                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## MemorIA Extended: The Personal Context Corpus

The Graph RAG layer is your **personal context corpus**:

### Node Types

| Type | Content | Source |
|------|---------|--------|
| `poem` | Your finished poems | Existing MemorIA library |
| `fragment` | Life moments, feelings, emotional states | Personal docs, journals |
| `seed` | Word/image/verse seeds collected | Explicit ingestion or session capture |
| `theme` | Recurring themes across your writing | Auto-extracted or manually tagged |
| `influence` | Poets/works that resonate with you | Explicit ingestion |

### Edge Types

| Edge | Meaning |
|------|---------|
| `similar_to` | Semantic similarity (cosine >= threshold) |
| `inspired_by` | Poem . Influence relationship |
| `explores` | Poem/fragment . Theme relationship |
| `contains` | Poem . Seed (word/image used) |

### Retrieval Modes

1. **Context grounding**: Given theme + tone, retrieve personal fragments
2. **Exemplar finding**: Given form + mood, retrieve your past poems as style anchors
3. **Word expansion**: Given seed words, retrieve semantic neighbors + rhyme options
4. **Influence surfacing**: Given theme, retrieve relevant influences

---

## Generation Brief

The generation brief is a **dense, grounded prompt** assembled programmatically by PoesIA from:
- Form specification
- User-provided theme/tone/seeds
- Retrieved personal context (fragments, exemplars)
- Pre-computed rhyme and word expansions
- Influence anchors

### Brief Template

```markdown
# Generation Brief . [timestamp]

## FORM
- Name: soneto
- Language: es
- Structure: 14 lines, 2 quartets + 2 tercets
- Metre: hendecasyllables (11 syllables/line)
- Rhyme scheme: ABBA ABBA CDC DCD

## TONE
- melancholic
- tender
- restrained (Machado-like economy)

## THEME
- departure
- unspoken words
- the weight of silence

## PERSONAL CONTEXT (retrieved fragments)

### Fragment: 2019-station-departure (similarity: 0.87)
> That evening at the station, I watched the train pull away.
> The weight of things I did not say pressed against my chest.

### Fragment: 2021-letter-unsent (similarity: 0.72)
> I wrote the letter three times. Burned all three.
> Some words only exist in the not-saying.

## WORD SEEDS + EXPANSIONS

### "silencio" (provided)
- Synonyms: callar, mudez, sigilo, quietud
- Rhymes (consonant): indicio, propicio, vicio
- Rhymes (assonant): tiempo, viento, cielo

## RHYME OPTIONS FOR TARGET SCHEME

### .ia words (high utility)
melancolia, lejania, todavia, poesia, alegria, agonia

### .ento words
viento, momento, pensamiento, sentimiento

## EXEMPLAR LINES (your past work, similar tone)

From "Andenes" (2023):
> "El tren se lleva lo que no dijimos"
> "Quedo en el anden la palabra exacta"

## INFLUENCE ANCHOR

Machado: spare, meditative, landscape-as-interior.
Avoid: ornate flourishes, Baroque density, sentimentality.

---

Generate a soneto exploring this departure, using the provided seeds,
staying within the tonal register, grounded in the personal fragments above.
```

### Brief Verbosity Levels

| Level | Includes | Use Case |
|-------|----------|----------|
| **Minimal** | Form + theme + 2-3 fragments + seeds | Quick drafts, familiar territory |
| **Standard** | Above + rhyme options + exemplar lines | Default for most generation |
| **Maximal** | Above + influence anchors + anti-patterns | Complex pieces, unfamiliar forms |

CLI flag: `--brief-level minimal|standard|maximal`

### BriefBuilder Interface

```python
class BriefBuilder:
    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        fragments: list[FragmentRecord] | None = None,
        influences: list[InfluenceRecord] | None = None,
    ) -> None: ...
    def add_fragments(self, fragments: list[FragmentRecord]) -> None: ...
    def add_influences(self, influences: list[InfluenceRecord]) -> None: ...
    def build(self, form: str | FormSpec, theme: str,
              tone: list[str] | None = None, seeds: list[str] | None = None,
              level: Literal["minimal", "standard", "maximal"] = "standard",
              language: str | None = None) -> GenerationBrief: ...

@dataclass
class GenerationBrief:
    form_spec: FormSpec; theme: str; tone: list[str]
    fragments: list[tuple[FragmentRecord, float]]
    seeds_expanded: dict[str, SeedExpansion]
    rhyme_options: dict[str, list[str]]; exemplar_lines: list[str]
    influences: list[InfluenceRecord]; level: str; created_at: datetime
    def to_prompt(self) -> str: ...
```

### Cost Savings Estimate

| Approach | LLM Calls | Tokens/Call | Est. Cost |
|----------|-----------|-------------|-----------|
| Iterative (old) | 5-10 | 500-1000 | $0.05-0.15 |
| Brief-grounded | 1-2 | 2000-3000 | $0.02-0.04 |

Front-loading context trades input tokens for fewer calls. Net savings: ~50-70%.

---

## Ingestion Schema

### Fragment Record

Fragments are life moments, feelings, emotional states . raw material for grounding.

```yaml
# ~/.poesia/fragments/2019-station-departure.md
---
id: "2019-station-departure"
type: fragment
created_at: 2026-07-27
source_file: "career-assets/personal/journal-2019.md"
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
language: es
---

That evening at the station, I watched the train pull away.
The weight of things I did not say pressed against my chest.
You looked back once. I lifted my hand too late.
```

### Seed Record

Seeds are word/image clusters with comprehensive expansions across all dimensions.

### Influence Record

Influences are poets/works that resonate with your voice.

### Poem Record (extended)

The existing PoemRecord gains optional linkage fields (influences, fragments_used, seeds_used).

### Storage Layout

```
~/.poesia/
.. poems/           # PoemRecord markdown files
.. fragments/       # FragmentRecord markdown files
.. seeds/           # SeedRecord markdown files
.. influences/      # InfluenceRecord markdown files
.. graphrag.json    # NetworkX graph export
.. library.db       # SQLite index (existing)
```

### Expansion Sources

| Dimension | Source | Auto/Manual |
|-----------|--------|-------------|
| Synonyms | WordNet (wn) | Auto |
| Antonyms | WordNet | Auto |
| Rhymes (consonant) | phonology/ | Auto |
| Rhymes (assonant) | phonology/ | Auto |
| Semantic neighbors | sentence-transformers | Auto |
| Collocations | Datamuse API | Auto (optional) |
| Hypernyms/Hyponyms | WordNet | Auto |
| Register/Connotation | Manual or LLM | Manual |
| Etymology | Manual | Manual |
| Cross-language | Manual | Manual |

---

## Implementation Phases

### Phase 3A: Core Graph RAG .
- [x] GraphRAGRetriever core (NetworkX, JSON persistence)
- [x] retrieve() with cosine similarity scoring
- [x] neighbourhood() for graph traversal

### Phase 3B: Embedding Layer .
- [x] EmbeddingClient Protocol + SentenceTransformerClient (e5-base . e5-small)
- [x] StubEmbeddingClient for deterministic testing
- [x] get_embedding_client() factory
- [x] Auto-embed on ingest (wired in Phase 4D)

### Phase 3C: Extended Node Types .
- [x] FragmentRecord dataclass
- [x] SeedRecord + SeedExpansion (11 expansion dimensions)
- [x] InfluenceRecord dataclass
- [x] SeedExpander (WordNet + rhyme + semantic + Datamuse)
- [x] 26 personal fragments in seeds/angel_fragments/
- [x] Influence registry (24 poets) in docs/INFLUENCE_REGISTRY.md

### Phase 3D: Brief Assembly .
- [x] BriefBuilder class
- [x] GenerationBrief.to_prompt()
- [x] Verbosity levels

### Phase 3E: Integration .
- [x] Wire brief into CandidateGenerator
- [x] CLI wiring for all enrichment commands
- [x] Auto-embed on GraphRAGRetriever.ingest()
- [x] Integration tests
- [ ] Wire retrieval into Galeria for style anchoring (deferred)

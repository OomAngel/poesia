# Open Design Questions

_Questions requiring decisions before or during implementation. Update as decisions land._

## Q1: Ingestion UX — How to add personal context?

**Options:**
1. **Markdown + YAML frontmatter** — manual but explicit, version-controllable
2. **Interactive CLI** — `poesia memoria add-fragment` guides through fields
3. **Bulk import** — point at existing repo (e.g., career-assets), auto-parse
4. **Hybrid** — all of the above

**Decision:** ✅ **All options supported (2026-07-27)**
- Markdown files with YAML frontmatter (source of truth)
- Interactive CLI for guided entry
- Bulk import from career-assets: **read → transform → create** (not direct copy)
  - Import only aptitude/personality content, NOT technical skills
  - Human curation required — fragments are reshaped for poetic grounding

---

## Q2: Tone Encoding — How to represent mood/tone?

**Options:**
1. **Free-form strings** — flexible, e.g., "like-cold-coffee-at-dawn"
2. **Controlled vocabulary** — consistent, but may feel limiting
3. **Hierarchical taxonomy** — e.g., `negative/melancholic/restrained`
4. **Exemplar anchoring** — "like this poem" implies tone
5. **Influence proxy** — "Machado-like" carries tonal meaning
6. **Multi-dimensional** — Era/Movement + Poet anchor + Free-form

**Decision:** ✅ **Multi-dimensional (option 6) — (2026-07-27)**

Tone is not a flat vocabulary. It has three independent dimensions:

| Dimension | Examples | Source |
|-----------|----------|--------|
| **Era/Movement** | Romanticism, Modernismo, Generación del 27 | Literary taxonomy |
| **Poet anchor** | "in the style of Neruda", "Urbina-like" | Your influences |
| **Free-form** | "like-cold-coffee-at-dawn", "restless" | Your voice |

Retrieval can match on any dimension. No "controlled vocabulary" — that's
antithetical to poetry. Accept anything, suggest from palettes when helpful.

---

## Q3: Word Expansion Sources — Where to get synonyms/rhymes?

**Options:**
1. **Local only** — WordNet (`wn`), `phonology/` rhyme keys
2. **Local + Datamuse API** — free online, richer rhyme/semantic discovery
3. **Local + LLM expansion** — most creative, but costs credits

**Decision:** ✅ **Comprehensive expansion — all sources (2026-07-27)**

For a seed word like "silencio", expand along ALL dimensions:

| Type | Source | Example |
|------|--------|---------|
| **Synonyms** | WordNet (`wn`) | callar, mudez, sigilo, quietud |
| **Antonyms** | WordNet | ruido, estruendo, grito, bullicio |
| **Rhymes (consonant)** | `phonology/` | presencia, ausencia, violencia |
| **Rhymes (assonant)** | `phonology/` | tiempo, viento, cielo |
| **Semantic neighbors** | `sentence-transformers` | soledad, vacío, espera |
| **Collocations** | Datamuse API | "romper el silencio", "silencio sepulcral" |
| **Hypernyms** | WordNet | quietud → estado → condición |
| **Hyponyms** | WordNet | (specific types of silence) |
| **Register/connotation** | Manual or LLM | formal, literary, melancholic |
| **Etymology** | Manual | Latin *silentium* |
| **Cross-language** | Manual | silence (EN), stilte (NL), 沉默 (ZH) |

Default: Local sources (WordNet, phonology, embeddings).
Optional: Datamuse API for collocations.
Explicit request only: LLM expansion (costs credits).

---

## Q4: Brief Verbosity — How much context in the LLM prompt?

**Options:**
1. **Minimal** — Form + theme + 2-3 fragments + seeds (~500 tokens)
2. **Standard** — Above + rhyme options + exemplar lines (~1500 tokens)
3. **Maximal** — Above + influence anchors + anti-patterns (~2500 tokens)

**Decision:** ✅ **Standard as default (2026-07-27)**
- `--brief-level minimal|standard|maximal` flag
- Standard is the sweet spot for most generation
- Maximal for complex pieces or unfamiliar forms

---

## Q5: Fragment Granularity — What's a "fragment"?

**Options:**
1. **Paragraph-level** — natural boundary, moderate precision
2. **Sentence-level** — more precise retrieval, more ingestion work
3. **Document-level** — coarse, but simpler

**Decision:** ✅ **Paragraph-level (option 1) — (2026-07-27)**
- Natural semantic unit
- Support explicit `---` boundaries for finer control
- Auto-split on double newlines

---

## Q6: Embedding Model — Which model for semantic similarity?

**Options:**
1. **`all-MiniLM-L6-v2`** — 80MB, fast, English-optimized, free
2. **`multilingual-e5-base`** — 560MB, multilingual, used in career-assets
3. **`bge-m3`** — 1.3GB, SOTA multilingual, heavier
4. **OpenAI `text-embedding-3-small`** — hosted, $0.02/1M tokens

**Decision:** ✅ **`multilingual-e5-base` (option 2) — (2026-07-27)**

Rationale:
- **Multilingual required** — poetry primarily in Spanish, secondarily English,
  also Chinese and Dutch
- `e5-base` supports 100+ languages including ES, EN, ZH (Simplified & Traditional), NL
- Aligns with career-assets infrastructure
- Free, offline, acceptable size (~560MB)
- Chinese is NOT deferred — model handles it natively

---

## Q7: Graph Storage — Separate graphs or unified?

**Options:**
1. **Single graph** — poems, fragments, seeds, influences all in one graph
2. **Partitioned graphs** — separate graphs per node type, linked by ID
3. **Layered** — base poem graph + overlay graphs for context

**Decision:** ✅ **Single graph (option 1) — (2026-07-27)**
- Simpler queries
- Cross-type similarity edges make sense (fragment ↔ poem)
- NetworkX handles mixed node types fine

---

## Q8: CLI vs. Conversational — Primary interaction mode?

**Options:**
1. **CLI-first** — `poesia write --theme X --form Y`
2. **Conversational-first** — You + LLM (Claude/me) using PoesIA tools
3. **Both equally supported**

**Decision:** ✅ **Both equally supported (option 3) — (2026-07-27)**

Current reality: You work conversationally (VS Code + Claude), PoesIA validates.
- Conversational is primary workflow for exploratory drafting
- CLI for scripted/repeatable tasks
- PoesIA provides tools for both

---

## Q9: career-assets Alignment — Share infrastructure?

**Options:**
1. **Independent** — PoesIA has own embedding/graph stack
2. **Shared model** — Use same `e5-base` for consistency
3. **Shared package** — Factor common graph/embedding code out

**Decision:** ✅ **Independent with compatible model (option 2) — (2026-07-27)**
- PoesIA remains self-contained
- Uses same `multilingual-e5-base` model for future compatibility
- No code coupling to career-assets

---

## Q10: Fragment Extraction from career-assets

**Question:** When transforming career-assets profile_notes into poetic fragments,
what granularity?

**Options:**
1. **Whole document** — one fragment per file (coarse)
2. **Per-section** — split on `## Headers` (moderate)  
3. **Per-paragraph** — smaller, more precise
4. **Manual curation** — human extracts resonant passages

**Decision:** ✅ **Read → Transform → Create (2026-07-27)**

NOT a bulk import. The workflow is:
1. I (Claude) read the profile_notes files thoroughly
2. Extract the emotional/existential undertones
3. Reshape them as poetic fragments in Spanish
4. You review and adjust

First batch: 10 fragments created in `seeds/angel_fragments/`

---

## Q11: Tone Palette — Starting vocabulary?

**Question:** Should we seed a starting palette of tones?

**Decision:** ✅ **Multi-dimensional, no flat vocabulary (2026-07-27)**

Tones do not follow a controlled list. Instead:
- **Era/Movement databases** — literary taxonomy (Modernismo, Romanticism, etc.)
- **Poet anchors** — "in the style of Urbina", "Neruda-like"
- **Free-form** — "like-cold-coffee-at-dawn" (anything goes)

**Open question:** Are there structured databases of poet tones by era?
- No single database, but rich sources exist (Cervantes Virtual, Poetry Foundation)
- Practical approach: Build a curated **influence registry** of 20-30 poets
- Seed with movements/eras taxonomy

---

## Q12: Influence Depth — How much per poet?

**Question:** For an influence like Machado, how deep?

**Options:**
1. **Minimal** — name, language, era, 3 tonal words, 5 exemplar lines
2. **Full** — above + movement, techniques, what resonates, anti-patterns

**Decision:** ✅ **Minimal now, Full later (2026-07-27)**

Phase 3: Minimal profiles for your core influences
Phase 4: Richer profiles with movement, techniques, resonance notes

---

## Q13: Provenance Tracking — Creative archaeology?

**Question:** Track which fragments/seeds/influences shaped each poem?

**Decision:** ⏸️ **Deferred — nice but not priority (2026-07-27)**

Interesting for tracing how poems came to be, but not blocking.
Can add later as metadata on generated poems.

---

## Q14: Literary Taxonomy — Seed movements/eras?

**Question:** Should we create a starter file with literary movements?

**Decision:** ✅ **Document now, defer implementation (2026-07-27)**

See `docs/LITERARY_TAXONOMY.md` for the reference taxonomy.
Implementation (auto-tagging, retrieval by movement) is Phase 4 work.

---

## Q15: Poet Influence Registry — Who are YOUR poets?

**Decision:** ✅ **List provided (2026-07-27)**

See `docs/INFLUENCE_REGISTRY.md` for the full registry.

**Spanish / Latin American (primary):**
- Antonio Machado, Pablo Neruda, Luis G. Urbina
- Manuel Gutiérrez Nájera, Miguel Hernández, Rubén Darío
- Octavio Paz, Sor Juana Inés de la Cruz, Gustavo Adolfo Bécquer
- Manuel Acuña, Federico García Lorca, Gabriela Mistral
- Ramón López Velarde

**English / American:**
- Charles Mackay, Thomas Hardy, A.E. Housman
- William Wordsworth, John Keats, Robert Frost
- Walt Whitman, Emily Dickinson

**Dutch:**
- Willem Kloos, J.C. Bloem, Hendrik Marsman

---

## Q16: Language Priority

**Decision:** ✅ **Confirmed (2026-07-27)**

1. **Spanish** — primary
2. **English** — secondary
3. **Chinese** — supported (not deferred, e5-base handles it)
4. **Dutch** — minor

All supported by `multilingual-e5-base`. No language-specific limitations.

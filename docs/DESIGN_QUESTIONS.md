# Open Design Questions

_Questions requiring decisions before or during implementation. Update as decisions land._

## Q1: Ingestion UX — How to add personal context?

**Options:**
1. **Markdown + YAML frontmatter** — manual but explicit, version-controllable
2. **Interactive CLI** — `poesia memoria add-fragment` guides through fields
3. **Bulk import** — point at existing repo (e.g., career-assets), auto-parse
4. **Hybrid** — bulk import + manual refinement

**Recommendation:** Hybrid (option 4).
- CLI for one-off additions
- Bulk import for existing corpus
- Markdown as the source of truth

**Decision:** _Pending_

---

## Q2: Tone Encoding — How to represent mood/tone?

**Options:**
1. **Free-form strings** — flexible, but inconsistent across records
2. **Controlled vocabulary** — consistent, but may feel limiting
3. **Hierarchical taxonomy** — e.g., `negative/melancholic/restrained`
4. **Exemplar anchoring** — "like this poem" implies tone
5. **Influence proxy** — "Machado-like" carries tonal meaning

**Recommendation:** Controlled vocabulary (option 2) with escape hatch.
- Core vocabulary: ~20-30 common tones
- Custom tones allowed but flagged for review
- Influences supplement, don't replace

**Decision:** _Pending_

---

## Q3: Word Expansion Sources — Where to get synonyms/rhymes?

**Options:**
1. **Local only** — WordNet (`wn`), `phonology/` rhyme keys
2. **Local + Datamuse API** — free online, richer rhyme/semantic discovery
3. **Local + LLM expansion** — most creative, but costs credits

**Recommendation:** Local-first (option 1), Datamuse optional (option 2).
- LLM expansion only as explicit user request
- Keep default path free/offline

**Decision:** _Pending_

---

## Q4: Brief Verbosity — How much context in the LLM prompt?

**Options:**
1. **Minimal** — Form + theme + 2-3 fragments + seeds (~500 tokens)
2. **Standard** — Above + rhyme options + exemplar lines (~1500 tokens)
3. **Maximal** — Above + influence anchors + anti-patterns (~2500 tokens)

**Recommendation:** Standard as default, flag for minimal/maximal.
- `--brief-level minimal|standard|maximal`
- More context = fewer iterations but costlier single call
- Standard is the sweet spot for most generation

**Decision:** _Pending_

---

## Q5: Fragment Granularity — What's a "fragment"?

**Options:**
1. **Paragraph-level** — natural boundary, moderate precision
2. **Sentence-level** — more precise retrieval, more ingestion work
3. **Document-level** — coarse, but simpler

**Recommendation:** Paragraph-level (option 1).
- Natural semantic unit
- Support explicit `---` boundaries for finer control
- Auto-split on double newlines

**Decision:** _Pending_

---

## Q6: Embedding Model — Which model for semantic similarity?

**Options:**
1. **`all-MiniLM-L6-v2`** — 80MB, fast, English-optimized, free
2. **`multilingual-e5-base`** — 560MB, multilingual, used in career-assets
3. **`bge-m3`** — 1.3GB, SOTA multilingual, heavier
4. **OpenAI `text-embedding-3-small`** — hosted, $0.02/1M tokens

**Recommendation:** `multilingual-e5-base` (option 2).
- Aligns with career-assets infrastructure
- Good Spanish+English quality
- Free, offline
- Acceptable size for personal use

**Decision:** _Pending_

---

## Q7: Graph Storage — Separate graphs or unified?

**Options:**
1. **Single graph** — poems, fragments, seeds, influences all in one graph
2. **Partitioned graphs** — separate graphs per node type, linked by ID
3. **Layered** — base poem graph + overlay graphs for context

**Recommendation:** Single graph (option 1).
- Simpler queries
- Cross-type similarity edges make sense (fragment ↔ poem)
- NetworkX handles mixed node types fine

**Decision:** _Pending_

---

## Q8: CLI vs. Conversational — Primary interaction mode?

**Options:**
1. **CLI-first** — `poesia write --theme X --form Y`
2. **Conversational-first** — You + LLM (Claude/me) using PoesIA tools
3. **Both equally supported**

**Current reality:** You work conversationally (VS Code + Claude), PoesIA validates.

**Recommendation:** Both (option 3), but conversational is primary workflow.
- CLI for scripted/repeatable tasks
- Conversational for exploratory drafting
- PoesIA provides tools for both

**Decision:** _Pending_

---

## Q9: career-assets Alignment — Share infrastructure?

**Options:**
1. **Independent** — PoesIA has own embedding/graph stack
2. **Shared model** — Use same `e5-base` for consistency
3. **Shared package** — Factor common graph/embedding code out

**Recommendation:** Independent with compatible model (option 2).
- Keeps PoesIA self-contained
- Future integration easy if same model
- No coupling to career-assets codebase

**Decision:** _Pending_

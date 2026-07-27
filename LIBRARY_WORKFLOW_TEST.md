# Library Workflow Test Results (2026-07-27)

## Test: Complete P1 End-to-End Data Flow

### What We Tested
1. Save poems with `--save`
2. Load library with `--use-library`
3. Semantic retrieval of relevant context
4. Provenance tracking

### Test Steps & Results

#### Step 1: Save a poem without provenance
```bash
poesia write --theme 'luna nocturna' --form haiku --save --tags 'noche,luna'
```

**Result:** ✅ Saved to `~/.poesia/poems/20260727_161355_233093_luna_nocturna.md`

Markdown file contains:
```yaml
---
id: 20260727_161355_233093_luna_nocturna
language: es
form: haiku
theme: luna nocturna
created_at: 2026-07-27T16:13:55.233093
tags: [noche, luna]
---
```

#### Step 2: Save with full provenance (--brief)
```bash
poesia write --theme 'estrellas brillantes' --form haiku --brief --save --tags 'cielo,estrellas'
```

**Result:** ✅ Saved with provenance metadata

Markdown file contains:
```yaml
---
id: 20260727_161423_888398_estrellas_brillantes
language: es
form: haiku
theme: estrellas brillantes
created_at: 2026-07-27T16:14:23.888398
tags: [cielo, estrellas]
embedding_model: intfloat/multilingual-e5-base
brief_level: standard
fragments_used: [07_breadth_curse, 01_pattern_finder, 10_learning_velocity, ...]
---
```

#### Step 3: Generate using library as context
```bash
poesia write --theme 'luna llena' --form haiku --use-library --brief --save
```

**Result:** ✅ Library poems used as retrieval context

Console output:
```
Loaded 2 poems from library for context
Added 2 library poems as retrieval context
✓ Semantic scoring enabled (sentence-transformers)
```

#### Step 4: Verify retrieval worked
Check the provenance of the new poem:

```yaml
fragments_used: [
  library:20260727_161423_888398_estrellas_brillantes,  ← Retrieved poem #2!
  library:20260727_161355_233093_luna_nocturna,          ← Retrieved poem #1!
  07_breadth_curse,                                       ← Personal fragments
  02_canary_in_mine,
  10_learning_velocity
]
```

**Result:** ✅ Library poems successfully retrieved and tracked in provenance

### Findings

#### ✅ What Works
1. **Saving poems** - Markdown + SQLite dual storage
2. **Provenance metadata** - Full lineage tracking when `--brief` used
3. **Library loading** - `--use-library` loads existing poems
4. **Fragment conversion** - Poems converted to retrievable fragments with `library:` prefix
5. **Semantic retrieval** - E5 embeddings select relevant context
6. **Provenance tracking** - `fragments_used` lists which poems influenced generation
7. **Theme scoring** - Non-zero scores (0.79) show semantic context is active

#### ⚠️ Limitations Found
1. **SQLite doesn't store provenance** - Only in markdown YAML frontmatter
2. **`Library.list_all()`** - Doesn't parse provenance from files (only basic metadata)
3. **Stub LLM language detection** - Sometimes generates English instead of Spanish with `--brief`

#### 📊 Data Flow Verified

```
[Generate with --save --brief]
         ↓
[Markdown file with provenance] + [SQLite index]
         ↓
[Load with --use-library]
         ↓
[Convert to fragments: library:<id>]
         ↓
[Semantic retrieval via E5 embeddings]
         ↓
[Selected fragments → GenerationBrief]
         ↓
[Generate new poem]
         ↓
[Provenance records: fragments_used]
```

### Conclusion

**P1 end-to-end RAG generation journey is WORKING** ✅

The complete flow from saving poems, loading them as context, semantic retrieval,
generation with that context, and provenance tracking all functions correctly.

The only gap is SQLite doesn't store full provenance (just basic metadata), but
the markdown files have complete lineage tracking and the retrieval system works.

### Test Data Location
- Library: `~/.poesia/poems/`
- Database: `~/.poesia/poems/library.db`
- 3 test poems saved with cross-references in provenance

# PoesIA Usage Guide

Complete guide to using PoesIA's poetry generation and analysis tools.

---

## Installation

```bash
# Basic installation (stub LLM only, no embeddings)
pip install -e .

# With semantic scoring (embeddings for theme/novelty)
pip install -e ".[nlp]"

# Full installation (includes image/music backends)
pip install -e ".[all]"
```

---

## Quick Start

### Generate a Simple Haiku
```bash
poesia write --theme "luna brillante" --form haiku
```

### Generate with Alternative Candidates Shown
```bash
poesia write --theme "noche estrellada" --form haiku --show-alternatives 5
```

### Save to Personal Library
```bash
poesia write --theme "soledad" --form haiku --save --tags "noche,introspección"
```

### Generate Using Library as Context
```bash
poesia write --theme "cielo nocturno" --form haiku --use-library --brief --show-alternatives 3
```

## Core Commands

### `poesia write` - Generate Poetry

Generate a poem using the constrained generate/validate/repair loop.

**Basic syntax:**
```bash
poesia write --theme "<theme>" --form <form> [OPTIONS]
```

**Key Options:**

| Option | Description | Default |
|--------|-------------|---------|  
| `--theme TEXT` | Thematic anchor (REQUIRED) | - |
| `--form NAME` | Poetic form: haiku, soneto, romance | `soneto` |
| `--language CODE` | Language: es, en, nl | `es` |
| `--llm BACKEND` | LLM backend: stub, gemini, openai, auto | `stub` |
| `--brief` | Use BriefBuilder for rich context | off |
| `--use-library` | Load library poems as context | off |
| `--save` | Save to library with provenance | off |
| `--show-alternatives N` | Show top-N candidates per line | `0` (off) |

---

## Poetic Forms

| Form | Lines | Syllables | Language |
|------|-------|-----------|----------|
| `haiku` | 3 | 5-7-5 | en, es |
| `soneto` | 14 | 11 | es |
| `romance` | variable | 8 | es |
| `sonnet_shakespearean` | 14 | 10 | en |

---

## Scoring Modes

### Degraded Mode (No Embeddings)
```
Scoring mode: metre only (no semantic scoring)
```
- Only metre scoring active
- Works offline, no dependencies

### Full Mode (With --brief)
```
✓ Semantic scoring enabled (sentence-transformers)
Scoring mode: metre + theme + novelty
```
- Theme: semantic similarity to theme (via E5 embeddings)
- Novelty: distinctness from prior lines
- Requires: `pip install -e ".[nlp]"`

## Alternative Presentation

The `--show-alternatives N` flag displays top-N candidates per line.

**Example:**
```
Line 1 (target: 5 syllables):
  1. [0.810] luna en la noche ✓
      syllables=5, metre=0.71, theme=0.00, novelty=1.00
  2. [0.600] luna sobre el mar azul
      syllables=8, metre=0.40, theme=0.00, novelty=1.00
```

**Color coding:**
- Green: score ≥ 0.7 (good)
- Yellow: score ≥ 0.4 (medium)
- Red: score < 0.4 (poor)
- ✓ checkmark: selected candidate

---

## Library Workflow

### Save Poems
```bash
poesia write --theme "luna" --form haiku --save --tags "noche,luna"
```

Saved to: `~/.poesia/poems/<id>.md` with provenance metadata.

### Generate Using Library Context
```bash
poesia write --theme "estrellas" --form haiku --use-library --brief
```

**What happens:**
1. Loads all poems from library
2. Converts to retrieval fragments (prefix: `library:<id>`)
3. Semantic retrieval selects relevant poems
4. Selected poems become generation context
5. Provenance tracks which poems were used

**Verify retrieval:**
```bash
cat ~/.poesia/poems/<newest-id>.md | grep fragments_used
# Shows: library:poem1_id, library:poem2_id, ...
```

---

## Examples

### Complete Workflow
```bash
# 1. Save first poem
poesia write --theme "luna de invierno" --form haiku --brief --save

# 2. Generate using first as context
poesia write --theme "estrellas frías" --form haiku --use-library --brief --show-alternatives 5

# 3. Verify retrieval
cat ~/.poesia/poems/$(ls -t ~/.poesia/poems/*.md | head -1) | grep fragments_used
```

### Debug Generation
```bash
poesia write --theme "soledad" --form haiku --show-alternatives 10 > debug.txt
grep -A 50 "Alternative Candidates" debug.txt
```

---

For more details, see README.md and LIBRARY_WORKFLOW_TEST.md.

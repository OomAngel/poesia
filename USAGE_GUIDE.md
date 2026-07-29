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

> **Note:** This project uses a conda environment. Activate with `conda activate poesia`.

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

### Generate with a Real LLM Backend
```bash
# Groq (requires GROQ_API_KEY)
poesia write --theme "luna" --form soneto --llm groq --brief

# Local Ollama (requires running ollama serve)
poesia write --theme "luna" --form haiku --llm ollama

# LoRA fine-tuned adapter
poesia write --theme "luna" --form soneto --llm lora --brief

# Grammar-constrained (Outlines / Qwen 1.5B)
poesia write --theme "luna" --form soneto --llm outlines
```

### Interactive Generation
```bash
poesia write --theme "noche" --form haiku --interactive --show-alternatives 5
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
| `--form NAME` | Poetic form: haiku, soneto, romance, sonnet_shakespearean | `soneto` |
| `--language CODE` | Language: es, en, nl | `es` |
| `--llm BACKEND` | LLM backend: stub, groq, gemini, openai, ollama, outlines, lora, auto | `stub` |
| `--brief` | Use BriefBuilder for rich context (fragments, seeds, influences) | off |
| `--brief-level LEVEL` | Verbosity: minimal, standard, maximal | `standard` |
| `--tone TONES` | Comma-separated tone descriptors (e.g., "melancholic,tender") | - |
| `--seeds SEEDS` | Comma-separated seed words for expansion | - |
| `--use-library` | Load library poems as context | off |
| `--save` | Save to library with provenance | off |
| `--show-alternatives N` | Show top-N candidates per line | `0` (off) |
| `--show-retrieval` | Display retrieved fragments/scores/graph paths | off |
| `--interactive` | Human line-by-line selection from scored candidates | off |
| `--yes` | Skip privacy confirmation (when using personal context) | off |
| `--lines N` | Override total line count for variable-length forms (e.g., romance) | auto |
| `--movement MOVEMENT` | Filter influences by literary movement (e.g., "Romanticism", "Generacion del 98") | - |

---

## Poetic Forms

| Form | Lines | Syllables | Language | Status |
|------|-------|-----------|----------|--------|
| `haiku` | 3 | 5-7-5 | en, es | ✅ |
| `soneto` | 14 | 11 | es | ✅ |
| `romance` | variable | 8 | es | ⚠️ Needs `--lines` param |
| `sonnet_shakespearean` | 14 | 10 | en | ✅ |

See `FORM_TESTING_RESULTS.md` for detailed form verification history.

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

## Interactive Mode

The `--interactive` flag lets you choose each line manually:

```
Line 1 (target: 5 syllables) — pick a candidate:
   1. [0.810] luna en la noche
   2. [0.600] luna sobre el mar
   3. [0.450] noche de luna llena
Enter choice (Enter=top, #=number, t=type own): 
```

- **Enter**: Accept the top-scored candidate
- **Number**: Pick a specific numbered candidate
- **t**: Type your own line (will be scanned and scored)

## Retrieval Display

The `--show-retrieval` flag shows which personal fragments and graph paths influenced generation:

```
Retrieved 5 fragments for brief:

--- Fragment: pattern-finder (score: 0.87) ---
  Path: pattern-finder -[similar_to 0.82]-> hound -[inspired_by]-> Garcia Lorca
  Content: There is a pattern in the way things break...

--- Influence: Antonio Machado (score: 0.72) ---
  spare, meditative, austere
```

## LLM Backends

| Backend | CLI Flag | Key/Setup | Notes |
|---------|----------|-----------|-------|
| Stub (dev/test) | `--llm stub` | None | Deterministic templates, no network |
| Groq | `--llm groq` | `GROQ_API_KEY` | Llama 3.3 70B, fast, free tier (30 RPM) |
| Gemini | `--llm gemini` | `GEMINI_API_KEY` | Google's Gemini API |
| OpenAI | `--llm openai` | `OPENAI_API_KEY` | OpenAI API |
| Ollama | `--llm ollama` | `ollama serve` running | Local, offline, gemma2:2b default |
| Outlines | `--llm outlines` | None | Qwen 1.5B + regex constraints, local |
| LoRA | `--llm lora` | Trained adapter | Qwen 1.5B + QLoRA fine-tune |
| Auto | `--llm auto` | Any available | Priority: Gemini → Groq → OpenAI |

---

## Library Workflow

### Save Poems
```bash
poesia write --theme "luna" --form haiku --save --tags "noche,luna"
```

Saved to: `~/.poesia/poems/<id>.md` with provenance metadata.

### List and Search Library
```bash
poesia memoria list                     # All poems
poesia memoria list --form haiku        # Filter by form
poesia memoria list --language es       # Filter by language
poesia memoria list --limit 10          # Limit results
poesia memoria search luna              # SQLite substring search
```

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

---

## Training (MLOps)

PoesIA includes a lightweight fine-tuning pipeline for QLoRA training of Qwen2.5-1.5B-Instruct.

### Structure

| Path | Purpose |
|---|---|
| `seeds/poetry_corpus/training_data/` | Versioned training/eval splits (JSONL, in git) |
| `scripts/train_poetry_lora.py` | QLoRA training script |
| `mlops/runs/` | Training run logs (not in git) |
| `models/` | Trained adapters (not in git) |
| `mlops/configs/` | Training configs (hyperparameters, data path) |
| `mlops/experiments.py` | Query DB: `list`, `best`, `compare`, `tag` |
| `mlops/ab_compare.py` | A/B comparison of two adapters |
| `mlops/evaluate_adapter.py` | Full eval across 5 themes |
| `mlops/pipeline.py --all` | Full pipeline: distill -> train -> eval -> compare |

### How to train

```bash
conda activate poesia
python scripts/train_poetry_lora.py mlops/configs/train_v1.yaml  # 500 sonetos, r=16
python scripts/train_poetry_lora.py mlops/configs/train_multiform.yaml  # 1,246 poems, r=32
```

### Evaluation

```bash
python mlops/experiments.py list
python mlops/experiments.py best --metric line_count_accuracy
python mlops/experiments.py compare --ids <a> <b>
python mlops/ab_compare.py --adapter-a <path> --adapter-b <path>
```

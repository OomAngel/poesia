# PoesIA Usage Guide

PoesIA is an instrument for letting things out: you bring what you carry, it
helps you give it the shape of poetry, and it teaches the craft as it goes.
This guide walks through the whole instrument. (Why it exists, who it is for and
the landscape research: `docs/POSITIONING.md`.)

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

> **Note:** This project uses a conda environment (`poesia`). Use `scripts/poesia_env.sh` for automatic env detection and activation, or `bash scripts/launch_training.sh local <config>` for training.

---

## The Poet's Path — start from what you feel

Four steps, from raw feeling to a made thing that stays yours:

### 1. You write, it teaches

Drop a line that's stuck in you; PoesIA scans syllables, stress and validity,
and tells you *why*:

```bash
poesia scan "la noche pesa como una losa de silencio" --language es
```

### 2. You choose, it scaffolds

Draft line by line. Keep the words that feel like yours, or type your own (`t`)
and have them scanned and scored:

```bash
poesia write --theme "lo que no pude decir" --form haiku --interactive --show-alternatives 5
```

### 3. You finish, it keeps

Save the poem *you* decided to keep — the machine's output was scaffolding:

```bash
poesia write --theme "lo que no pude decir" --form haiku --interactive --save
```

### 4. You look back, it remembers

```bash
poesia memoria list
poesia memoria search silencio
```

Everything below is the machinery for these steps.

---

## Quick Start (scaffolding mode)

The machine's output is always a *draft* — the poem is what you decide to keep.

### Generate a Draft Haiku
```bash
poesia write --theme "luna brillante" --form haiku
```

### Generate with Alternative Candidates Shown
```bash
poesia write --theme "noche estrellada" --form haiku --show-alternatives 5
```

### Save a Kept Poem to Your Library
```bash
poesia write --theme "soledad" --form haiku --save --tags "noche,introspección"
```

### Draft Using Your Library as Context
```bash
poesia write --theme "cielo nocturno" --form haiku --use-library --brief --show-alternatives 3
```

### Draft with a Real LLM Backend
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

### Interactive Drafting (the editor's seat)
```bash
poesia write --theme "noche" --form haiku --interactive --show-alternatives 5
```

## Core Commands

### `poesia write` - Draft Poetry

Draft a poem using the constrained generate/validate/repair loop. The output is
*scaffolding* — the poem is what you decide to keep.

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
| `--llm BACKEND` | LLM backend: stub, groq, gemini, openai, ollama, outlines, lora, cloudflare, auto | `stub` |
| `--brief` | Use BriefBuilder for rich context (fragments, seeds, influences) | off |
| `--brief-level LEVEL` | Verbosity: minimal, standard, maximal | `standard` |
| `--tone TONES` | Comma-separated tone descriptors (e.g., "melancholic,tender") | - |
| `--seeds SEEDS` | Comma-separated seed words for expansion | - |
| `--use-library` | Load library poems as context | off |
| `--save` | Save to library with provenance | off |
| `--reflection TEXT` | What you meant/felt — stored beside the poem in memoria | prompted on save (skipped with `--yes`) |
| `--no-title` | Disable automatic LLM title suggestion on save | off (auto-title on) |
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
- **t**: Type your own line — it is scanned and *taught* against the line
  position's target before it is kept (syllable count, sinalefas, why it's
  over/short, and how to fix it)

## The Workshop — the four movements, guided

`poesia workshop` walks the whole poet's path in one sitting: you write what
you carry (outlet), shape it line by line (the machine scaffolds, you keep the
editor's seat), get the craft explained on every line (teaching), and — if you
choose to save — the poem and your reflection are kept together in memoria
(linking).

```bash
poesia workshop --form soneto --save
poesia workshop --form haiku --outlet "lo que no pude decir"  # non-interactive outlet
```

After the draft, the workshop prints a teaching recap that scans every line of
the finished poem against its target and explains each one.

## Scan — the teaching voice

`poesia scan` reads a line and teaches *why* it works or how to fix it. Give
it a form (or an explicit target) and it teaches against that metre:

```bash
# Plain scan: syllables, stress, validity
poesia scan "la noche pesa como una losa de silencio" --language es

# Teaching against a form's target
poesia scan "la noche pesa como una losa" --form soneto
poesia scan "la aurora brilla" --form haiku

# Or against an explicit target
poesia scan "verso demasiado largo" --syllables 11
```

The lesson names the metre delta ("Short by 1: this line has 10 syllables; the
target of a soneto is 11"), points at any sinalefas, notes final-word stress
effects (aguda/esdrújula), and gives craft-specific fix tips.

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
| LoRA | `--llm lora` | Trained adapter | Auto-detects best adapter + base model (1.5B or 3B) |
| MLflow | `--llm mlflow` | `MLFLOW_MODEL_URI` env | Loads registered model via `PoetryModelWrapper.predict()` |
| Cloudflare | `--llm cloudflare` | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | Workers AI llama-3.3-70b via the OpenAI-compatible endpoint |
| Outlines | `--llm outlines` | None | Qwen + regex constraints, auto-detects adapter | 
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

PoesIA uses MLflow for experiment tracking, model registry, and serving. All training runs log to `mlruns/mlflow.db` (SQLite).

### Launcher (recommended)

```bash
# Auto-activates conda env, sources .env_mlflow, validates GPU
bash scripts/launch_training.sh local mlops/configs/train_qwen3b.yaml
bash scripts/launch_training.sh local mlops/configs/train_smoke.yaml --dry-run
bash scripts/launch_training.sh docker mlops/configs/train_qwen3b.yaml
bash scripts/launch_training.sh dpo    # DPO preference learning

# List available configs
bash scripts/launch_training.sh local --list-configs
```

### Environment setup

```bash
# Auto-detect and activate (sources conda + .env_mlflow)
source scripts/poesia_env.sh --source

# Or manually:
conda activate poesia
export MLFLOW_TRACKING_URI="sqlite:///mlruns/mlflow.db"
```

### Manual training

```bash
python scripts/train_poetry_lora.py mlops/configs/train_v1.yaml       # 500 sonetos, r=16
python scripts/train_poetry_lora.py mlops/configs/train_qwen3b.yaml   # Qwen2.5-3B
python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml          # DPO learning
```

### MLflow UI

```bash
# Docker stack (PostgreSQL + MLflow UI):
docker compose -f docker/docker-compose.yml up -d
# Open: http://localhost:5000

# Or local:
mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db
```

### Query experiments

```bash
python mlops/experiments.py list
python mlops/experiments.py best --metric eval_line_count_accuracy
python mlops/list_runs.py
```

### Docker (for reproducible training)

```bash
docker compose -f docker/docker-compose.yml build training
docker compose -f docker/docker-compose.yml run training python scripts/train_poetry_lora.py mlops/configs/train_qwen3b.yaml
```

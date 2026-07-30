# Active Context — PoesIA

_Last updated: 2026-07-30 (massive architecture + MLflow + training overhaul)_

---

## Re-entry checklist

```bash
cd /home/angel/dev/poesia
conda activate poesia
source .env_mlflow  # sets MLFLOW_TRACKING_URI
```

Quick sanity:
```bash
poesia write --theme "luna sobre el mar" --form haiku --llm stub

# Test MLflow data exists:
python3 -c "import mlflow; mlflow.set_tracking_uri('sqlite:///mlruns/mlflow.db'); from mlflow.tracking import MlflowClient; c=MlflowClient(); print(sum(len(c.search_runs([e.experiment_id])) for e in c.search_experiments()), 'runs')"
```

## Current focus

**Full training pipeline needs a complete run.** MLflow has data (9 runs, 6 experiments) but no fully trained adapter with composite loss. The last composite run was killed (was 1000s/step due to live scorer penalty — fixed with pre-computed weights).

### Available to run

| Command | What | Time |
|---------|------|------|
| `python scripts/train_poetry_lora.py mlops/configs/train_composite.yaml` | Composite loss on 500 scored sonetos | ~2h |
| `python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml` | DPO preference learning | ~1h |
| `python scripts/evaluate_poetry.py --adapter models/poetry-lora-v2/final_adapter` | MLflow 3.x genai.evaluate | ~5min |
| `python scripts/run_experiment_grid.py --grid loss_compare` | Compare CE vs Composite vs DPO | ~5h |

### What was built this session

#### 1. Architecture Patterns (VerifIA)
- WriteConfig Builder — 16-param god function fixed (`src/poesia/config/types.py`)
- LLM Registry — `@register_llm` decorator, `get_llm()` factory (`src/poesia/generation/registry.py`)
- ScorerProtocol — evaluation now follows Protocol seam
- Observer hooks — HookEvent system in generation loop
- Facade API — `from poesia.api import write_poem`
- VerifIA pattern documented — `docs/ARQUITECTURA.md`

#### 2. Training Infrastructure
- PoetryTrainer — weighted CE with pre-computed quality scores
- 8-metric scoring — syllable, rhyme, lexical diversity, abstract ratio, emotion, imagery, readability, line count
- DPO training — `scripts/train_poetry_dpo.py`
- Experiment grid — `scripts/run_experiment_grid.py`

#### 3. MLflow (finally correct)
- Backend: SQLite (`sqlite:///mlruns/mlflow.db`)
- Training: `mlflow.transformers.autolog()` replaces 100+ lines of manual logging
- Traces: `@mlflow.trace()` on all 4 LLM clients
- Evaluation: `mlflow.genai.evaluate()` with custom `@scorer` decorators
- Model Registry: auto-promotes to Production
- **9 runs across 6 experiments** with real data

#### 4. Emotion & Imagery Pipeline
- pysentimiento (sentence-level emotion, ES+EN)
- Spanish Emotion Lexicon (98 words, 8 NRC emotions)
- textstat readability (Spanish)
- Imagery extraction (spaCy noun phrases -> sensory modalities)
- Image prompt builder (-> DALL-E/SDXL)

#### 5. Documentation
- `docs/ARQUITECTURA.md` — VerifIA pattern + benchmarks vs Hexagonal/LangChain
- `docs/EXPERIMENTS_PLAN.md` — 6 models x 6 techniques x 3 loss functions
- `docs/CRONOLOGIA_CLOUD.md` — Local -> Neon -> Fly.io migration
- `docs/ANALOGIA_PLAN.md` — A/B, memory mining, stylistic fingerprinting

## Quick commands for next session

```bash
# Start MLflow UI
python3 -m mlflow server --backend-store-uri sqlite:///mlruns/mlflow.db --host 0.0.0.0 --port 5000

# Train with composite loss
python scripts/train_poetry_lora.py mlops/configs/train_composite.yaml

# Evaluate adapter with MLflow 3.x scorers
python scripts/evaluate_poetry.py --adapter models/poetry-lora-v2/final_adapter

# Find best adapter by metric
python3 -c "from scripts.train_poetry_lora import search_best_adapter; print(search_best_adapter('syllable_accuracy'))"

# Run DPO
python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml

# Run experiment grid
python scripts/run_experiment_grid.py --grid loss_compare
```

## Document authority

| What | Where |
|------|-------|
| VerifIA pattern + benchmarks | `docs/ARQUITECTURA.md` |
| Experiment plan (models, techniques, loss) | `docs/EXPERIMENTS_PLAN.md` |
| Cloud migration guide | `docs/CRONOLOGIA_CLOUD.md` |
| AnalogIA (A/B + memory mining) plan | `docs/ANALOGIA_PLAN.md` |
| RAG/LLM sequencing | `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` |
| Feature roadmap | `docs/ROADMAP.md` |
| CLI usage | `USAGE_GUIDE.md` |
| Kanban | `memory-bank/tasks.md` |
| Architecture + package survey | `docs/ARCHITECTURE.md` |
| Pre-generation enrichment | `docs/ENRICHMENT.md` |
| CronologIA deployment | `cronologia/docker-compose.yml` + `.env.example` |
| Retraining history | `docs/ROADMAP.md` (Retraining section) |

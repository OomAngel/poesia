# PoesIA MLOps

Lightweight MLOps for a personal poetry fine-tuning pipeline.
No Kubernetes, no MLflow — just git + JSONL + a GPU.

## Pipeline

```
data/  ──►  train.py  ──►  adapter/  ──►  evaluate.py  ──►  deploy (via --llm lora)
 ↑                 ↑
seeds/            models/
```

## Structure

| Path | Purpose |
|---|---|
| `seeds/poetry_corpus/training_data/` | Versioned training/eval splits (JSONL, in git) |
| `scripts/train_poetry_lora.py` | QLoRA training script |
| `mlops/runs/` | Training run logs (not in git) |
| `models/` | Trained adapters (not in git) |
| `mlops/compare.py` | Compare base vs fine-tuned output quality |

## How to train

```bash
# Activate environment
conda activate poesia

# Run training (~1-2 hours on RTX 2000 Ada, 8.6GB VRAM)
python scripts/train_poetry_lora.py

# Output: models/poetry-lora-3b/final_adapter/ (~50 MB)
```

## How to evaluate

After training, compare base model vs fine-tuned:

```bash
# Generate with base model
python -m poesia.cli write --theme "luna" --form haiku --llm lora --brief --yes

# Compare with Groq
python -m poesia.cli write --theme "luna" --form haiku --llm groq --brief --yes
```

## Data versioning

The training corpus is in `seeds/poetry_corpus/training_data/` and tracked in git.
When you add new data:
1. Add new poems to `seeds/poetry_corpus/`
2. Rebuild the dataset with the extraction script
3. Retrain
4. Commit the new data + new adapter

## Retraining triggers

- New poetry sources added to the corpus
- Current adapter quality degrades for your use case
- Better base model becomes available (e.g. Llama 4 3B)

## Model artifacts

The trained adapter is at `models/poetry-lora-3b/final_adapter/` (gitignored).
To reproduce it:

```bash
python scripts/train_poetry_lora.py
```

This uses the versioned training data in `seeds/poetry_corpus/training_data/`
and the versioned training script in `scripts/train_poetry_lora.py`.

# Session Handoff — 2026-07-28

## Current State
**Git HEAD:** e99732c
**Working tree:** clean

## What Was Done

### 1. Prompt Engineering (Path 1)
- Hard language constraint: `IMPORTANT: You MUST write in Spanish.`
- Few-shot examples (Lope de Vega soneto, classic haiku)
- Poetic quality directive (imagery, metaphor, musicality)

### 2. Language Filter (Path 2)
- `_filter_by_language()` in constrained_loop.py
- Rejects English lines for Spanish poems before scoring
- Interactive line selector: Enter=best, number=choice, t=type own

### 3. Fine-Tuning (Path 3)
- First run: 9,622 raw poems, r=16, loss=3.22 — line count ~9/14
- Second run: 500 structured sonetos, r=16, loss=2.69 — line count 14/14 ✅
- Syllable deviation: from 2.5 to 1.1 (56% improvement)
- Adapter: `models/poetry-lora-v2/final_adapter/`

### 4. Grammar-Constrained Generation (Outlines)
- OutlinesClient: enforces single-line generation at token level
- Wired as `--llm outlines`
- Fixes the '9 lines instead of 14' problem completely

### 5. MLOps Infrastructure
- Config-driven training: `mlops/configs/` (.yaml)
- Experiments database: `mlops/runs/experiments.jsonl`
- Query CLI: `python mlops/experiments.py list | best | compare | tag`
- Adapter registry: `mlops/adapter_registry.json`
- Auto-evaluation after training (line count + syllable deviation)
- A/B comparison: `mlops/ab_compare.py`
- Pipeline orchestration: `mlops/pipeline.py --all`
- First tracked run: `20260728_231807`
  - 500 sonetos, r=16, 10 epochs, loss=2.69
  - Line count: 100%, Syllable dev: 1.1, Status: evaluated

### 6. Semantic Resources Wired
- NLTK WordNet installed (English synonyms/antonyms/hypernyms/hyponyms)
- spaCy es_core_news_sm (Spanish lemmatization + POS)
- Datamuse API endpoint fixed (synonyms + collocations)
- SeedExpander updated with NLTK fallback + spaCy + Datamuse

### 7. Multi-Form Datasets Created
| Form | Count | Structure |
|------|-------|-----------|
| soneto | 500 | 14 lines, ~11 syll |
| romance | 500 | 8-syll lines, variable length |
| decima | 133 | 10 lines, 8 syll |
| cuarteto | 86 | 4 lines |
| haiku | 27 | 3 lines, 5-7-5 |
- Combined: `seeds/poetry_corpus/training_data_structured/multiform_train.jsonl` (1,246 poems)

## Pending for Next Session

### Priority 1: Multi-form Training
- `python scripts/train_poetry_lora.py mlops/configs/train_multiform.yaml`
- r=32, 12 epochs, 1,246 multi-form poems
- Then compare: `python mlops/experiments.py compare --ids 20260728_231807 <new_id>`

### Priority 2: Distillation Pipeline
- `GROQ_API_KEY=gsk_... python scripts/distill_sonetos.py --count 200`
- Generates perfect sonetos with verified metre + rhyme
- Train: `python scripts/train_poetry_lora.py mlops/configs/train_distilled.yaml`

### Known Issues to Address
- `wn` server 503 (Open Multilingual Wordnet) — NLTK fallback active for EN, Datamuse for ES
- 500 structured sonetos avg 10.5 syll, not exactly 11 (filter needed if exact target required)
- Spanish WordNet `omw-es:1.4` needs retry when server is up

## Quick Reference

### Training
```bash
python scripts/train_poetry_lora.py mlops/configs/train_v1.yaml          # 500 sonetos, r=16, ~15 min
python scripts/train_poetry_lora.py mlops/configs/train_multiform.yaml   # 1,246 poems, r=32, ~30 min
python scripts/train_poetry_lora.py mlops/configs/train_distilled.yaml   # Distilled from Groq
```

### Evaluation
```bash
python mlops/experiments.py list                                    # All runs
python mlops/experiments.py best --metric line_count_accuracy       # Best model
python mlops/experiments.py compare --ids <a> <b>                   # Side-by-side
python mlops/experiments.py tag --id <run> --add 'baseline'         # Tag runs
python mlops/ab_compare.py --adapter-a <path> --adapter-b <path>    # A/B adapters
python mlops/pipeline.py --all --distill-count 100                  # Full pipeline
```

### Generation
```bash
poesia write --theme 'luna' --form soneto --llm outlines --brief
poesia write --theme 'luna' --form romance --llm outlines --brief
poesia write --theme 'luna' --form haiku --llm groq --brief
poesia write --theme 'luna' --form soneto --llm lora --brief
```

### Monitor Training
```bash
tail -f /tmp/training.log | tr '\r' '\n' | grep -oP '\d+/\d+.*?s/it'
nvidia-smi
```
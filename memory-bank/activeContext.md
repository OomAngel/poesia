# Active Context — PoesIA

_Last updated: 2026-07-28 (full session — MLOps, Outlines, multi-form datasets, WordNet/spaCy wired)_

---

## Re-entry checklist

```bash
cd /home/angel/dev/poesia
conda activate poesia
python -m pytest tests/ --tb=no -q   # 400+ passed
export GROQ_API_KEY=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
```

Quick sanity:
```bash
poesia write --theme "luna sobre el mar" --form haiku --llm outlines --brief --yes
```

---

## Current focus — next session starts here

**Priority: Multi-form training → Distillation → Syllable filtering**

### Immediate next action (run first)
```bash
python scripts/train_poetry_lora.py mlops/configs/train_multiform.yaml
```
- 1,246 poems (sonetos, romances, décimas, cuartetos, haikus)
- r=32, 12 epochs, lr=1e-4, batch=16 effective
- Expected: ~30 min on RTX 2000 Ada
- Track in: `mlops/runs/experiments.jsonl`
- Compare afterwards: `python mlops/experiments.py compare --ids 20260728_231807 <new_run_id>`

### Then (priority 2)
```bash
GROQ_API_KEY=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 \
  python scripts/distill_sonetos.py --count 200
python scripts/train_poetry_lora.py mlops/configs/train_distilled.yaml
```

### Then (known issues)
- `wn` Spanish WordNet server 503 — retry later
- 500 structured sonetos avg 10.5 syll, not exactly 11 — can filter if needed
- Exact syllable filtering for training data

---

## What has been built

### Generation clients (6 total)
| Client | Flag | Backend |
|---|---|---|
| `StubLLMClient` | `--llm stub` | Mock (dev/test) |
| `HostedLLMClient` | `--llm groq/gemini/openai` | API-based |
| `OllamaClient` | `--llm ollama` | Local Ollama |
| `LoRAClient` | `--llm lora` | Qwen 1.5B + LoRA adapter |
| `OutlinesClient` | `--llm outlines` | Qwen 1.5B + regex constraints |

### Training infrastructure (MLOps)
| Tool | Purpose |
|---|---|
| `scripts/train_poetry_lora.py` | Config-driven QLoRA training (reads .yaml) |
| `mlops/configs/` | Training configs (hyperparameters, data path, tags) |
| `mlops/experiments.py` | Query DB: `list`, `best`, `compare`, `tag` |
| `mlops/ab_compare.py` | A/B comparison of two adapters (metric table + winner) |
| `mlops/evaluate_adapter.py` | Full eval across 5 themes (line count, syllable dev) |
| `mlops/adapter_registry.json` | Registry of all trained adapters |
| `mlops/pipeline.py --all` | Full pipeline: distill → train → eval → compare |
| `mlops/runs/` | Experiment logs and database |

### Training data (curated)
| Dataset | Count | Location |
|---|---|---|
| Raw corpus (mixed) | 9,140 | `seeds/poetry_corpus/training_data/train.jsonl` |
| Row sonetos | 5,060 | `seeds/poetry_corpus/sonetos_curated/sonetos.jsonl` |
| Structured sonetos | 500 | `seeds/poetry_corpus/training_data_structured/sonetos_train.jsonl` |
| Romances | 500 | `seeds/poetry_corpus/training_data_structured/romances.jsonl` |
| Décimas | 133 | `seeds/poetry_corpus/training_data_structured/decimas.jsonl` |
| Cuartetos | 86 | `seeds/poetry_corpus/training_data_structured/cuartetos.jsonl` |
| Haikus | 27 | `seeds/poetry_corpus/training_data_structured/haikus.jsonl` |
| **Multi-form combined** | **1,246** | **`seeds/poetry_corpus/training_data_structured/multiform_train.jsonl`** |

### Trained adapters
| Run ID | Experiment | Config | Line acc | Syll dev | Location |
|---|---|---|---|---|---|
| `20260728_231807` | soneto-structured | `train_v1.yaml` | 100% | 1.1 | `models/poetry-lora-v2/final_adapter/` |

### Semantic resources wired
| Resource | Language | Status |
|---|---|---|
| NLTK WordNet | English | ✅ synonyms, antonyms, hypernyms, hyponyms |
| spaCy es_core_news_sm | Spanish | ✅ lemmatization, POS |
| Datamuse API (ml=) | Spanish/English | ✅ synonyms, collocations |
| Open Multilingual Wordnet (wn) | Spanish | ❌ server 503, retry later |
| SeedExpander | Multi | ✅ fallback chain: wn → NLTK → Datamuse |
| Sentence Transformers (e5-small) | Multi | ✅ cached (384-dim) |

---

## Document authority

| What | Where |
|---|---|
| RAG/LLM sequencing and DoD | `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` |
| Feature roadmap | `docs/ROADMAP.md` |
| Kanban | `memory-bank/tasks.md` |
| CLI usage | `USAGE_GUIDE.md` |
| Architecture rules | `docs/ARCHITECTURE.md` |
| Full session handoff | `docs/SESSION_HANDOFF.md` |
| All tunable parameters | `docs/ALL_TUNABLE_PARAMETERS.md` |
| Retraining plan + missing techniques | `docs/RETRAINING_PLAN.md` |

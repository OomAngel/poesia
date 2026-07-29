# Active Context — PoesIA

_Last updated: 2026-07-29 (documentation audit, consolidation, and fixes across all docs)_

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

## Current focus

**Training complete** — multi-form adapter saved to `models/poetry-lora-multiform/final_adapter/`

| Metric | Soneto-only (v2) | Multi-form (v3) |
|--------|:-:|:-:|
| Line accuracy | 100% | 100% |
| Syllable deviation | 1.1 | 2.14 |
| Train loss | 2.69 | 2.66 |
| Forms | 1 (soneto) | 5 |

v2 is better for sonetos (more precise syllables). v3 is the only option for other forms.
Switch adapters: `LORA_ADAPTER_PATH=models/poetry-lora-v2/final_adapter`

### 🔄 Running now

**Distillation v3**: `scripts/distill_sonetos.py` — 17/50 valid sonetos, ~5% success rate (strict quality filter)

### Architecture improvements implemented this session

| # | Pattern | Files | Status |
|---|---------|-------|--------|
| 1 | **WriteConfig Builder** — replaces 16-param god function | `src/poesia/config/types.py`, `cli.py` | ✅ |
| 2 | **CQS** — ConstrainedLoop separated from scoring | `scorer.py` (ScorerProtocol) | ✅ |
| 3 | **LLM Registry** — `@register_llm` decorator, `get_llm()` factory | `src/poesia/generation/registry.py` | ✅ |
| 4 | **ScorerProtocol** — evaluation layer now follows Protocol seam | `src/poesia/evaluation/scorer.py` | ✅ |
| 5 | **Composite Config** — WriteConfig validates + serialises | `src/poesia/config/types.py` | ✅ |
| 6 | **Observer hooks** — HookEvent system in generation loop | `src/poesia/generation/hooks.py` + `constrained_loop.py` | ✅ |
| 7 | **Facade API** — `from poesia.api import write_poem` | `src/poesia/api.py` | ✅ |
| 8 | **Data Lineage** — source files, git hash, filter params tracked | `scripts/train_poetry_lora.py` | ✅ |
| 9 | **CronologIA** — Docker + PostgreSQL MLflow stack | `cronologia/docker-compose.yml` | ✅ |

### What was done this session (2026-07-29)
1. **Documentation consolidation**: 26 → 13 files. Deleted 6 stale records, absorbed 8 files into 5 targets, merged 3 enrichment docs into 1.
2. **Romance form fix**: Added `--lines N` CLI param for variable-length forms. Wired through CLI → ConstrainedLoop.run() as `total_lines_override`.
3. **Syllable filter script**: `scripts/filter_exact_syllables.py` — scans poems via phonology backend, filters by configurable tolerance. Generated `sonetos_filtered_t2.jsonl` (47 poems with ≤2 off-target lines).
5. **LoRAClient adapter resolution**: Now auto-discovers newest adapter (multiform -> v2 -> v3b). Supports `LORA_ADAPTER_PATH` env var override.
6. **Distillation script hardened**: Added User-Agent header (Cloudflare fix), 429 retry, correct output config reference.
7. **WordNet Spanish**: Still 503/unavailable. NLTK WordNet (EN) fallback working.

### Next after training completes
1. Compare: `python mlops/experiments.py compare --ids 20260728_231807 <new_run_id>`
2. Evaluation: `python mlops/evaluate_adapter.py --adapter models/poetry-lora-multiform/final_adapter`
3. Distillation: `GROQ_API_KEY=... python scripts/distill_sonetos.py --count 200`
4. Distilled training: `python scripts/train_poetry_lora.py mlops/configs/train_distilled.yaml`

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
| Feature roadmap + retraining history | `docs/ROADMAP.md` |
| Kanban | `memory-bank/tasks.md` |
| CLI usage | `USAGE_GUIDE.md` |
| Architecture + package survey | `docs/ARCHITECTURE.md` |
| Pre-generation enrichment | `docs/ENRICHMENT.md` |
| Arquitectura pattern | `docs/ARQUITECTURA.md` |
| Cloud migration guide | `docs/CRONOLOGIA_CLOUD.md` |
| AnalogIA plan | `docs/ANALOGIA_PLAN.md` |
| CronologIA deployment | `cronologia/docker-compose.yml` + `.env.example` |
| Retraining history + missing techniques | `docs/ROADMAP.md` (Retraining section) |

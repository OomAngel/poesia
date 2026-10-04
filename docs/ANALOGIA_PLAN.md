# AnalogIA — Comparison, Pattern Matching & Memory Mining

> **Analogía** (Spanish: *analogy*). Natural extension: **-IA**.
> Role: A/B comparisons, retrieval comparisons, fragment pattern matching, and **memory mining** — finding how the same feeling recurs across poems and fragments over time.

---

## Vision

AnalogIA is the observatory of PoesIA: the tool that looks backward across all experiments, all fragments, all poems — and finds patterns. It compares adapters, compares retrieval strategies, and most importantly, **compares you to yourself across time**.

---

## Current adapter comparison (2026-09-08)

All 8 non-empty adapters have been evaluated via
`scripts/evaluate_adapter_mlflow.py` (3 themes: luna, mar, tiempo), logged to
MLflow (`poesia-evaluation` experiment, 27 runs). Lower syllable deviation is
better; line-count accuracy is 1.00 for every adapter.

| Adapter | avg syllable dev | line acc | base model | training |
|---|---|---|---|---|
| poetry-lora-distilled | **0.90** | 1.00 | Qwen2.5-1.5B | knowledge distillation |
| poetry-lora-qwen3b | 1.13 | 1.00 | Qwen2.5-3B | structured |
| poetry-lora-v2 | 1.97 | 1.00 | Qwen2.5-1.5B | structured |
| poetry-lora-3b | 3.91 | 1.00 | Qwen2.5-1.5B | early/legacy |
| smoke-test-adapter | 4.08 | 1.00 | Qwen2.5-1.5B | smoke |
| poetry-lora-v2-fixed | 4.80 | 1.00 | Qwen2.5-1.5B | "fixed" format |
| poetry-lora-dpo-expanded | 6.07 | 1.00 | Qwen2.5-1.5B | DPO |
| poetry-lora-multiform | 9.29 | 1.00 | Qwen2.5-1.5B | multi-form |

**Champion: `poetry-lora-distilled` (0.90).** Challenger: `poetry-lora-qwen3b`
(1.13).

Caveat (2026-10-04): the 2026-09-01 run of the same 3 unseeded themes put them in the
opposite order (`qwen3b` 1.00, `distilled` 1.29; `GENERATION_QUALITY_PLAN.md`). The order of
the top two is within noise. Only the large gaps (≤ 1.3 against ≥ 4.8) hold at this sample
size. See `docs/RETRAINING_PLAN_2026-10.md` §4.

Surprises worth investigating: the "fixed-format" retraining (v2-fixed, 4.80)
and the multi-form v3 (multiform, 9.29) are *worse* than the earlier
distilled/v2/qwen3b adapters, and DPO (6.07) underperforms plain CE — the
"fixed format" hypothesis (the `scripts/build_fixed_dataset.py` docstring and the
`mlops/configs/train_v2_fixed.yaml` header) did not pan out.

Note: these MLflow `avg_syllable_deviation` values differ from the legacy
`eval_syllable_deviation` in `mlops/adapter_registry.json` (pre-MLflow manual
eval); treat the MLflow values as the current methodology.

---

## Planned Features

### Phase 1: A/B Testing (MVP — partially done in mlops/ab_compare.py)
- [ ] Move `ab_compare.py` into `src/poesia/analogia/` (package to create)
- [ ] Run two adapters on the same 5 themes
- [ ] Compare syllable deviation, line accuracy, rhyme accuracy
- [ ] Declare a winner with evidence table

### Phase 2: Dense vs Graph Retrieval Comparison
- [ ] Run dense-only and graph-enhanced retrieval on the same query
- [ ] Compare which fragments are found by each method
- [ ] Measure overlap ratio, diversity gain
- [ ] Currently partially covered by `test_graph_retrieval_returns_results()`
  (`tests/test_p4_retrieval_relevance.py`; the older `test_dense_vs_graph_retrieval_differ()`
  was removed in `76f5c84`)

### Phase 3: Time-series adapter evolution
- [ ] Chart syllable deviation across all adapter runs
- [ ] Chart line accuracy growth over time
- [ ] Identify which training decisions produced the biggest improvements
- [ ] Feed from MLflow (`mlops/experiments.py`, `mlruns/mlflow.db`) + `mlops/adapter_registry.json`
  (the legacy `experiments.jsonl` was removed 2026-08-01)

### Phase 4: Memory Mining (core AnalogIA feature)
- [ ] Given a theme or emotion ("soledad", "melancolía"), find fragments from *every* source (angel_fragments, library poems, influences, training data)
- [ ] Show how the same concept appears in different forms across years
- [ ] Visualize emotional arc across your entire poetic corpus
- [ ] Answer: *"How has my voice changed?"*

### Phase 5: Stylistic Fingerprinting
- [ ] Compute a "stylistic fingerprint" for each adapter
- [ ] Metrics: avg syllables, rhyme density, emotional range, imagery density, lexical diversity
- [ ] Compare fingerprints across adapters to quantify "this model writes more like Machado now"

---

## Data Sources

| Source | What it contains | How AnalogIA uses it |
|--------|-----------------|---------------------|
| MLflow (`mlruns/mlflow.db`, queried via `mlops/experiments.py`) | All training runs (replaces the removed `mlops/runs/experiments.jsonl`) | Time-series adapter evolution |
| `mlops/adapter_registry.json` | Adapter metadata | A/B test selection |
| `~/.poesia/poems/` | All saved poems | Stylistic fingerprinting |
| `seeds/angel_fragments/` | Personal fragments | Memory mining |
| `data/influences.yaml` | Poetic influences | Style comparison anchors |

---

## CLI (planned — no `poesia analogia` command exists yet)

```bash
# Compare two adapters
poesia analogia compare --adapter-a models/v2 --adapter-b models/v3

# Run retrieval comparison
poesia analogia retrieve --query "silencio" --dense-vs-graph

# Show memory mining results
poesia analogia mine --theme "soledad" --from 2019 --to 2026

# Show adapter evolution
poesia analogia timeline

# Show stylistic fingerprint of current poems
poesia analogia fingerprint --source library
```

# AnalogIA — Comparison, Pattern Matching & Memory Mining

> **Analogía** (Spanish: *analogy*). Natural extension: **-IA**.
> Role: A/B comparisons, retrieval comparisons, fragment pattern matching, and **memory mining** — finding how the same feeling recurs across poems and fragments over time.

---

## Vision

AnalogIA is the observatory of PoesIA: the tool that looks backward across all experiments, all fragments, all poems — and finds patterns. It compares adapters, compares retrieval strategies, and most importantly, **compares you to yourself across time**.

---

## Planned Features

### Phase 1: A/B Testing (MVP — partially done in mlops/ab_compare.py)
- [ ] Move `ab_compare.py` into `src/poesia/analogia/`
- [ ] Run two adapters on the same 5 themes
- [ ] Compare syllable deviation, line accuracy, rhyme accuracy
- [ ] Declare a winner with evidence table

### Phase 2: Dense vs Graph Retrieval Comparison
- [ ] Run dense-only and graph-enhanced retrieval on the same query
- [ ] Compare which fragments are found by each method
- [ ] Measure overlap ratio, diversity gain
- [ ] Currently partially in `test_dense_vs_graph_retrieval_differ()`

### Phase 3: Time-series adapter evolution
- [ ] Chart syllable deviation across all adapter runs
- [ ] Chart line accuracy growth over time
- [ ] Identify which training decisions produced the biggest improvements
- [ ] Feed from `experiments.jsonl` + `mlflow`

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
| `mlops/runs/experiments.jsonl` | All training runs | Time-series adapter evolution |
| `mlops/adapter_registry.json` | Adapter metadata | A/B test selection |
| `~/.poesia/poems/` | All saved poems | Stylistic fingerprinting |
| `seeds/angel_fragments/` | Personal fragments | Memory mining |
| `data/influences.yaml` | Poetic influences | Style comparison anchors |

---

## CLI

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

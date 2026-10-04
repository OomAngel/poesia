# Arquitectura — PoesIA Architectural Pattern

> **VerifIA** (verificación + IA): an architecture where a deterministic verification layer
> constrains and validates a generative LLM, not the other way around.

---

## 1. The VerifIA Pattern

```
User Input ──► Enrichment ──► LLM Generation ──► Deterministic Verification ──► Human Selection
                    │                │                   │
                    ▼                ▼                   ▼
              BriefBuilder    CandidateGenerator    Phonology + Scorer
              (context)       (creative)            (ground truth)
```

**Core principle:** The LLM is never trusted for structure. It generates candidates;
deterministic phonology validates them. This inverts the typical "LLM does everything"
pattern.

**Three invariants:**
1. `phonology/` has zero dependencies — it is the mathematical ground truth
2. Every external service is behind a `Protocol` — no SDK import leaks
3. Heavy dependencies are lazy-loaded — `import poesia` never loads PyTorch

---

## 2. Layer Map

| Layer | Trust model | Technology | Swap cost |
|-------|------------|------------|-----------|
| **Phonology** (phonology/) | Deterministic — never calls LLM | silabeador, fonemas, pronouncing (rantanplan does not install on 3.13) | One-file change |
| **Scorer** (evaluation/) | Composable — Protocol | sentence-transformers (optional theme/novelty in `scorer.py`); `evaluation/emotion_lexicon.py` (NRC lexicon), pysentimiento and textstat are used only by data-prep scripts (`distill_sonetos.py`, `score_training_data.py`) | Protocol implementation |
| **Generator** (generation/) | Untrusted — candidates only | Registry (`generation/registry.py`): Groq, Gemini, OpenAI, Ollama, Cloudflare, llama.cpp, LoRA, Outlines, MLflow, router | Registry lookup |
| **Enrichment** (generation/brief_builder.py) | Structured — dataclass | E5 embeddings, WordNet, Datamuse | Builder config |
| **CLI** (cli.py) | Thin — delegates to config | Typer, Rich | Form -> WriteConfig |

---

## 3. Benchmark: VerifIA vs Other Architectures

| Dimension | **VerifIA** (PoesIA) | Hexagonal | Pipeline | LangChain-style | Microkernel |
|-----------|---------------------|-----------|----------|-----------------|-------------|
| **Testability** | ★★★★★ Phonology pure; LLM stubbed | ★★★★ Ports testable | ★★★ Linear flow | ★★ Heavy mocking | ★★★★ Core isolated |
| **Swapability** | ★★★★★ Protocol per backend, Registry | ★★★★ Adapters | ★★ Hard-coupled | ★★★ Chain composition | ★★★★★ Plugin API |
| **LLM independence** | ★★★★★ Never trust LLM for structure | ★★★ Doesn't address | ★★★ Doesn't address | ★ LLM is the core | ★★★ Doesn't address |
| **Safety/guardrails** | ★★★★★ Built-in: phonology rejects | ★ Neutral | ★ Neutral | ★★ Guardrails separate | ★ Neutral |
| **Cold start** | ★★★★★ `import poesia` instant | ★★★★ | ★★★★ | ★★★ Heavy imports | ★★★★ |
| **Adding a backend** | ★★★★★ `@register_llm(name)` | ★★★★ New adapter | ★★★ New stage | ★★★ New chain link | ★★★★★ New module |
| **Adding a metric** | ★★★★★ New ScorerProtocol impl | ★★★ New port | ★★ New pipeline stage | ★★★ New callback | ★★★★ New plugin |
| **Docker/MLflow** | ★★★ Optional, not required | ★★★ | ★★★ | ★★ Required | ★★★ |

## 4. VerifIA vs Industry Patterns

### vs LangChain (agent-based)
LangChain chains LLM calls together. The LLM is the core; guardrails are add-ons.
VerifIA inverts this: **deterministic validation is the core, LLM is a plugin**.

```
LangChain: llm -> tool -> llm -> guardrail -> output
VerifIA:   validator <- llm <- validator <- llm <- validator
```

### vs Guardrails AI
Guardrails validates after LLM output. VerifIA validates **inside the generation loop** --
every line is checked before the next is generated. Catches errors earlier.

### vs Outlines (grammar-constrained)
Outlines constrains tokens at generation time. VerifIA validates after generation.
Both are compatible -- PoesIA supports Outlines as one of its backends.

### vs Traditional rule-based NLP
Rules for structure, LLM for creativity. The best of both worlds.

---

## 5. Quantitative Comparison

| Metric | VerifIA | LLM-only | Rule-based |
|--------|:------------:|:---------:|:----------:|
| Forms supported | **5 + variable** | Unlimited (wrong) | Unlimited (rigid) |
| Rhyme detection | **phonology.rhyme_key()** | None | Perfect |
| Time to add new form | **~10 lines (FormSpec)** | Days prompt engineering | Hours |

Rows removed 2026-10-04 because nothing measured them for this pattern. "Syllable deviation
1.1" and "line count 100%" were the v2 LoRA adapter's results (`docs/ROADMAP.md`,
"Second run"), not results of the verification loop. The LLM-only figures (~3-5, ~60%)
had no source. Emotion (pysentimiento) and imagery (spaCy) scoring run in data-prep
scripts, not in `evaluation/scorer.py`.

---

## 6. Named Layers (-IA family)

```
                PoesIA (core generation)
  EufonIA | GalerIA | MemorIA | ArmonIA | ImagIA
  (sound) | (image) | (RAG)   | (music) | (imagery: galeria/imagery.py, not a scorer)
  ---------------------------------------------------------
                 VerifIA (phonology + scorer)
  ---------------------------------------------------------
  CronologIA  |  AnalogIA  |  More to come
  (MLOps)     |  (A/B)     |

```

---

## 7. Where VerifIA Falls Short

| Weakness | Why | Mitigation |
|----------|-----|------------|
| No LLM-as-judge | Don't ask Groq to rate itself | Manual review |
| No streaming | Line-by-line blocks UI | Not needed for CLI |
| Single language | Python only | Fine for personal |
| Training not automated | CI (`.github/workflows/ci.yml`) runs the tests on 3.13; `train.yml` needs a self-hosted GPU runner that does not exist | Manual train loop |

# PoesIA

[![Python](https://img.shields.io/badge/python-3.11-blue)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-brightgreen)](#)

> *poesía* (Spanish, "poetry") — with **IA** (*Inteligencia Artificial*) already
> hiding inside the word. Nothing invented; just noticed.

A personal hybrid poetry-writing engine: deterministic phonology/prosody validation
anchored to LLM semantic generation, extended into illustration, collections and
music. Later to gain Graph RAG for corpus-aware retrieval and stylistic grounding.

---

## Philosophy

> **LLM**: semantic imagination, metaphor, ambiguity, emotional movement.
> **Algorithms**: metre, rhyme, phonetic pattern, measurable repetition.
> **Human**: taste, necessity, surprise — and whether the poem deserved to exist.

Do not trust the LLM to count syllables, identify stress, or guarantee rhyme.
A language-specific study on Greek poetry found that pure LLM generation produced
fewer than 4 % formally valid poems; adding deterministic phonological verification
raised validity to 73.1 %. The exact numbers do not transfer directly to English or
Spanish, but the architectural lesson is persuasive.

---

## The -IA family

One package, five commands, all sharing the same phonology/evaluation spine.
Each sub-brand is a real Spanish word that already ends in "-ía" — read the
last three letters as **IA**.

| Command | Word (Spanish) | Meaning | Role |
|---|---|---|---|
| `poesia write` / `poesia scan` | *poesía* — poetry | core generation + validation loop |
| `poesia eufonia` | *eufonía* — euphony | **sound** analysis: rhyme, assonance, consonance, how a poem *sounds* |
| `poesia galeria` | *galería* — gallery | **illustration**: auca-style illustrated verse sheets, image generation |
| `poesia memoria` | *memoria* — memory | **collections**: personal library, later the Graph RAG retrieval layer |
| `poesia armonia` | *armonía* — harmony | **music**: prosody → rhythm, symbolic score, sung/recited output |

**Why EufonIA ≠ ArmonIA:** euphony is the pleasantness of *sound itself*
(the acoustic/phonetic layer — rhyme, assonance, cacophony avoidance). Harmony
is the concordant balance *among parts*, and in music specifically the
vertical stacking of notes into chords. EufonIA judges how the words sound;
ArmonIA turns the poem into music. They are neighbors, not synonyms.

---

## Architecture (high-level)

```
┌─────────────────────────────────────────────────────────┐
│                  poesia CLI (Typer)                     │
│      write · scan · eufonia · galeria · memoria · armonia│
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │    Generation Loop           │
          │  (generation/)               │
          │  · generate N candidate lines│
          │  · validate → score → rank   │
          │  · ask LLM to repair defects │
          └───┬──────────────────┬───────┘
              │                  │
   ┌──────────▼──────┐  ┌────────▼────────────┐
   │  Phonology Layer │  │  Evaluation Layer    │
   │  (phonology/)    │  │  (evaluation/)       │
   │  · syllable count│  │  · metre score       │
   │  · stress pattern│  │  · rhyme score       │
   │  · rhyme class   │  │  · theme/semantic    │
   │  · IPA / fonemas │  │  · novelty, cliché   │
   └──────────────────┘  └──────────────────────┘
              │                     │
   ┌──────────▼─────────┐  ┌────────▼────────────┐  ┌──────────────────┐
   │  eufonia/           │  │  galeria/            │  │  armonia/         │
   │  sound analysis,    │  │  image backends,     │  │  prosody→rhythm,  │
   │  consumes phonology │  │  auca layout, PDF     │  │  score/MIDI, TTS  │
   └─────────────────────┘  └──────────────────────┘  └───────────────────┘
                                   │
                    ┌──────────────▼────────────┐
                    │  memoria/ (retrieval)      │
                    │  collections now,          │
                    │  Graph RAG later           │
                    │  · poet style anchors      │
                    │  · semantic neighbourhood  │
                    └────────────────────────────┘
```

---

## Language targets

| Language | Phonology stack | Form recognition |
|----------|----------------|------------------|
| Spanish  | `rantanplan`, `silabeador`, `fonemas`, `phonemizer` | 45 stanza types via rantanplan |
| English  | `pronouncing` + CMUdict, `prosodic`, `phonemizer` (OOV) | iambic pentameter, syllabics, free verse |
| Multilingual | `phonemizer` (eSpeak NG backend), `epitran` (IPA) | — |

See `docs/ARCHITECTURE.md` (Package survey section) for the full package survey, including
illustration and music backends.

---

## Quickstart

```bash
cd /home/angel/dev/poesia
pip install -e ".[dev]"
poesia --help
```

Demo (Spanish hendecasyllable scan):

```bash
poesia scan "En el principio era el Verbo y el Verbo" --language es
```

Demo (generation loop stub, offline via StubLLMClient):

```bash
poesia write --theme "lluvia sobre piedra" --language es --form soneto
```

---

## Roadmap

See `docs/ROADMAP.md`.

**Phase 0 ✅**: Scaffold, phonology validation, all five -IA modules.
**Phase 1 ✅**: LLM candidate generation + reranking loop.
**Phase 2 ✅**: GalerIA (DALL-E/Replicate) + ArmonIA (MIDI/TTS).
**Phase 3 ✅**: Graph RAG in MemorIA, BriefBuilder enrichment, seed expansion.
**Phase 4 ✅**: Real LLM integration, richer influences, GalerIA style anchoring.
**Phase 5 ✅**: P0–P5 hardening: Groq, directive prompts, rhyme tracking, interactive CLI,
              privacy controls, structured errors, index compatibility, evaluation corpus.

### Current capabilities
- **Spanish sinalefa handling** — correct metrical syllable counting with vowel elision
- **Semantic scoring** — theme/novelty via sentence-transformers embeddings
- **Graph RAG** — NetworkX-based semantic retrieval for personal context
- **Multi-language** — Spanish (primary), English, Dutch phonology backends
- **Real LLM backends** — Gemini/OpenAI via `--llm` option (API key required)

---

## Project layout

```
poesia/
├── src/poesia/
│   ├── phonology/       # Language-specific prosody validators (the shared spine)
│   ├── generation/      # LLM orchestration + constrained loop
│   ├── evaluation/      # Scoring functions (metre, rhyme, semantics, novelty)
│   ├── forms/           # Stanza/form definitions and validators
│   ├── eufonia/         # Sound/euphony analysis feature
│   ├── galeria/         # Illustration: image backends, auca layout, PDF export
│   ├── memoria/         # Collections/library; future Graph RAG retrieval
│   ├── armonia/         # Music: prosody→rhythm, score/MIDI, TTS recitation
│   └── cli.py           # Root Typer app mounting all five subcommands
├── tests/               # pytest unit + integration tests
├── docs/                # Architecture, naming rationale, package survey, roadmap
├── notebooks/           # Exploration notebooks
├── scripts/             # One-off tools, demos
└── memory-bank/         # Session continuity files
```

---

## Status

**Phases 0–5 complete + P0–P5 RAG/LLM hardening** (2026-08-01). **400+ tests passing.**

### Recent Updates (2026-08-01)
- ✅ Corpus expanded: 1,059 new poems (Gutenberg + Wikisource) — 601 by Mexican poets
- ✅ Fixed-format dataset builder (38K examples) + v2-fixed retraining (fixes the instruction-echo bug)
- ✅ DPO training complete (loss 0.008, acc 1.0); Model Registry verified
- ✅ Original sonetos in the library: "El peso del saber", "El umbral", RadicleCrops ×6 (13 poems total)
- ✅ MLOps Phases 1–11: MLflow single source of truth, Registry, Docker, CI/CD, monitoring
- ✅ Multi-form training infrastructure (MLOps: config-driven, experiments DB, A/B compare)
- ✅ Grammar-constrained generation via Outlines (`--llm outlines`)
- ✅ LoRA fine-tuning with Qwen2.5-1.5B + QLoRA (`--llm lora`)
- ✅ Real LLM backends: Groq, Gemini, OpenAI (`--llm groq|gemini|openai`)
- ✅ Local offline inference via Ollama (`--llm ollama`)
- ✅ Directive prompts: syllable targets, rhyme word banks, anti-repetition
- ✅ RhymeTracker with per-letter-group commitments + Datamuse/CMUdict word banks
- ✅ Typed graph nodes/edges + bounded traversal with explainable paths
- ✅ Interactive line selection (`--interactive`) and retrieval display (`--show-retrieval`)
- ✅ Privacy confirmation before personal context reaches hosted providers
- ✅ Structured exception hierarchy (`PoesiaError`, 10 subtypes)
- ✅ Embedding profile frozen to `intfloat/multilingual-e5-small` (384-dim)
- ✅ Index compatibility enforcement, atomic writes, source fingerprinting
- ✅ Distillation pipeline (Groq → clean sonetos) for synthetic training data

See `USAGE_GUIDE.md` for complete feature documentation and `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` for the full hardening scope.

---

## Naming rationale

### PoesIA — the hidden pun

*Poesía* is simply the Spanish word for "poetry." Read the last three letters as **IA** (*Inteligencia Artificial* — "AI") and the pun is already there, unforced. Nothing invented.

Every sub-brand follows the same pattern — a genuine Spanish noun ending in "-ía" whose literal meaning matches the module's responsibility (see the -IA family table above).

### Naming search history

Earlier candidates that were explored and rejected:
- **poiesis** (Greek "making") — fine but not bilingual EN/ES-flavored enough
- root+suffix mashups (`coplai`, `rimagraph`, `silvagraph`) — felt mechanical
- "hidden pun in a real word" tricks in English (`SoNNet`) — collides with Anthropic's Claude Sonnet
- movie-pastiche jokes (`Rhymenator`, `Trovatron`) — fun but not durable branding

**PoesIA** won because it is the *exact* real word, works identically in speech and text, and the -IA family pattern reproduces cleanly across every other relevant Spanish "-ía" word.

### PyPI availability

`poesia` is unregistered on PyPI (HTTP 404 at check). Irrelevant unless this repo is ever published — it remains a personal project shared privately by invitation.

---

## License & sharing

**Software** — MIT License, see [`LICENSE`](LICENSE).
**Original creative content** (`seeds/angel_fragments/`, `seeds/library/`) — © the author and **not** covered by the MIT license. See [`NOTICE`](NOTICE).
**Corpus texts** (`seeds/poetry_corpus/`) — public domain (Project Gutenberg, es.wikisource.org); full provenance in [`docs/CORPUS_SOURCES.md`](docs/CORPUS_SOURCES.md).

Contribution standards: [`CONTRIBUTING.md`](CONTRIBUTING.md) · Security: [`SECURITY.md`](SECURITY.md) · History: [`CHANGELOG.md`](CHANGELOG.md)

**Author:** Angel — shared by invitation; contact details are provided personally, never published here.

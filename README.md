# PoesIA

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

See `docs/PACKAGES_SURVEYED.md` for the full package survey, including
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

Phase 0 (now): repo scaffold, phonology validation layer, all five -IA
modules present as documented, importable skeletons.
Phase 1: LLM candidate generation + reranking loop wired to a real backend.
Phase 2: Corpus ingestion + KenLM stylistic prior; GalerIA illustration and
ArmonIA music backends wired to real image/audio generation.
Phase 3: Graph RAG in MemorIA — poet nodes, influence edges, semantic
retrieval.

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

Early scaffold, local-only repo (not pushed to any remote). No production
code yet beyond the phonology/evaluation vertical. See
`memory-bank/tasks.md` for the current Kanban.

# Architecture

## Core principle

> LLM: semantic imagination, metaphor, ambiguity, emotional movement.
> Algorithms: metre, rhyme, phonetic pattern, measurable repetition.
> Human: taste, necessity, surprise, and whether the poem deserved to exist.

The `phonology/` package is the shared spine every other module depends on.
It must never call an LLM — it is the deterministic "ground truth" layer.

## Layering rules

1. **`phonology/`** has zero dependency on any other `poesia` package. It
   scans raw text and returns `ScanResult` / `RhymeKey` / `Stress` — pure
   data, computed deterministically.
2. **`evaluation/`** depends on `phonology/` only. It turns scan results into
   scores (`metre_score`, `rhyme_score`, ...), combined via `composite_score`.
3. **`generation/`** depends on `phonology/` and `evaluation/`. It is the
   *only* package allowed to talk to an LLM, via the `LLMClient` Protocol —
   no concrete SDK import leaks outside `generation/`.
4. **`forms/`** is pure data (`FormSpec` dataclasses) — no behavior, no
   dependencies on the above. Consumed by `generation/` and `evaluation/`.
5. **`eufonia/`** depends on `phonology/` only (it re-analyzes scan results,
   never re-derives phonemes itself).
6. **`galeria/`** depends on nothing from the phonology/generation spine
   directly — it takes already-generated poem text as input. Its own
   `ImageBackend` Protocol (in `galeria/backends.py`) mirrors the
   `LLMClient` seam discipline: no `openai`/`replicate`/`diffusers` import
   outside `galeria/`.
7. **`armonia/`** depends on `phonology/` (for `Stress`/stress patterns via
   `prosody_to_rhythm.py`). Its own backend Protocols (`ScoreBackend`,
   `AudioSynthBackend`, `RecitationBackend`) keep `music21`/`pyfluidsynth`/
   `audiocraft` imports contained to `armonia/backends.py`.
8. **`memoria/`** depends on nothing else at Phase 0-1 (`library.py` is a
   flat in-memory store). Phase 3's `graphrag.py` will additionally depend
   on `sentence-transformers` embeddings, contained the same way.

## The seam discipline (why every backend is a Protocol)

Every place this project touches an external service or heavy dependency —
LLM inference, image generation, music synthesis — is crossed through a
typed `Protocol` with a `Stub*` implementation for offline testing. This is
deliberate, not incidental:

- It means `pip install -e "."` (no extras) gives you a fully importable,
  fully testable package — nothing crashes on missing dependencies until you
  actually call a method that needs one, and then it raises an actionable
  `RuntimeError` naming the exact extra to install.
- It means swapping `openai` for `replicate`, or a hosted LLM for
  `llama-cpp-python`, is a one-file change (the concrete backend), never a
  refactor of the calling code.
- It mirrors the seam discipline already proven useful in adjacent personal
  projects (typed ports for hardware/SDK boundaries).

## Generation loop (the actual algorithm)

```
1. Generate 16-64 candidate lines           (generation/candidate_generator.py)
2. Scan syllables, stress, rhyme            (phonology/{spanish,english}.py)
3. Reject formally impossible candidates    (evaluation/scorer.py)
4. Score semantic continuity and novelty    (evaluation/metrics.py — Phase 1)
5. Detect clichés and repeated patterns     (evaluation/metrics.py)
6. Keep the best few candidates             (evaluation/scorer.py, sorted)
7. Ask the LLM to repair one defect at a time (generation/llm_client.py .repair)
8. Rescan after every revision              (loop back to step 2)
9. Human chooses among surviving lines      (CLI output, human in the loop)
```

Implemented in `generation/constrained_loop.py::ConstrainedLoop.run`, one
line at a time, for `FormSpec.total_lines` iterations.

## Why this is not over-engineered for "just a personal poetry tool"

The five-module (-IA family) split isn't speculative scope creep — each
module maps to something the user explicitly asked for during scoping
(sound analysis, illustration, collections, music), and each stays
importable/testable independently because of the Protocol seam discipline
above. Nothing here requires standing up infrastructure (a database, a GPU,
an API key) to import the package and run its tests.

---

## Package survey

### Phonology / prosody

| Package | Language | Role | Assessment |
|---|---|---|---|---|
| `rantanplan` | ES | metric scansion, ~45 stanza types | Primary Spanish backend |
| `silabeador` | ES | syllabification + stress | Good fallback |
| `fonemas` | ES | phonological transcription | Needed for rhyme validation |
| `pronouncing` + `cmudict` | EN | rhyme, phonemes, stress | Simplest English combo |
| `prosodic` | EN (+ FI) | full metrical parsing, feet | Foot-level scansion |
| `phonemizer` | multi | phoneme via eSpeak NG | Best multilingual layer |
| `epitran` | multi | IPA transcription | Consistent IPA across languages |
| `gruut` | multi | G2P without eSpeak binary | Lighter fallback |
| `g2p_en` | EN | neural G2P backoff | CMUdict OOV words |
| `pyphen` | multi | hyphenation | Cheap syllable count check |
| `CLTK` | Latin/Greek | classical metrical scansion | LLM-validity study reference |

### Linguistic / semantic

| Package | Role |
|---|---|
| `spaCy` | lemmatization, POS, dependency parsing (ES+EN) |
| `sentence-transformers` | semantic similarity, reranking |
| `wn` / NLTK WordNet | semantic relations |
| `wordfreq` | lexical-frequency prior |
| `python-datamuse` | interactive rhyme/near-rhyme discovery |
| `markovify` | Markov-chain baseline sanity check |

### LLM generation / constrained decoding

| Package | Role |
|---|---|
| `transformers` | local inference, custom LogitsProcessor |
| `llama-cpp-python` | C++ inference, GBNF grammars |
| `guidance` / `outlines` | constrained generation (regex/schema) |

### Illustration (GalerIA)

| Package | Role |
|---|---|
| `openai` | DALL-E / gpt-image API |
| `replicate` | hosted SDXL + specialized models |
| `diffusers` | local SDXL |
| `Pillow` | raster compositing, text stamping |
| `svgwrite` / `drawsvg` | vector illustration |
| `weasyprint` | HTML/CSS to PDF |

### Music (ArmonIA)

| Package | Tier | Role |
|---|---|---|
| `music21` | symbolic | stress pattern to rhythm, MusicXML/MIDI |
| `pretty_midi` / `mido` | symbolic | raw MIDI manipulation |
| `pyfluidsynth` + .sf2 | audio | render MIDI to audio |
| `audiocraft` | AI generation | local text to music |
| `piper` | TTS | fast local TTS |
| Coqui `TTS` | TTS | local TTS (heavier) |

### Graph RAG storage

| Option | Tradeoff |
|---|---|
| `networkx` (in-memory) | Zero infra, fast, does not scale past personal corpus |
| `neo4j` | Real graph DB, adds infra dependency |

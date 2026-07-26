# Packages surveyed

This is the accumulated package survey behind PoesIA's design, split by
concern. "Assessment" notes reflect a second, independent pass beyond the
packages the user had already researched, to check for gaps.

## Phonology / prosody

| Package | Language | Role | Assessment |
|---|---|---|---|
| `rantanplan` | ES | metric scansion, ~45 stanza types | Primary Spanish backend — most complete option found. |
| `silabeador` | ES | syllabification + stress, lower-level | Good fallback when rantanplan's higher-level API is insufficient. |
| `fonemas` | ES | phonological transcription | Needed for rhyme validation under historical/dialectal spelling. |
| `pronouncing` + `cmudict` | EN | rhyme, phonemes, stress | Simplest, most reliable English combination. Primary backend. |
| `prosodic` | EN (+ FI) | full metrical parsing, feet | Only option found for real foot-level scansion, not just syllable counts. |
| `phonemizer` | multi | phoneme sequences via eSpeak NG/Festival | Best pragmatic multilingual layer; requires eSpeak NG binary. |
| `epitran` | multi | IPA transcription | Consistent IPA across languages, complements phonemizer. |
| `gruut` *(added)* | multi | G2P without requiring the eSpeak binary | Lighter-weight fallback when installing eSpeak system-wide is impractical (e.g. constrained deploy targets). |
| `g2p_en` *(added)* | EN | neural G2P backoff | Complements `pronouncing` for CMUdict out-of-vocabulary words; standard pairing in TTS pipelines. |
| `pyphen` *(added)* | multi | hyphenation (OpenOffice dictionaries) | Cheap cross-language syllabification sanity check beyond ES/EN. |
| `CLTK` *(added)* | Latin/Greek | classical metrical scansion | Directly relevant: the LLM-validity study cited in the README was on **Greek** poetry. Worth knowing even if not wired immediately. |

## Linguistic / semantic

| Package | Role | Assessment |
|---|---|---|
| `spaCy` | lemmatization, POS, dependency parsing (ES+EN) | Confirmed good fit for syntactic-variation / enjambment detection. |
| `sentence-transformers` | semantic similarity, reranking | Needed for `theme_score`/`novelty_score` (currently stubbed). |
| `wn` / NLTK WordNet | semantic relations (synonym/hypernym/etc.) | For controlled lexical exploration, not naive synonym substitution. |
| `wordfreq` | lexical-frequency prior | Caveat: frequency snapshot only through ~2021 — a prior, not a live monitor. |
| `python-datamuse` *(added)* | interactive rhyme/near-rhyme/semantic word discovery | Thin wrapper around the free Datamuse API; complements WordNet for exploratory word-finding. |
| `markovify` *(added)* | Markov-chain text generation | Not for production generation — useful only as a cheap statistical baseline to sanity-check LLM output quality against. |

## LLM generation / constrained decoding

| Package | Role | Assessment |
|---|---|---|
| `transformers` | local inference, custom LogitsProcessor | Token-level metre enforcement is hard (subwords ≠ syllables); line-level generation + reranking is cleaner in practice. |
| `llama-cpp-python` | Python binding to llama.cpp | The clear C++ inference choice once local/offline inference is needed; supports GBNF grammars. |
| `guidance` / `outlines` | constrained generation (regex/schema/grammar) | Good for structural container constraints (stanza shape); not naturally suited to phonological constraints (those need the phonology layer, not a character grammar). |

## Illustration (GalerIA)

| Package | Role | Assessment |
|---|---|---|
| `openai` | DALL·E / gpt-image API | Agreed — good default hosted backend, strong style control via prompting. |
| `replicate` | hosted SDXL + specialized models | Agreed — cheaper than OpenAI, access to woodcut/line-art models suited to a "grabado español" auca aesthetic. |
| `diffusers` (HuggingFace) | local SDXL | Agreed as the offline/local alternative; GPU-heavy, kept as a separate `illustration-local` extra. |
| `Pillow` | raster compositing, text stamping | Agreed — correct backbone choice for pairing image + verse. |
| `svgwrite` / `drawsvg` *(added)* | vector illustration | Not in the user's original list — needed if scalable print-quality auca sheets are wanted instead of fixed-resolution raster. |
| `weasyprint` | HTML/CSS → PDF | Chosen over `fpdf2`/`ReportLab` for typography quality when exporting a full illustrated poetry book. |
| Noto Serif / EB Garamond (fonts, not packages) *(added)* | diacritic-complete typeface | Real gotcha: narrow Latin-1 fonts mishandle Spanish á/í/ñ when stamped via Pillow's `ImageFont`. |
| `Fabric.js` | interactive web canvas | Deferred — only relevant if/when a web frontend exists. Not part of Phase 0-2 (Python-only). |

## Music (ArmonIA)

| Package | Tier | Role | Assessment |
|---|---|---|---|
| `music21` | symbolic | stress pattern → rhythm, MusicXML/MIDI | Best fit for the prosody→rhythm bridge that makes ArmonIA a natural phonology extension rather than a bolt-on. |
| `pretty_midi` / `mido` | symbolic | raw MIDI manipulation | Lower-level fallback/complement to music21. |
| `pyfluidsynth` + a `.sf2` SoundFont | audio | render MIDI → audio | Simplest path from symbolic score to actual sound. |
| `audiocraft` (Meta MusicGen) | AI generation | local text→music | Real open local option; heavier dependency, kept as a separate `music-ai` extra. |
| Suno / Udio | AI generation | hosted | Noted but not adopted — commercial, limited/no public API access at present. |
| `piper` | TTS/recitation | fast local TTS | Preferred local recitation backend once needed. |
| Coqui `TTS` | TTS/recitation | local TTS | Alternative to piper, heavier. |
| eSpeak NG (via `phonemizer`, already a dependency) | TTS/recitation | free, low-quality fallback | Cheapest possible recitation path — no new dependency, since `phonology-multi` already wraps it. |

## Multilingual text infrastructure (not yet wired, noted for later)

| Package | Role |
|---|---|
| `ICU4C` | robust Unicode boundary analysis, combining marks, non-Latin scripts — matters once support extends past ES/EN accented Latin script. |
| `OpenFst` / `Pynini` | weighted finite-state transducers — a formal grammar-based metrical validator, only justified if constraint-search complexity grows significantly beyond the current scan-then-score approach. |
| `KenLM` | fast C++ n-gram LM | cheap stylistic prior / cliché detector against a period-or-poet-specific corpus (Phase 2). |

## Graph RAG storage (Phase 3, undecided)

| Option | Tradeoff |
|---|---|
| `networkx` (in-memory) | Zero infra, fast to prototype, does not scale past a modest personal corpus, no persistence built in. |
| `neo4j` | Real graph database, persistent, query language (Cypher) suited to influence/style-neighbourhood queries; adds an infra dependency (a running Neo4j instance) that a personal project may not want yet. |

Decision deliberately deferred — see `docs/ROADMAP.md` Phase 3.

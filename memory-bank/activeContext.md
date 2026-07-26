# Active Context — PoesIA

_Last updated: Phase 2 completion (GalerIA illustration, ArmonIA MIDI music & TTS, Spanish phonology)._

## What We Just Did

1. **Phase 1 Infrastructure**:
   - `HostedLLMClient` (Gemini & OpenAI REST APIs), repository `AGENTS.md` guardrails, `EuphonyAnalyzer` rhyme scheme & sound analysis, `MemorIA` Markdown YAML frontmatter disk persistence (`~/.poesia/poems/*.md`) + SQLite auto-index, `theme_score`/`novelty_score` baseline vector math.

2. **GalerIA Illustration Engine (`HostedImageBackend` & `AucaComposer`)**:
   - Implemented `HostedImageBackend` supporting OpenAI DALL-E 3 & Replicate SDXL APIs with default `traditional spanish woodcut line-art, engraving style` prompt styling.
   - Implemented Pillow `AucaComposer.compose_panel()` (card rendering with image + centered caption text) and `compose_sheet()` (multi-panel 2-column grid layout).
   - Added unit tests in `tests/test_galeria.py`.

3. **ArmonIA Music & Recitation Engine (`MidiScoreBackend` & `EspeakRecitationBackend`)**:
   - Implemented pure Python `MidiScoreBackend` converting prosodic `Stress` patterns into standard binary MIDI (`.mid`) scores.
   - Implemented `EspeakRecitationBackend` wrapping `espeak-ng`/`espeak` for audio recitation.
   - Added unit tests in `tests/test_armonia_backends.py`.

4. **Spanish Phonology (`SpanishPhonology`)**:
   - Implemented `SpanishPhonology.rhyme_key()` (consonant & assonant rhyme extraction) and `classify_stanza()` (stanza form classification).
   - Added unit tests in `tests/test_phonology_spanish.py` (all **48 unit tests** passing in `0.76s`).

## Current Focus

Phase 2 features are complete and fully tested! Next focus area (Phase 3):

1. Land Graph RAG storage decision (NetworkX graph vs. Neo4j).
2. Implement `GraphRAGRetriever.ingest` / `.retrieve` in `src/poesia/memoria/graphrag.py`.

## Open Questions

- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred to Phase 3 per `docs/PACKAGES_SURVEYED.md`.
- CLI-only focus (no web frontend planned for Phase 1/2).


## Open Questions

- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred to Phase 3 per `docs/PACKAGES_SURVEYED.md`.
- CLI-only focus (no web frontend planned for Phase 1/2).



## Open Questions

- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred to Phase 3 per `docs/PACKAGES_SURVEYED.md`.
- CLI-only focus (no web frontend planned for Phase 1/2).



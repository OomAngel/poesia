# Active Context — PoesIA

_Last updated: Phase 1 completion (LLM client, sound analysis, poem storage, evaluation metrics)._

## What We Just Did

1. **Phase 1 LLM Backend (`HostedLLMClient`)**:
   - Implemented `HostedLLMClient` in `src/poesia/generation/llm_client.py` supporting Gemini (`gemini-2.5-flash`) and OpenAI (`gpt-4o-mini`) REST APIs via stdlib `urllib` and environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`).

2. **Repository Guardrails & Instructions (`AGENTS.md`)**:
   - Created `AGENTS.md` documenting commit standards (Conventional Commits, test before commit, logical blocks), local-only git discipline, layering rules, and session lifecycle.

3. **EufonIA Sound Analysis (`EuphonyAnalyzer`)**:
   - Implemented `EuphonyAnalyzer.analyze()` and `detect_rhyme_scheme()` in `src/poesia/eufonia/analyzer.py` for rhyme scheme inference (e.g. `ABAB`), assonance density, consonance density, and sibilance/cacophony flags.

4. **MemorIA Library Persistence (`Library`)**:
   - Implemented human-readable **Markdown files with YAML frontmatter** (`~/.poesia/poems/*.md`) persistence in `src/poesia/memoria/library.py` alongside a background **SQLite auto-index** (`library.db`).

5. **Evaluation Metrics Baseline (`theme_score` & `novelty_score`)**:
   - Implemented pure Python vector math baseline (cosine similarity and distance) for `theme_score` and `novelty_score` in `src/poesia/evaluation/metrics.py`.
   - All **38 unit tests** passing in `0.07s`.

## Current Focus

Phase 1 features are complete and fully tested! Next focus area (Phase 2):

1. `GalerIA` illustration backend integration (Pillow + WeasyPrint PDF layout).
2. `ArmonIA` score and audio synthesis (`music21` / eSpeak NG recitation).
3. Spanish rhyme key classification (`SpanishPhonology.rhyme_key`).

## Open Questions

- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred to Phase 3 per `docs/PACKAGES_SURVEYED.md`.
- CLI-only focus (no web frontend planned for Phase 1/2).



## Open Questions

- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred to Phase 3 per `docs/PACKAGES_SURVEYED.md`.
- CLI-only focus (no web frontend planned for Phase 1/2).



# Active Context — PoesIA

_Last updated: Phase 1 MemorIA library disk persistence completion._

## What We Just Did

1. **Phase 1 LLM Backend (`HostedLLMClient`)**:
   - Implemented `HostedLLMClient` in `src/poesia/generation/llm_client.py` supporting Gemini (`gemini-2.5-flash`) and OpenAI (`gpt-4o-mini`) REST APIs via stdlib `urllib` and environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`).
   - Added unit tests in `tests/test_generation_llm_client.py`.

2. **Repository Guardrails & Instructions (`AGENTS.md`)**:
   - Created `AGENTS.md` documenting commit standards (Conventional Commits, test before commit, logical blocks), local-only git discipline, layering rules, and session lifecycle.

3. **EufonIA Sound Analysis (`EuphonyAnalyzer`)**:
   - Implemented `EuphonyAnalyzer.analyze()` and `detect_rhyme_scheme()` in `src/poesia/eufonia/analyzer.py` for rhyme scheme inference (e.g. `ABAB`), assonance density, consonance density, and sibilance/cacophony flags.

4. **MemorIA Library Persistence (`Library`)**:
   - Implemented human-readable **Markdown files with YAML frontmatter** (`~/.poesia/poems/*.md`) persistence in `src/poesia/memoria/library.py` alongside a background **SQLite auto-index** (`library.db`).
   - Updated unit tests in `tests/test_memoria_library.py` (32 passing tests).

## Current Focus

Proceed with Phase 1 tasks:

1. Add `sentence-transformers` for `theme_score` and `novelty_score` in `src/poesia/evaluation/metrics.py` (lazy-imported behind try-except block).


## Open Questions

- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred to Phase 3 per `docs/PACKAGES_SURVEYED.md`.
- CLI-only focus (no web frontend planned for Phase 1/2).



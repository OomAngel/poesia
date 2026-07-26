# Active Context — PoesIA

_Last updated: Phase 1 HostedLLMClient & repository guardrails completion._

## What We Just Did

1. **Phase 1 LLM Backend (`HostedLLMClient`)**:
   - Implemented `HostedLLMClient` in `src/poesia/generation/llm_client.py` supporting Gemini (`gemini-2.5-flash`) and OpenAI (`gpt-4o-mini`) REST APIs via stdlib `urllib` and environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`).
   - Added unit tests in `tests/test_generation_llm_client.py` (28 passing tests).

2. **Repository Guardrails & Instructions (`AGENTS.md`)**:
   - Created `AGENTS.md` documenting commit standards (Conventional Commits, test before commit, logical blocks), local-only git discipline, layering rules, and session lifecycle.

3. **Phase 1 Alignment (`/grill-me`)**:
   - Aligned Phase 1 roadmap: Hosted LLM client → `EuphonyAnalyzer.analyze()` → Markdown+YAML frontmatter with SQLite background index for `MemorIA` → `sentence-transformers` extended evaluation metrics.

## Current Focus

Proceed with Phase 1 tasks:

1. Implement `EuphonyAnalyzer.analyze()` in `src/poesia/eufonia/analyzer.py` (rhyme schemes, assonance/consonance scoring).
2. Implement human-readable Markdown + YAML frontmatter persistence with background SQLite auto-index in `src/poesia/memoria/library.py`.
3. Add `sentence-transformers` for `theme_score` and `novelty_score` in `src/poesia/evaluation/metrics.py`.

## Open Questions

- Graph RAG storage backend (networkx vs. neo4j) explicitly deferred to Phase 3 per `docs/PACKAGES_SURVEYED.md`.
- CLI-only focus (no web frontend planned for Phase 1/2).


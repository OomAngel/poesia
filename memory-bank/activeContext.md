# Active Context — PoesIA

_Last updated: 2026-07-27 — End of session. P0 + P1 complete. Next: P2._

---

## Instant re-entry checklist

```bash
cd /home/angel/dev/poesia
conda activate poesia
python -m pytest tests/ --tb=no -q   # should say 285 passed
export GROQ_API_KEY=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
```

Quick sanity test:
```bash
poesia write --theme "luna sobre el mar" --form haiku --language es --llm groq --n-candidates 3
```

---

## What was completed this session (Phase 5)

| Sub-phase | What shipped |
|---|---|
| 5A Groq | --llm groq, GROQ_API_KEY, sequential n calls, User-Agent fix, rate-limit delay |
| 5B Prompts | Syllable target + numbered priors + output-only rule + anti-repetition per line |
| 5C Rhyme | RhymeTracker commits keys; RhymeFetcher word bank (Datamuse/CMUdict/ES offline) |
| 5D P1 | memoria list/search real; --show-retrieval; --interactive with typed-own-line |
| Docs | USAGE_ISSUES all done, RAG plan updated, ROADMAP Phase 5 added, this file rewritten |

285 tests passing. Last commit: 90f4b79

---

## Key source files

- src/poesia/generation/constrained_loop.py — Loop; line_selector= callback; RhymeTracker wired
- src/poesia/generation/candidate_generator.py — Directive prompts with rhyme + syllable
- src/poesia/generation/rhyme_tracker.py — Per-letter-group rhyme commitment + word bank
- src/poesia/generation/rhyme_fetcher.py — Datamuse + CMUdict + offline ES suffix match
- src/poesia/generation/llm_client.py — Gemini / OpenAI / Groq backends
- src/poesia/cli.py — All flags including --interactive, --show-retrieval
- src/poesia/memoria/library.py — Real Markdown+SQLite library

---

## What to do next: P2 (Graph structure)

Authority: docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md section 12, P2

Four tasks in order:

1. Typed nodes and relations in GraphRAGRetriever / records.py
   - NodeType enum: poem, fragment, influence, seed, theme
   - RelationType enum: similar_to, inspired_by, explores, contains

2. Bounded graph expansion: traverse N hops along typed edges with a budget cap;
   return path + endpoints (not just endpoints)

3. --show-retrieval path extension: show graph path in retrieval output:
   pattern-finder -[similar_to 0.82]-> hound -[inspired_by]-> Garcia Lorca

4. Dense vs graph comparison: same theme twice, compare brief content.
   This is the evidence gate the hardening plan requires.

Key files for P2:
- src/poesia/memoria/graphrag.py — NetworkX implementation to extend
- src/poesia/memoria/records.py — add typed enums
- src/poesia/generation/brief_builder.py — extend to call graph retrieval
- tests/test_memoria_graphrag.py — existing tests to extend

Do NOT start P3/P4/P5 before P2 evidence gate is passed.

---

## Known rough edges (not bugs)

- Groq soneto sometimes repeats: word bank helps; use --n-candidates 5+ for variety
- Metre not always exact: repair loop helps; phoneme-level constraints are P3+
- --interactive with Groq is slow: 2.1s x n per line; reduce --n-candidates or upgrade tier
- romance form has no default line count: known incomplete spec, deferred

---

## Document authority map

- What to build next: docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md section 12
- Phase history: docs/ROADMAP.md
- Kanban: memory-bank/tasks.md
- CLI usage: USAGE_GUIDE.md
- Original issues (historical, all done): USAGE_ISSUES.md
- Architecture rules: docs/ARCHITECTURE.md
- Package survey: docs/PACKAGES_SURVEYED.md

# Tasks — PoesIA (Kanban)

## DONE (Phase 0 & Phase 1 Initial)

- [x] Scaffold project (pyproject.toml, .gitignore, README)
- [x] `phonology/` — base dataclasses (Stress, Syllable, RhymeKey, ScanResult)
- [x] `evaluation/` — metre_score, rhyme_score, cliche_penalty functional
- [x] `forms/` — FormSpec + registry (soneto, romance, sonnet_shakespearean, haiku)
- [x] `generation/` — LLMClient Protocol + StubLLMClient, CandidateGenerator, ConstrainedLoop
- [x] `eufonia/` / `galeria/` / `armonia/` / `memoria/` skeletons & CLI subcommands
- [x] Docs: ARCHITECTURE.md, ROADMAP.md, NAMING.md, PACKAGES_SURVEYED.md
- [x] memory-bank/ continuity files & initial unit tests
- [x] `generation/` — `HostedLLMClient` (Gemini REST & OpenAI REST API backends via stdlib urllib)
- [x] `AGENTS.md` — guidelines, guardrails, and commit standards
- [x] `eufonia/` — `EuphonyAnalyzer.analyze()` & `detect_rhyme_scheme()` implemented
- [x] `memoria/` — `Library` Markdown YAML frontmatter storage (`~/.poesia/poems/*.md`) + SQLite auto-index

## IN PROGRESS

- [ ] Implement `theme_score`/`novelty_score` using `sentence-transformers` in `src/poesia/evaluation/metrics.py`

## BACKLOG (Phase 1)

- [ ] Implement `SpanishPhonology.rhyme_key` / `classify_stanza`
- [ ] Expand test coverage as each component matures


## BLOCKED

- [ ] `memoria/graphrag.py` — blocked on storage backend decision (Phase 3)
- [ ] `galeria/auca.py` compose_panel/compose_sheet/export_pdf — blocked on Phase 2
- [ ] `armonia` real backends (music21/pyfluidsynth/TTS) — blocked on Phase 2



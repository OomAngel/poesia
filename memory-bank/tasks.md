# Tasks — PoesIA (Kanban)

## IN PROGRESS

(None — session ending, see activeContext.md for what to run next)

## BACKLOG

- [ ] Complete full training run with composite loss + MLflow tracking
- [ ] Run experiment grid: CE vs Composite vs DPO
- [ ] Train on Ruli-3B (Spanish-native model)
- [ ] Try Unsloth for 2x faster training
- [ ] Wire Model Registry aliases ("champion" / "challenger")
- [ ] Phase 4E: literary taxonomy auto-tagging
- [ ] Wire retrieval into GalerIA for illustration style anchoring
- [ ] WordNet Spanish (omw-es:1.4) — retry when server is up
- [ ] Security linting: fix bandit issues (subprocess, try-except-pass, urlopen)
- [ ] Snapshot tests for CLI + generation pipeline

## DONE

All phases P0-P5 complete (400+ tests passing):
- Core phonology, evaluation, forms, generation loop
- eufonia, galeria, armonia sub-brands
- memoria Library (Markdown + SQLite), real CLI list/search
- GraphRAGRetriever: typed nodes/edges, traverse(), retrieve_with_paths()
- BriefBuilder wired to retriever
- All 6 LLM backends (stub, groq, gemini, openai, ollama, outlines)
- PoetryTrainer with composite loss (pre-computed weights, not live scorer)
- MLflow: autolog, tracing, genai.evaluate, model registry, SQLite backend
- VerifIA architecture pattern documented and benchmarked
- CronologIA Docker stack (Postgres + MLflow)
- Emotion analysis (pysentimiento + NRC lexicon)
- Imagery extraction + image prompt builder
- DPO training script
- Experiment grid automation
- Documentation consolidated from 26 to 14 files

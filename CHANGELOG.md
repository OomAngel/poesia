# Changelog

All notable changes to PoesIA. Milestones derived from `memory-bank/tasks.md`
and git history (125+ commits, single author).

## 2026-08-03 — Share-ready repo + GalerIA end-to-end

- **GalerIA wired end-to-end**: `poesia galeria illustrate` generates one image
  per stanza (auca sheets) with real backend selection (`auto | stub | openai |
  replicate`), imagery extraction, style anchoring, PNG sheet + WeasyPrint PDF
  export; `poesia write --illustrate` produces a sheet alongside the poem
- **Pro-grade README** rewrite (features, quickstart, GalerIA walkthrough,
  architecture, extras table, license)
- Lint pass committed: ruff format on `src/ mlops/`, bandit/mypy tooling config,
  CI gates (`ruff format --check`, bandit skip flags, `phonology-extra` extras)
- Hosted-LLM tests aligned with the P5.3 structured-exception hierarchy
  (`LLMProviderError`); Dutch phonology tests skip gracefully without pyphen
- Suite: 431 tests passing

## 2026-08-01 — Corpus expansion + v2-fixed retraining

- 19 new corpus files, 1,059 new poems (Project Gutenberg + Wikisource);
  601 poems by Mexican poets (Nervo, López Velarde, Sor Juana, Acuña, Sabines, Paz…)
- `scripts/build_fixed_dataset.py` → 38K training / 2K eval examples matching
  the inference prompt exactly (fixes the instruction-echo bug)
- DPO training finished (loss 0.008, acc 1.0)
- Original sonetos added to the library: "El peso del saber", "El umbral",
  RadicleCrops ×6 (ES/EN) — library at 13 poems
- Model Registry re-linked to migrated runs (3 models verified)

## 2026-07-30 — MLOps consolidation + gap-fixing sprint

- MLflow is the single source of truth (dual JSONL tracking removed)
- Fixed structural `start_run()` bug (params were logged, metrics were not)
- Fixed garbage `train_runtime_s` values (nanoseconds logged as seconds)
- MLOps Phases 1–11 complete: autologging, Model Registry, nested evaluation
  runs, data versioning, pyfunc wrapper, Optuna HPO, Docker, CI/CD, monitoring,
  git tags (v1.0–v1.2)
- Env automation: `scripts/poesia_env.sh`, `scripts/launch_training.sh`
- GPU memory leak fixed; CLI crash fixed; 3B adapter + Outlines 3B support

## 2026-07-28 — P0–P5 RAG/LLM hardening complete

- 6 LLM backends (stub, groq, gemini, openai, ollama, outlines)
- Grammar-constrained generation via Outlines; LoRA fine-tuning (Qwen2.5 + QLoRA)
- Directive prompts, RhymeTracker, typed Graph RAG, explainable retrieval paths
- Interactive CLI, privacy confirmation, structured exceptions
- Embedding profile frozen (`intfloat/multilingual-e5-small`, 384-dim);
  distillation pipeline (Groq → clean sonetos)

## 2026-07-25/27 — Core engine (Phases 0–5)

- Phonology/prosody spine (Spanish sinalefa handling; EN/ES/NL backends)
- Evaluation layer (metre, rhyme, theme, novelty)
- All five -IA modules: write/scan, eufonia, galeria, memoria, armonia
- CLI (Typer) with 9 registered backends; 400+ tests

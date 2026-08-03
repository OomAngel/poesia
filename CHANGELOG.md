# Changelog

All notable changes to PoesIA. Milestones derived from `memory-bank/tasks.md`
and git history (125+ commits, single author).

## 2026-08-03 — Free image-gen provider research + Pollinations backend

- **`docs/IMAGE_GENERATION_PROVIDERS.md`**: 8-criterion weighted ranking (cost,
  friction, ergonomics, quality, determinism, reliability, rate, privacy) of 6
  free/low-cost providers — verdict: **Pollinations #1 (4.15/5)**, Cloudflare
  Workers AI, Gemini free tier and AI Horde tied #2 (3.60), credit platforms and
  HF Inference trailing. Includes live probe log and honest gaps
- **`PollinationsImageBackend`** (`--backend pollinations`): free, key-less,
  single-GET online image generation; deterministic prompt-derived seed; stdlib
  urllib; graceful RuntimeError → suggests `--backend procedural`
- **Live-tested 2026-08-03** (this is why we test): Sana pipeline rejected our
  seed (`Too big: expected number to be <=2147483647`) — a mocked test could
  not have caught it. Fixed by masking `& 0x7FFFFFFF`. Verified end-to-end:
  2-stanza auca sheet composed live (1.3 MB PNG), and same prompt+seed ⇒
  **byte-identical images** (service-level determinism)
- `--backend auto` stays offline-first (procedural); pollinations is explicit
- Suite: 447 → **456 tests passing** (9 new pollinations tests)

## 2026-08-03 — mypy gate green (54 type errors fixed)

- **Root cause**: numpy 2.5 ships PEP 695 stubs (Python 3.12 `type` syntax);
  mypy ran with `python_version = "3.11"` and hard-aborted on parse, **hiding
  54 real type errors** across 12 files. Bumped mypy target to 3.12 (gates
  only *allowed syntax*, runtime still supports 3.11) and fixed every error:
  - `PhonologyBackend` Protocol added to `phonology/base.py` (was imported but
    never defined); CLI + RhymeTracker type against it
  - BriefBuilder `level` casts to `Literal["minimal","standard","maximal"]`
  - `Library.storage_dir` normalised through `Path()` at file-write sites
  - `Scorer`: `_prior_embeddings` widened; `composite_score(**breakdown)` typed
  - seed_expander / llm_client / model_wrapper / poetry_trainer: lazy-import
    attributes (`_model`, `_tokenizer`, `_nlp`) typed `Any`, `nn.Module.device`
    and `batch_decode` targeted ignores, dead duplicated `raise` removed
  - GalerIA: font union, float/int variable names, PIL conversion for
    `mlflow.log_image`
- **Verified**: `mypy src/` → Success (0 errors), ruff check/format clean,
  full suite exit 0 (447 tests)

## 2026-08-03 — GalerIA offline backend + README showcase

- **`ProceduralImageBackend`** (`--backend procedural`): deterministic offline
  generative art rendered with Pillow — palette + composition seeded from the
  poem's imagery, no API key, reproducible bit-for-bit. `--backend auto` now
  falls back to it instead of a 1×1 stub pixel
- **Library**: `Library.get()` fixed (PoemRecord `content` mirror — it was
  raising `TypeError`, breaking `galeria illustrate --from-library`);
  `Library.attach_image()` persists `image:` in the poem's YAML frontmatter
  after `poesia write --illustrate --save`
- **CLI**: `galeria illustrate` now strips YAML frontmatter from `.md` poem
  files; MLflow best-effort logging no longer banners the file-store warning
- **README**: Showcase section featuring a real generated auca sheet
  (`docs/examples/auca_el_peso_del_saber.png`), 9 badges, procedural-backend
  walkthrough
- Suite: 431 → **447 tests passing** (16 new: procedural backend, attach_image,
  `get()` round-trip, markdown frontmatter stripping)

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

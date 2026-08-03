# Security Policy

## Reporting a vulnerability

PoesIA is a private, personal project shared by invitation. If you have been
given access and you find a security issue, report it through the same private
channel the project was shared with you — do **not** open a public issue.

## Secrets & credentials

- Real secrets (`.env_mlflow`, API keys, private keys) are gitignored and must
  never be committed. Only `.env_mlflow.example` (placeholders) is tracked.
- Hosted LLM backends (Groq, Gemini, OpenAI) require API keys via environment
  variables only.
- The CLI prompts for explicit confirmation before any personal context is sent
  to hosted providers (`--yes` to skip).

## Dependency hygiene

- `ruff`, `mypy`, `bandit`, and `safety` are part of the dev toolchain and the
  CI quality gate (see `.github/workflows/ci.yml`).
- Heavy/optional dependencies are isolated behind `pip install -e ".[extra]"`
  extras (see `pyproject.toml`) and are lazy-imported at runtime.

## Model & data artifacts

- Large artifacts (`models/`, `mlruns/`, `mlops/data/`, corpus raw downloads)
  are untracked build outputs and are excluded from share bundles by
  `scripts/package_share.sh`.

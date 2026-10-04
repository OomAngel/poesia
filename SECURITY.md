# Security Policy

## Reporting a vulnerability

PoesIA is a personal project in a public GitHub repository
([OomAngel/poesia](https://github.com/OomAngel/poesia)). If you find a security
issue, report it privately to the author — do **not** open a public issue.

## Secrets & credentials

- Real secrets (`.env`, `.env_mlflow`, API keys, private keys) are gitignored and
  must never be committed. Tracked: the placeholder files `.env.example` and
  `.env_mlflow.example`, and the SOPS-encrypted `secrets/poesia.env.sops.yaml`
  (`secrets/README.md`).
- Hosted LLM backends (Groq, Gemini, OpenAI) require API keys via environment
  variables only.
- The CLI prompts for explicit confirmation before any personal context is sent
  to hosted providers (`--yes` to skip).

## Dependency hygiene

- `ruff`, `mypy` and `bandit` gate CI (`.github/workflows/ci.yml`); `safety` runs
  there but only reports. `.github/workflows/dependency-audit.yml` runs
  `pip-audit`, and the pre-commit workflow runs the `no-plaintext-secrets` hook.
- Heavy/optional dependencies are isolated behind `pip install -e ".[extra]"`
  extras (see `pyproject.toml`) and are lazy-imported at runtime.

## Model & data artifacts

- Model weights (`models/`) and the poetry corpus (`seeds/poetry_corpus/`) are
  DVC-tracked, never in git; `mlruns/` and `mlops/data/` are gitignored generated
  output. None of them enters a share bundle (`scripts/package_share.sh` archives
  tracked files only).
- The repository is public: poems and corpus data must never be committed, and
  `.dockerignore` keeps `seeds/poetry_corpus/` and `mlops/data/` out of the images.

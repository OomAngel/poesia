# Contributing to PoesIA

PoesIA is a personal, private repository shared by invitation. This guide
documents the standards for the author and any explicitly invited collaborator.

## Environment

The project uses a conda environment named `poesia` (see `environment.yml`).
For automatic detection and activation:

```bash
source scripts/poesia_env.sh --source
```

## Development loop

1. Create a topic branch: `git switch -c feat/your-change`
2. Make small, single-purpose commits following **Conventional Commits**:
   - `feat(<scope>): description`
   - `fix(<scope>): description`
   - `docs(<scope>): description`
   - `test(<scope>): description`
   - `refactor(<scope>): description`
3. Never mix unrelated changes in one commit.

## Quality gates

Before committing, from the repository root:

```bash
pytest                          # must pass (400+ tests)
ruff check src/ mlops/
mypy src/ --ignore-missing-imports
```

## Architecture & seam discipline

- `phonology/` is pure and deterministic — no LLM or network calls.
- `evaluation/` scoring functions are pure or self-contained.
- Feature modules (`eufonia`, `galeria`, `memoria`, `armonia`) depend on
  abstract `Protocol` backends (`LLMClient`, `ImageBackend`, `ScoreBackend`),
  never on vendor SDKs directly.
- Heavy ML/audio/image libraries must be lazy-imported behind try-except blocks
  with actionable `RuntimeError` messages pointing to `pip install -e ".[extra]"`.

## Sharing rules

- Do not push to any remote or publish any part of this repository without the
  author's explicit instruction.
- Original creative content in `seeds/angel_fragments/` and `seeds/library/` is
  NOT under the MIT license — see `NOTICE`. Do not copy or redistribute it.

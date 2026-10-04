# Contributing to PoesIA

PoesIA is a personal project in a public GitHub repository
([OomAngel/poesia](https://github.com/OomAngel/poesia)). This guide documents the
standards for the author and any collaborator.

## Environment

The project uses a conda environment named `poesia`: `environment.yml` (hardware-neutral
base) plus `requirements/<tier>.txt` for the machine's GPU, built by `scripts/env.sh create`
(README.md "Machines"). For automatic detection and activation:

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
pytest                          # must pass (519 locally, 2026-10-04)
ruff check src/ mlops/
ruff format --check src/ mlops/
mypy src/ --ignore-missing-imports
```

CI (`.github/workflows/ci.yml`) runs the same checks plus bandit, and a separate
pre-commit workflow.

## Architecture & seam discipline

The layering and lazy-import rules are in `AGENTS.md` §3.

## Sharing rules

- Push only when the author asks. Never commit poems or corpus data (they are
  DVC-tracked only) and never bake them into Docker images.
- Original creative content in `seeds/angel_fragments/` and `seeds/library/` is
  NOT under the MIT license — see `NOTICE`. Do not copy or redistribute it.

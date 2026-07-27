# AGENTS.md — PoesIA

> Guidelines, Guardrails, and Operational Standards for AI Coding Assistants working on **PoesIA**.

---

## 1. Project Identity & Scope

* **PoesIA**: A personal hybrid poetry-writing engine combining deterministic phonology/prosody validation with LLM semantic generation, extended into sound analysis (`eufonia`), illustration (`galeria`), collection library (`memoria`), and music score/recitation (`armonia`).
* **Repo State**: Personal local-only repository. **Never configure or push to a remote (GitHub/GitLab) unless explicitly instructed by the user.**

### Active RAG/LLM Development Authority

Before changing `memoria/`, embedding-backed evaluation, retrieval-informed generation,
hosted LLM integration, or their CLI paths, read
`docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md` completely. It owns the current sequencing,
honest capability boundary, acceptance criteria, and definition of done for this work.
Do not mark a RAG/LLM phase complete from file presence or aggregate test count alone.

---

## 2. Commit Preparation & Git Standards

Before making any git commit, adhere to the following workflow:

1. **Test Verification**: Always run `pytest` from the repository root. Never commit broken code or failing tests.
2. **Logical Blocks**: Make commits in small, single-purpose logical blocks. Do not combine unrelated refactors, docs, and features into a single commit.
3. **Conventional Commits**: Format all commit messages using Conventional Commits:
   * `feat(<scope>): description` (e.g. `feat(generation): implement HostedLLMClient for Gemini and OpenAI APIs`)
   * `fix(<scope>): description`
   * `docs(<scope>): description`
   * `test(<scope>): description`
   * `refactor(<scope>): description`
4. **Clean Working Tree**: Ensure no temporary test artifacts or scratch files are left untracked.

---

## 3. Architecture & Seam Discipline

* **Layering Rules**:
  * `phonology/`: Pure, deterministic language prosody validators. No LLM or network calls allowed.
  * `evaluation/`: Scoring functions (metre, rhyme, theme, novelty). Pure functions or self-contained metrics models.
  * `generation/`: LLM orchestration and candidate repair loops (`ConstrainedLoop`).
  * Feature sub-modules (`eufonia`, `galeria`, `memoria`, `armonia`): Rely on abstract `Protocol` backends (`LLMClient`, `ImageBackend`, `ScoreBackend`) to keep vendor SDKs decoupled.
* **Lazy Imports**: Heavy ML/audio/image libraries (`sentence-transformers`, `pillow`, `music21`, `weasyprint`) must be lazy-imported behind try-except blocks with actionable `RuntimeError` messages instructing the user on `pip install -e ".[extra]"`.

---

## 4. Session Start & Handoff Protocol

### Session Start
1. Check `memory-bank/activeContext.md` and `memory-bank/tasks.md` to establish current state and active focus.
2. For RAG/LLM work, read `docs/RAG_LLM_ENGINEERING_HARDENING_PLAN.md`.
3. Run `pytest` to confirm working tree status.

### Session End / Task Completion
1. Update `memory-bank/activeContext.md` under **What We Just Did** and **Current Focus**.
2. Update `memory-bank/tasks.md` (move completed items to `DONE`, update `IN PROGRESS` or `BACKLOG`).
3. Ensure git working tree is clean or committed in logical blocks.

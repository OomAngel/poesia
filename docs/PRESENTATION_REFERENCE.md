# PoesIA Presentation Reference

> The repo-presentation standard distilled from the PoesIA repository (2026-08-04).
> Use it to review, diagnose, and level up any personal repo. **Enrichable** — see
> [§7 Enrichment protocol](#7-enrichment-protocol); keep the PoesIA exemplars fresh
> as the repo evolves.

---

## 0. Purpose & how to use this reference

This document formalises the presentation principles behind
[`OomAngel/poesia`](https://github.com/OomAngel/poesia) — the README structure,
the GitHub metadata, and the honesty rules — into a reusable, scoring, extendable
standard for the other repositories.

Three ways to use it:

1. **Review an existing repo** — score it with the [rubric (§4)](#4-scoring-rubric);
   the first full audit of the other 9 repos is in
   [`REPO_README_AUDIT.md`](REPO_README_AUDIT.md).
2. **Write a new README** — start from the [template (§6)](#6-template-starter-readme)
   and the recommended [anatomy (§3)](#3-readme-anatomy-recommended-order).
3. **Enrich the standard itself** — add principles, counter-examples, or new
   exemplars following the [protocol (§7)](#7-enrichment-protocol).

**Scope & non-goals.** This is about *presentation* (README + GitHub surface), not
engineering quality. It deliberately does **not** push every repo toward
public-facing polish: private/evidence/IP repos have their own correct posture
([P15](#p15-privateevidence-posture)). The standard is a spectrum, not a mandate.

---

## 1. The principles (P1–P15)

Four tiers. Tier A makes the first impression; Tier B proves the thing exists and
works; Tier C makes the reader trust the structure; Tier D earns trust about
governance. Each principle lists its **PoesIA exemplar** (a real snippet), the
**check** (rules that can be scored), and **anti-patterns**.

### Tier A — First impressions

#### P1 · Identity & hook
**What.** A name, a domain word, and a one-to-two-line hook that makes a
first-time reader smile or immediately understand the point of view.

**PoesIA exemplar:**
```markdown
# PoesIA

> *poesía* — Spanish for "poetry" — already contains **IA** (*Inteligencia Artificial*).
> Nothing invented; just noticed.
```

**Check.** (a) `# Title` matches the repo name (or the title explains the repo
name if they differ). (b) ≤2 lines after the title give a hook (etymology, pun,
domain insight). (c) The hook is *true* and cheap — nothing invented.

**Anti-patterns.** Title ≠ repo name with no explanation; generic "My project";
a paragraph-long tagline; a hook that needs domain lore the reader can't have.

#### P2 · Elevator pitch
**What.** One paragraph answering *what it is, for whom, and the core mechanism*.

**PoesIA exemplar:**
```markdown
A **hybrid poetry-writing engine**: deterministic phonology and prosody validation
anchored to LLM semantic generation — extended into sound analysis, illustration,
a personal library, and music.
```

**Check.** (a) One paragraph, ≤3 sentences. (b) Names the mechanism, not just the
domain. (c) States who it is for if that is non-obvious.

**Anti-patterns.** Vague adjectives ("powerful", "easy", "modern"); feature list
instead of a mechanism; "an AI tool for X" with no differentiation.

#### P3 · Thesis with evidence
**What.** The core claim stated crisply, backed by numbers — and the numbers kept
honest and reproducible.

**PoesIA exemplar:**
```markdown
Pure LLM generation produces formally valid poetry less than ~4% of the time.
Wrapping the same generation in deterministic phonological verification raises
validity to ~73%. The exact numbers differ per language; the architectural lesson
does not: **never trust an LLM to count syllables**.
```

**Check.** (a) At least one quantitative claim if the project has any measurable
behaviour. (b) Numbers are reproducible or linked to where they were measured.
(c) Caveats ("exact numbers differ per language") travel with the claim.

**Anti-patterns.** All-caps "×10 faster" with no baseline; stale counts that drift
from CI; percentages with no methodology.

#### P4 · Badge stack
**What.** A small, consistent row of `shields.io` badges at the top that encode
status, version/language, license, and feature facts — each anchoring to a
section.

**PoesIA exemplar:**
```markdown
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-478%20passing-brightgreen)](#development)
[![Status](https://img.shields.io/badge/status-active-brightgreen)](#status)
[![LLM backends](https://img.shields.io/badge/LLM%20backends-8%2B-blueviolet)](#core-generation)
[![Image backends](https://img.shields.io/badge/image%20backends-6-orange)](#galeria--illustration)
[![Languages](https://img.shields.io/badge/languages-es%20%7C%20en%20%7C%20nl-green)](#language-support)
[![Retrieval](https://img.shields.io/badge/retrieval-Graph%20RAG-purple)](#memoria)
[![MLOps](https://img.shields.io/badge/MLOps-MLflow-important)](#tooling)
```

**Check.** (a) Same provider (`shields.io`) and same `label-value-color` grammar
throughout. (b) Semantic colour: green = passing/active; blue = stable facts;
orange/violet/purple = feature facets. (c) Every badge links somewhere useful
(section anchor, LICENSE, docs). (d) **Test counts match CI exactly.** (e) ≤10
badges — beyond that, read like noise.


### Tier B — Proof of life

#### P5 · Showcase-first
**What.** Immediately after the pitch, show **real output** of the thing (an image,
a terminal transcript) plus the exact command that produced it — not a mock-up.

**PoesIA exemplar.** The very first section after the pitch is
`## Showcase — GalerIA in action`, with two real generated auca sheets (embedded
PNGs), each preceded by the exact command:

```bash
poesia galeria illustrate seeds/library/20260731_030227_142539_el_peso_del_saber__ingenuidad.md \
  --backend procedural --output docs/examples/auca_el_peso_del_saber.png
```

followed by honest context: *"Four stanzas, four panels, no network, no key."*

**Check.** (a) At least one real artifact visible without scrolling too far
(best: a `<p align="center">` image, 500–600 px wide). (b) The exact reproduction
command is one copy-paste away. (c) A caption says what the artifact is and what
trade-off it demonstrates.

**Anti-patterns.** Mocked/placeholder screenshots; images without captions;
"coming soon" showcases; artifacts that can't be regenerated by the shown command.

#### P6 · Feature map
**What.** Features grouped into a small number of memorable, named units, with a
table mapping **surface → name → role**. Named units turn a flat feature list into
a mental model.

**PoesIA exemplar:**
```markdown
| Command | Word | Role |
|---|---|---|
| `poesia write` · `poesia scan` | *poesía* — poetry | Core generation + validation loop |
| `poesia eufonia analyze` | *eufonía* — euphony | **Sound**: rhyme, assonance, consonance |
| `poesia galeria illustrate` | *galería* — gallery | **Illustration**: auca-style image sheets |
| `poesia memoria` | *memoria* — memory | **Collections**: library, semantic retrieval, Graph RAG |
| `poesia armonia` | *armonía* — harmony | **Music**: prosody → rhythm, score, sung/recited output |
```

**Check.** (a) Every major capability appears in exactly one named unit. (b) The
mapping table is the first thing under the Features heading. (c) Names are real
words with meaning, not initials-only.

**Anti-patterns.** A 30-bullet flat list with no grouping; invented names that
don't appear in the CLI; a feature mentioned in the README but not discoverable.

#### P7 · Honest capability boundaries
**What.** Explicitly separate the deterministic/reproducible core from the
AI/external surface, and state what is reproducible vs novel-per-request. Honesty
here is a *feature* of the presentation, not a weakness.

**PoesIA exemplar.** A dedicated subsection *"Phonology — the deterministic
spine"* states *"Lazy, pluggable backends — no network, no LLM, pure algorithms"*;
and the Cloudflare path is flagged *"output is novel per request — the served
SDXL ignores the seed; use `procedural` when bit-for-bit reproducibility
matters."* (and *"live-verified"*).

**Check.** (a) The README says which parts are deterministic and which are not.
(b) Non-deterministic/AI paths carry a one-line caveat at the point of use.
(c) Claims of reproducibility are true and tested.

**Anti-patterns.** "Fully reproducible" when a backend ignores seeds; AI
capabilities described as if deterministic; caveats buried in docs only.

#### P8 · Installation & extras
**What.** One canonical install command, plus a table of optional extras and
exactly what each enables.

**PoesIA exemplar:**
```markdown
git clone <repo-url> poesia && cd poesia
pip install -e ".[dev]"

| Extra | What it enables |
|---|---|
| `.[spanish]` | Spanish phonology (`silabeador`, `fonemas`) |
| `.[english]` | English phonology (`pronouncing`, CMUdict, `prosodic`) |
| `.[nlp]` | Semantic scoring (sentence-transformers) + imagery extraction (spaCy) |
...
```

**Check.** (a) One canonical path with zero optional ceremony. (b) An extras table
with *effect*, not just package names. (c) Minimum supported version stated
("Requires Python 3.11+").

### Tier C — Structure & clarity

#### P9 · Quickstart with real output
**What.** Copy-paste commands that go from nothing to first result **fast**, each
followed by the actual output line the user can expect.

**PoesIA exemplar:**
```bash
poesia scan "En el umbral de la noche callada" --language es
poesia write --theme "lluvia sobre piedra" --form soneto --illustrate
# ✓ Illustrated sheet: galeria/lluvia_sobre_piedra_20260803_175942.png
```

**Check.** (a) First successful command is ≤3 steps from a fresh clone.
(b) Commands show their real output (a `# ✓` line, a file path). (c) The
no-API-key / free path is explicitly called out if one exists.

**Anti-patterns.** "See docs" instead of a command; commands that need an API key
with no fallback note; output lines that don't match the current version.

#### P10 · Deep-dive per feature
**What.** For each major feature: the parameters that matter, the trade-offs, the
`--dry-run`/`--help` exploration paths, and a link to the deeper doc.

**PoesIA exemplar.** The long *GalerIA — illustration* section covers the pipeline
diagram, every backend (procedural/pollinations/cloudflare/openai/replicate) with
per-provider caveats, `--dry-run` for iterating prompts, `--panel-mode`, style
anchoring, and links the provider ranking to
`docs/IMAGE_GENERATION_PROVIDERS.md`.

**Check.** (a) Every named unit from [P6](#p6-feature-map) has a section.
(b) Each section has at least one real command and one trade-off note. (c) A
"explore without spending" path (`--dry-run`, `--help`) is shown.

**Anti-patterns.** One-liner sections ("See code"); deep-dives that repeat the
quickstart; trade-offs stated as facts without nuance.

#### P11 · Architecture in one diagram + a discipline statement
**What.** A single ASCII diagram of the whole system plus a two-to-three-sentence
architectural contract (what stays pure, what talks to the world, and why).

**PoesIA exemplar:** the ASCII box diagram
(`poesia CLI → Generation Loop → phonology/evaluation + feature modules`) followed by:

> The discipline: `phonology/` and `evaluation/` are **pure and deterministic**.
> Feature modules (`galeria/`, `armonia/`, `memoria/`) talk to the outside world
> only through abstract `Protocol` backends — no vendor SDK leaks into core logic.

**Check.** (a) One diagram that fits on a phone screen without scrolling sideways.
(b) A 2–3 sentence discipline statement in plain words. (c) The diagram's module
names match the code layout.

**Anti-patterns.** Auto-generated 200-node graphs; diagrams whose labels don't
exist in the repo; no statement of what is *forbidden*.

#### P12 · Development & quality gates
**What.** The exact commands for tests/lint/type, and a statement that CI enforces
them. Test counts are stated here, and they must match CI.

**PoesIA exemplar:**
```bash
pip install -e ".[dev]"
pytest                       # 478 tests
ruff check src/ mlops/       # lint (CI-enforced)
ruff format --check src/ mlops/
mypy src/ --ignore-missing-imports
```
> 478 passing tests; ruff, mypy, bandit, safety enforced in CI

**Check.** (a) Commands are runnable in the documented env. (b) The stated test
count equals the CI badge on [P4](#p4-badge-stack). (c) CI status is either
shown or linked.

**Anti-patterns.** Test counts from three months ago; "pytest" without the env;
### Tier D — Trust & governance

#### P13 · Status (honest, dated)
**What.** A dated, honest status: what is complete, what is in progress, what
failed. Future readers (and future-you) read this first.

**PoesIA exemplar:**
> Core engine complete; Phases 0–5 + P0–P5 hardening done, **478 tests passing**
> (2026-08). Fine-tuning and DPO pipelines operational (MLflow-tracked); GalerIA
> wired end-to-end …

**Check.** (a) The status carries a date. (b) Completed and in-progress are
separate. (c) It is *honest* — early repos say "early" (`microscopy-instrument-workbench`
does this well).

**Anti-patterns.** "Production-ready v0.5.0" with no evidence; no date; status
contradicting the Development section.

#### P14 · License & sharing + GitHub metadata
**What.** License badge + `LICENSE`; creative-content carve-outs via `NOTICE`;
corpus/data provenance; `CONTRIBUTING`/`SECURITY`/`CHANGELOG` links; and the
GitHub surface itself (description, topics, homepage).

**PoesIA exemplar:**
> **Software** — MIT, see `LICENSE`. **Original creative content** (`seeds/…`) —
> © the author, **not** covered by the MIT license. See `NOTICE`. **Corpus texts**
> — public domain; provenance in `docs/CORPUS_SOURCES.md`.
> Contribution standards: `CONTRIBUTING.md` · Security: `SECURITY.md` · History: `CHANGELOG.md`

**GitHub metadata checklist (off-README).**
- **Description** — ≤120 chars, mechanism + domain (PoesIA: *"A personal hybrid
  poetry-writing engine: deterministic phonology/prosody validation anchored to LLM
  semantic generation, with illustration (GalerIA), collections (MemorIA) and music
  (ArmonIA). Spanish-first."*).
- **Topics** — 5–7 real topics (PoesIA: `ai-poetry, llm, nlp, phonology, poetry, rag, spanish`).
- **License** — set in GitHub settings so the sidebar shows it.
- **Homepage** — set only if there is a real one.
- **CI** — visible badge, green.

**Check.** (a) LICENSE + badge present and consistent. (b) Content not covered by
the license is explicitly carved out. (c) Description and topics set on GitHub.
(d) CONTRIBUTING/SECURITY/CHANGELOG exist or are at least linked.

**Anti-patterns.** "Apache-2.0" license file with an MIT badge; no description
field; zero topics; a CHANGELOG link that 404s.

#### P15 · Private/evidence posture
**What.** Not every repo is a presentation. Evidence, IP, and personal-archive
repos must say *their* truth: what they are, why they exist privately, and what
must never leave. This is a legitimate — and sometimes *the only* — correct
posture.

**PoesIA-adjacent exemplar (`luminose-ip-archive`):**
```markdown
**Personal archive. Never to be published, shared, or made portfolio material.**
...
- Never publish this repo or its contents.
- Never use any file here as portfolio/interview material.
```
And `cielch-color-research`: *"The committed image/result artifacts are private
context … not a grant to publish datasets, generated figures, or unpublished
conclusions."*

**Check.** (a) The first screen says what the repo is *for* (including "never
publish"). (b) The boundary between shareable tooling and private evidence is
explicit. (c) No showcase/badges are bolted onto an evidence repo to make it
"look public-ready".

---

## 3. README anatomy (recommended order)

For a shareable/public-facing repo, in order:

1. `# Title` + hook (P1)
2. Badge row (P4)
3. Elevator pitch (P2)
4. Thesis + evidence (P3)
5. **Showcase — real artifact + command** (P5)
6. Feature map (named units, table) (P6)
7. Feature sections, each with commands + trade-offs (P10); deterministic vs AI
   boundaries called out inline (P7)
8. Installation + extras table (P8)
9. Quickstart with real output (P9)
10. Architecture diagram + discipline statement (P11)
11. Language/platform support table (if relevant)
12. Development & quality gates (P12)
13. Status (dated, honest) (P13)
14. License & sharing + links (CONTRIBUTING/SECURITY/CHANGELOG) (P14)

For a **private/evidence repo**, the correct anatomy is much shorter: title +
pitch + purpose/policy (P15) + setup + a scope table. No showcase, no badges.

## 4. Scoring rubric

Each principle scores **0–4**:

| Score | Meaning |
|---|---|
| 0 | Absent |
| 1 | Mentioned but not actionable |
| 2 | Present, usable, minor gaps |
| 3 | Good — mostly follows the PoesIA exemplar |
| 4 | Exemplary — would serve as the exemplar itself |

- **Total:** P1–P14 = **56 pts**; P15 is scored separately as *purpose-fit* and
  does **not** lower the score of an evidence repo.
- **Bands (P1–P14):**
  - **48+** — share-ready; polish only.
  - **36–47** — strong; a focused pass closes the gaps.
  - **24–35** — functional but reads like tooling, not a project.
  - **<24** — minimal/private posture (fine for evidence repos).

Score honestly: if a claim is unverifiable, the score is capped at 1 (P3/P12).

## 5. Diagnosis workflow

To audit a repo against this reference:

1. Fetch the README (`gh api repos/<owner>/<repo>/readme -H 'Accept: application/vnd.github.raw'`)
   and metadata (`gh api repos/<owner>/<repo>` → description, topics, license).
2. Score each principle 0–4 against the **Check** bullets (not the PoesIA text).
3. Note strengths and the top 3–5 *highest-leverage* gaps (usually: description +
   topics, badge row, quickstart, honest status).
4. Respect [P15](#p15-privateevidence-posture): evidence/IP repos get a
   purpose-fit note instead of a public-polish push.
5. Record the dated audit (the first full one is in
   [`REPO_README_AUDIT.md`](REPO_README_AUDIT.md)).

## 6. Template (starter README)

```markdown
# <Name>

> <one-line hook: etymology / pun / domain insight, ≤2 lines>

[![<Fact 1>](https://img.shields.io/badge/<label>-<value>-<color>)](#<anchor>)
[![License](https://img.shields.io/badge/license-<SPDX>-<color>)](LICENSE)

<One-paragraph elevator pitch: what it is, for whom, the core mechanism.>

<Thesis with a number. *Caveat that travels with the claim.*>

## Showcase — <thing> in action

<img src="docs/examples/<artifact>.png" width="520" alt="...">
_<Caption: what it is + the trade-off it demonstrates>_

```bash
<exact reproduction command>
```

## <Feature family / map>

| Surface | Name | Role |
|---|---|---|
| ... | ... | ... |

## Features

### <Unit 1> — with one real command + one trade-off
### <Unit 2> — ...
_(deterministic/AI boundaries stated inline: "X is reproducible; Y is novel per request")_

## Installation

Requires **<Python/other version>**.

```bash
git clone <repo-url> <dir> && cd <dir>
pip install -e ".[dev]"
```

| Extra | What it enables |
|---|---|
| ... | ... |

## Quickstart

```bash
<command>          # → real output line
```

## Architecture

```
<one ASCII diagram>
```
<2–3 sentence discipline statement>

## Development

```bash
pytest      # N tests (matches CI)
ruff check .
mypy .
```
> N passing tests; <tools> enforced in CI

## Status

<Dated, honest: complete / in progress / known gaps>

## License & sharing

<SPDX> — see `LICENSE`. <Carve-outs via NOTICE.> Provenance in `docs/`.
Contribution: `CONTRIBUTING.md` · Security: `SECURITY.md` · History: `CHANGELOG.md`
```

## 7. Enrichment protocol

This document is meant to grow. Rules for extending it:

- **New principles** get the next number (P16+), a tier assignment, a **real**
  PoesIA (or other repo) exemplar snippet, checkable rules, and anti-patterns.
- **Editing existing principles**: keep the *Check* bullets objective and
  scorable; update exemplars only when the source repo actually changed.
- **Counter-examples are welcome**: add them to the Anti-patterns of the
  relevant principle (cite the repo name).
- Every change appends a row to the changelog below.
- If a principle stops being followed by PoesIA itself, fix PoesIA first or
  demote the principle — the exemplar must stay honest.

## 8. Reference changelog

| Date | Change |
|---|---|
| 2026-08-04 | Initial standard: P1–P15 in four tiers; rubric; template; enrichment protocol. |





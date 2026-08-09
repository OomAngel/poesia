# Repo README Audit — 2026-08-04

> Diagnosis of the **9 other `OomAngel` repos** against the
> [PoesIA Presentation Reference](PRESENTATION_REFERENCE.md) (P1–P15 rubric).
> All repos are currently **private**. Scores reflect *potential presentation
> quality*, not a mandate — evidence/IP repos are scored separately for
> purpose-fit ([P15](PRESENTATION_REFERENCE.md#p15-privateevidence-posture)).

**Method:** README fetched via `gh api …/readme` (raw), metadata via
`gh api …` (description / topics / license). Scored 0–4 per principle against
the reference's *Check* bullets. Total = P1–P14 (**/56**).

---

## Score table

| Repo | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 | P12 | P13 | P14 | **/56** | % | P15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| orchard_twins | 3 | 4 | 4 | 3 | 1 | 3 | 2 | 2 | 3 | 3 | 2 | 4 | 3 | 3 | **40** | 71% | – |
| hiops | 2 | 3 | 1 | 0 | 0 | 3 | 3 | 3 | 2 | 2 | 2 | 3 | 0 | 2 | **26** | 46% | 3 |
| pcb-tools | 2 | 3 | 0 | 0 | 0 | 3 | 3 | 3 | 2 | 1 | 2 | 2 | 0 | 2 | **23** | 41% | 3 |
| research-tools | 2 | 3 | 0 | 0 | 0 | 3 | 3 | 3 | 3 | 1 | 2 | 2 | 0 | 1 | **23** | 41% | 3 |
| microscopy-instrument-workbench | 2 | 3 | 0 | 0 | 0 | 3 | 4 | 2 | 1 | 0 | 1 | 2 | 2 | 2 | **22** | 39% | 3 |
| cielch-color-research | 2 | 3 | 1 | 0 | 0 | 2 | 3 | 2 | 1 | 0 | 1 | 2 | 0 | 2 | **19** | 34% | 4 |
| optics-analysis | 2 | 3 | 0 | 0 | 0 | 2 | 3 | 2 | 1 | 0 | 1 | 2 | 0 | 2 | **18** | 32% | 3 |
| hidrive-image-index | 2 | 3 | 2 | 0 | 0 | 0 | 2 | 1 | 2 | 0 | 2 | 1 | 0 | 2 | **17** | 30% | 3 |
| luminose-ip-archive | 2 | 3 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | **10** | 18% | **4** |

**Notes.** `luminose-ip-archive` is an evidence/IP repo: its low P1–P14 score is
*correct* — [P15](PRESENTATION_REFERENCE.md#p15-privateevidence-posture)
purpose-fit is **4/4** and is what matters there. `P14` includes GitHub
metadata: **no repo has topics**; `orchard_twins` and `research-tools` have no
description. *(2026-08-04: the metadata pass fixed the latter two — see the
[Audit changelog](#audit-changelog). P14 scores above are the pre-pass baseline.)*

---

## Per-repo findings

### 1. orchard_twins — 40/56 (71%) — the share-ready candidate

**Strengths.** Best overall. Badges (CI, Python, CUDA, License), strong
elevator pitch, quantified claims (2.7M pts/s, 60 FPS on 10M+ points, 182
tests), full Quick Start, project-structure tree, usage examples, performance
benchmarks, contributing + license + acknowledgments. P12 is exemplary.

**Gaps.**
- **P5 (1/4)** — a GUI app with *no screenshots*; a viewer showcase with a real
  `.rxp`/parquet screenshot would be transformative.
- **P14 (3/4)** — **no GitHub description, no topics** (sidebar is blank).
- **P4 (3/4)** — badge style drifts (`blue.svg` vs `blue`, `green.svg`);
  normalize to the PoesIA grammar.
- **P7/P13 honesty** — "Architecture Quality 8.3/10 (Excellent)" self-score is
  unusual and not reproducible; replace with CI-verifiable numbers (coverage,
  test count). Status says "Production-Ready (v0.5.0)" without evidence.
- **P1 (3/4)** — title "Tree Digitalization" ≠ repo `orchard_twins`; add a
  one-line hook explaining the name.

**Top actions.** (1) Add 1–2 real viewer screenshots + reproduction command
(P5). (2) Set description + 5–7 topics on GitHub (P14). (3) Normalize badges.
(4) Swap the 8.3/10 self-score for measured facts (P3/P7/P13).

### 2. hiops (BOM Suite) — 26/56 (46%)

**Strengths.** Clear pitch + "hardware-intelligence" direction; excellent Main
Surfaces map; strong validation section (conda + pip + lockfile clarity);
secrets/do-not-commit policy; MIT license section.

**Gaps.** No badges, no status, no quickstart-with-output, and a **title
mismatch**: README says `# BOM Suite`, repo is `hiops` — say why in one line
(P1). No GitHub topics (P14).

**Top actions.** (1) Add the one-line hook + explain `hiops` vs "BOM Suite".
(2) Add a badge row (status/language/license/CI). (3) Add a dated Status
section (P13). (4) Add topics.

### 3. pcb-tools — 23/56 (41%)

**Strengths.** Precise pitch; layout table; honest fixture disclaimer; solid
setup (conda env, FreeRouting jar handling); guardrail tests.

**Gaps.** No badges, no status, no example output, no license section in the
README (Apache-2.0 file exists but isn't linked from a badge/section).

**Top actions.** (1) Add license badge + short Usage example (P8/P9). (2) Add
status (P13). (3) Add topics.

### 4. research-tools — 23/56 (41%)

**Strengths.** Honest posture ("not packaged as a public library"); Main
Surfaces table; daily commands; real Examples; secrets policy; audit-driven
completeness.

**Gaps.** **No GitHub description**, no topics, no badges, no status, no
license section.

**Top actions.** (1) Write the ≤120-char description + topics (P14). (2) Add
license badge + a dated Status line (P13). (3) Add one "first command from a
fresh clone" with output (P9).

### 5. microscopy-instrument-workbench — 22/56 (39%)

**Strengths.** Best honesty on display: "early general-purpose workbench" +
renaming plan (P13 = 2, rare); What Is Included / Not Included scope table
(P6 = 3); explicit private-artifacts policy (P7 = 4).

**Gaps.** No badges/showcase (correct — early), no example output; license
metadata is **`NOASSERTION`** on GitHub (P14) — should be resolved before
anything is shared.

### 6. cielch-color-research — 19/56 (34%)

**Strengths.** Clear evidence-boundary statement (P7 = 3, P15 = 4): *"not a
grant to publish datasets, generated figures, or unpublished conclusions"* —
exemplary private posture. Layout table + caution.

**Gaps.** Private evidence repo: showcase/badges are *not* the goal. The only
presentation asks that matter: **topics** and a license badge.

### 7. optics-analysis — 18/56 (32%)

Same profile as cielch. **Strengths.** Clear scope + boundary (P7 = 3),
layout table. **Gaps.** No badge/license section, no topics. It is a tooling
repo with shareable potential — a badge row + status would lift it more than
cielch.

### 8. hidrive-image-index — 17/56 (30%)

**Strengths.** Tiny and sharp: crisp pitch, real design notes with numbers
(98 MB vs 24 MB CSV, `EXPLAIN QUERY PLAN` evidence), one usage command.

**Gaps.** No badges, no license section, no status, no topics. As a
single-purpose tool, the PoesIA template fits in ~60 lines — highest
effort-to-value ratio for a full rewrite.

### 9. luminose-ip-archive — 10/56 (18%) — purpose-fit 4/4

**Do not change the presentation.** The README is *correct* for its job:
first line says "Never to be published, shared, or made portfolio material",
explains why it exists, and states the policy. P15 = 4. The only suggestion:
make sure **no other repo links to it** as a reference.

---

## Cross-repo quick wins (do these everywhere)

1. ✅ **Topics added to all 9 repos** (2026-08-04) — 5–6 each, domain-relevant
   (see [Audit changelog](#audit-changelog)).
2. ✅ **Descriptions set** on `orchard_twins` + `research-tools` (2026-08-04).
3. ⚠️ **License "fix" retracted.** `microscopy-instrument-workbench`'s
   `NOASSERTION` is **deliberate** — its `LICENSE` says "UNLICENSED — PRIVATE
   PERSONAL REPOSITORY · All rights reserved" and explicitly defers any
   open-source decision. Do **not** replace it; that would be a legal grant on a
   private workbench. `luminose-ip-archive` intentionally has none. Both are
   correct P15 posture.
4. ✅ **CI + license badges added** (2026-08-04, local commits) — cielch,
   hidrive, hiops, microscopy, optics, pcb-tools, research-tools; badge rows use
   the PoesIA grammar.
5. ✅ **Dated Status sections (P13) added** (2026-08-04) — hiops, pcb-tools,
   research-tools, cielch, optics, hidrive; orchard_twins status + self-score
   refreshed to measured facts. *(7/8 pushed; research-tools blocked by its own
   xenon gate — see [Audit changelog](#audit-changelog).)*

4. ✅ **CI badges added** (2026-08-04) — cielch, hidrive, hiops, microscopy,
   optics, pcb-tools, research-tools (quality/ci/tests workflow each, verified).
   Badge rows use the PoesIA grammar (license `-yellow`, `-blue` facts).
5. ✅ **Dated Status sections (P13) added** (2026-08-04) — hiops, pcb-tools,
   research-tools, cielch, optics, hidrive; orchard_twins' status refreshed to
   honest "Active (2026-08) · v0.5.0 · CUDA 12.9 rebuild" (was a stale 2025-01-20
   "Production-Ready") and its subjective "Architecture Quality 8.3/10" replaced
   with measured facts (182 tests · 47% coverage · CI 1m45s). All prepared as
   local commits; **pushes pending user confirmation** (4 repos carry unpushed
   local work: hiops +13, research-tools +6, cielch +4, optics +1).

## Audit changelog

| Date | Change |
|---|---|
| 2026-08-04 | **Metadata pass applied (Alternative A).** Descriptions set on `orchard_twins` + `research-tools`; 5–6 topics added to all 9 repos via `gh repo edit`. License step **dropped** after inspection: `microscopy`'s `NOASSERTION` is deliberate (UNLICENSED private-workbench text), not a defect. CI-badge and Status-section steps deferred. |
| 2026-08-04 | **README pass prepared (local commits).** CI + license badges (7 repos), dated Status sections (6 repos), orchard_twins badge/hook/honesty fixes. `luminose-ip-archive` untouched (P15 purpose-fit). |
| 2026-08-04 | **Pushed 7/8** (user-approved, as-is): cielch, hidrive, hiops, microscopy, optics, orchard_twins, pcb-tools. **`research-tools` NOT pushed** — its own pre-push quality gate (`xenon` complexity) fails on the user's WIP knowledge-graph code (6 functions in `kg_build.py`, `kg_enrich_all.py`, `reference_graph_enricher.py`, `graph_api/main.py`). The failed push's pre-commit run also reformatted 13 files and trapped the user's WIP in a stash patch; **WIP fully restored** (15 files, from `~/.cache/pre-commit/patch1785845800-534766`), hook formatting reverted. research-tools remains local: `main` ahead 7 (incl. my README commit `9f45e89`). |

## Priority matrix (impact × effort)

| Priority | Repo | Why |
|---|---|---|
| 1 | orchard_twins | Only repo near share-ready (71%); ~2 h closes the gaps |
| 2 | hidrive-image-index | Full PoesIA-template rewrite is ~60 lines; instant result |
| 3 | hiops | Biggest surface; badges + status + hook lift it a tier |
| 4 | research-tools · pcb-tools | Solid tooling; description + badges + status |
| 5 | optics · cielch · microscopy | Private/tooling; topics + license badge only |
| — | luminose-ip-archive | Leave as-is (purpose-fit perfect) |

*Re-run this audit after any pass; scores and dates belong in this file's
changelog when they change.*

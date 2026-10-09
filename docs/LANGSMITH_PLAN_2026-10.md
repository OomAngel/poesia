# LangSmith in PoesIA: plan (2026-10-09)

Angel, 2026-10-09: "focus on using LangSmith for my Nebius work and also for my poesia work. Plan
that now." The Nebius half is in career-assets
`docs/ww-transition/competitions/nebius-langsmith-plan-2026-10-09.md`. Status: **plan only**;
nothing is built yet.

## Where it fits (and what it must not replace)
- **MLflow stays the system of record** for training and evaluation runs, metrics and the model
  registry (`docs/INFRASTRUCTURE_DECISIONS.md` §7). LangSmith duplicates none of it.
- **LangSmith adds what MLflow doesn't do here:**
  1. per-call traces of the generation loop (draft → validators → repair);
  2. a queue where Angel rates poems by hand;
  3. metadata-only monitoring of the public calaveritas service.
- **Linking the two:** every traced run carries the MLflow `run_id` as metadata, and every MLflow
  run that traced calls records the LangSmith project as a tag.
- **It's an opt-in development tool, not product infrastructure** (INFRASTRUCTURE_DECISIONS §4.6
  and §5 are unaffected). When Angel says go, record that in INFRASTRUCTURE_DECISIONS as its own
  entry.

## Account
- Organization `01a11cec-…`, Workspace 1, free Developer plan (5,000 base traces a month).
- The desktop service key is in research-tools `secrets/langsmith.env.sops.yaml` (Workspace 1 only,
  expires about 7 Jan 2027).
- The Veriton gets **its own** key when P4 starts. Create it field by field as for the desktop key,
  and store it on the box, never a copy of the desktop key.
- Projects: `poesia-dev`, `poesia-eval`, `poesia-annotation`, `calaveritas-prod`.

## Design: a seam, off by default
- `poesia/observability.py` exposes a no-op `traceable` and a `wrap_llm_client` by default. They
  are lazy-imported from `langsmith` only when `LANGSMITH_TRACING=true` and the `.[tracing]` extra
  is installed. This follows AGENTS.md §3: vendor SDKs behind seams, lazy imports with an
  actionable `RuntimeError`.
- **Instrument:** the `ConstrainedLoop` attempts, each validator verdict (metre, rhyme, theme, the
  safety screen) and each repair.
- **Leave alone:** `phonology/` stays pure: no tracing imports, no network.
- **Masked by default.** `hide_inputs` / `hide_outputs` replace poem text and retrieved corpus
  passages with lengths and hashes. That follows "never commit poems or corpus data" in spirit:
  the corpus (LACIPI, LoC, Gutenberg) and Angel's poems don't go to a US service unless chosen.
  - **Angel's own drafts:** an explicit per-run opt-in.
  - **Corpus passages:** never sent.

## Uses, in order

| # | Use | Why | When |
|---|---|---|---|
| P1 | **Debug the generation loop** (`poesia-dev`) | See which validator rejects a draft and what the repair changed. Example: the English leakage in German and French proposals measured in `fa72194`. Today this means reading JSONL | After 16 Oct |
| P2 | **Benchmark samples** (`poesia-eval`) | Trace a sample of the HF Jobs / CSCS / Ollama benchmark calls to inspect failures. **Numbers stay in MLflow** | After 16 Oct |
| P3 | **Annotation queue** (`poesia-annotation`) | Angel rates poems: quality, and safety false alarms and misses. Two uses: DPO pairs for `scripts/train_poetry_dpo.py`, and tuning and test sets for the safety screen (its research says to split `risk_other` before more tuning). Export the ratings to DVC (poems are DVC, never git) | After 16 Oct |
| P4 | **Calaveritas monitoring** (`calaveritas-prod`), **metadata only** | The service runs unattended 17 Oct – 4 Nov. Watch latency, errors, model, validator pass/fail and safety flags, with `LANGSMITH_HIDE_INPUTS/OUTPUTS=true`. The service rule "log no names or poem text" (workspace-governance `machines/veriton/services/calaveritas/README.md`) holds: no user text leaves the Veriton | See decision 2 |

**Not in the Hack Apertus entry.** The entry (`~/dev/poesia-apertus`) is pinned and due 13 Oct.
A new dependency there buys nothing before the 16 Oct close.

## Open checks before building
- Do CSCS / Apertus terms allow sending model outputs (even metadata) to a third-party service?
  Read the CSCS terms; P4's metadata-only mode reduces but doesn't settle this.
- The calaveritas container has an egress restriction (the Veriton README: "egress unit"). P4
  needs `api.smith.langchain.com` added to that allowlist, and that is a Veriton change.
- Monitoring alerts: check whether LangSmith's alerting is on the free plan. If not, P4 stays a
  dashboard, and Healthchecks/Telegram remains the alert path.

## Recommendations needing Angel's yes
1. **Masked by default** (poem text and corpus passages hidden), with your own drafts traceable per
   run on request: **yes**.
2. **P4 before the trip:** only if it fits in about 2 hours on 15–16 Oct after the Hack Apertus
   submission; otherwise after 4 Nov. Healthchecks already covers "is it up". LangSmith would add
   "is it writing well", which can wait.
3. **Order after 16 Oct:** P1 → P3 → P2.

Sources (read 2026-10-09):
[mask inputs/outputs](https://docs.langchain.com/langsmith/mask-inputs-outputs),
[administration overview (retention: base 14 days, extended 180 days)](https://docs.langchain.com/langsmith/administration-overview),
[pricing](https://www.langchain.com/pricing).

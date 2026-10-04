# Lemonade integration — plan (not started)

Recorded 2026-09-28. Why: PoesIA is the fastest candidate for the **AMD Lemonade
Developer Challenge** (a Strix Halo laptop for open-source projects "built with
Lemonade"; rolling "until supplies are exhausted"). Challenge research, rules and links:
`~/dev/career-assets/docs/ww-transition/competitions/amd-lemonade-challenge.md`.
Nothing below is implemented; treat each item as a proposal to verify before building.

## Why PoesIA fits

- Already public on GitHub under MIT — the challenge requires an open-source licence.
  (Note: `AGENTS.md` still says "Personal local-only repository… never push to a remote",
  but `origin` is `github.com/OomAngel/poesia` and GitHub reports it PUBLIC. Decide which
  is true and update `AGENTS.md` before submitting.)
- Already routes generation across providers: `src/poesia/generation/router.py`
  (`groq` → `openai` → `ollama` → `stub`, overridable with `LLM_ROUTE`), with a local
  Ollama client in `src/poesia/generation/llm_client.py` (`OLLAMA_HOST`, default
  `http://localhost:11434`, `OLLAMA_MODEL`).
- GalerIA already has pluggable image backends (`src/poesia/galeria/backends.py`) and a
  provider evaluation (`docs/IMAGE_GENERATION_PROVIDERS.md`) whose §8 names local
  generation as "the long-term home for GalerIA".
- AMD's own examples of a winning entry include "Integrate Lemonade into an app/workflow
  and demo it", and the maintainers said they "would absolutely love to see what you can
  do with Lemonade Omni Models". Past winners were working tools people use.

## Additions

1. **Lemonade as an LLM provider.** Lemonade serves OpenAI-, Anthropic- and
   Ollama-compatible APIs (default port 13305). Two options:
   - point the existing `ollama` provider at Lemonade (`OLLAMA_HOST=http://<host>:13305…`)
     — verify the exact Ollama-compatible path before relying on it;
   - or add a `lemonade` route entry using the OpenAI-compatible client with
     `base_url=http://<host>:13305/v1` — cleaner, and it shows up in `LLM_ROUTE` as
     `lemonade:<model>`.
   Candidate models from Lemonade's registry: Qwen3.5-4B / Qwen3-8B / Gemma-4 (verify
   Spanish poetry quality against PoesIA's own adapters).
2. **Serve PoesIA's own fine-tuned adapter locally.** Serve the adapter from the 2026-10
   retrain (`docs/RETRAINING_PLAN_2026-10.md`). The July adapters (`poetry-lora-distilled`,
   `poetry-lora-qwen3b`) are within noise of each other (`docs/ANALOGIA_PLAN.md`) and sit
   only on the laptop's DVC remote. If Lemonade can load a user-supplied GGUF (merged
   LoRA), PoesIA's own model runs through Lemonade — the strongest "built with Lemonade"
   story. UNVERIFIED: Lemonade's support for custom GGUF checkpoints. A 9B adapter's GGUF
   size matters here (`RETRAINING_PLAN_2026-10.md` §6 step 7).
3. **GalerIA backend on Lemonade image generation** (SD-Turbo, SDXL, Flux-2-Klein,
   Z-Image via sd-cpp; `cuda`/`vulkan`/`cpu` backends) — a local, free, private option
   for `docs/IMAGE_GENERATION_PROVIDERS.md` §8.
4. **Voice: read the poem aloud** with Lemonade text-to-speech (kokoro; Spanish voice
   availability UNVERIFIED) and optional dictation with Whisper for "bring what you carry".
   Today's recitation backend in code is eSpeak NG (`EspeakRecitationBackend` in
   `src/poesia/armonia/backends.py`); the `recitation` extra (`piper-tts`) is verified for
   Spanish synthesis on Python 3.13 but not wired in yet.
5. **One-endpoint "Omni" mode** (e.g. LMX-Omni-5.5B-Lite = Qwen3.5-4B + SD-Turbo +
   Whisper-Tiny + kokoro) so the whole instrument runs from one local server.
6. **Short benchmark note**: poem quality and latency per backend (Lemonade `cuda` on the
   RTX 3070, `vulkan`, `cpu` on the 5900X) — AMD lists "Deepdive performance eval" as an
   example entry.

## Constraints to respect

- `docs/ROADMAP.md` non-goals: "No web frontend until concrete need emerges" and "No
  C++ code" — Lemonade runs as a separate server, so neither is needed. The demo can be
  the CLI plus a recorded video.
- WSL2: Lemonade has no documented WSL2 path; run it natively on Windows and call it from
  WSL (Lemonade issue #1770 shows 0.0.0.0-binding/networking problems).
- Keep the deterministic checks as the authority ("the model proposes only what code can
  then check") — Lemonade is another generator behind the same gate, not a new authority.

## Submission checklist (challenge)

- [ ] Resolve the `AGENTS.md` local-only vs public-repo contradiction
- [ ] Lemonade provider + tests (mock-based, like the Groq/Ollama tests)
- [ ] GalerIA Lemonade backend; TTS reading
- [ ] README section "Run PoesIA fully local with Lemonade"
- [ ] Demo video; post in the Lemonade Discord #AMDDevChallenge
- [ ] Submit via the AMD member form: https://account.amd.com/en/member/ai-dev-program/lemonade-challenge.html

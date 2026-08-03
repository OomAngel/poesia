# Free & Low-Cost Image-Generation APIs — Evaluation for GalerIA

> **Status**: research pass + live probes, 2026-08-03.
> **Purpose**: choose online backends for GalerIA (auca sheets: one image per
> stanza) without paying for image generation.
> **Method**: documented sources (vendor docs, fetched 2026-08-03) **and** live
> probes where the sandbox had network access. Scores are a **decision aid, not
> gospel** — free tiers change constantly, so every pick must be re-verified at
> adoption time.
> **Scope**: cloud/serverless image-gen APIs. Local self-hosted options
> (diffusers/ComfyUI) are documented as a baseline but excluded from the online
> ranking. Paid-only providers (OpenAI DALL·E, Replicate, Ideogram, Leonardo…)
> are mentioned only as the paid ceiling to compare against.

---

## TL;DR — ranked verdict (online, free)

| # | Provider | Weighted score | One-line why |
|---|----------|---------------|--------------|
| 1 | **Pollinations.ai** | 4.15 / 5 | Free, no key, GET endpoint, seed-deterministic — but community infra (low reliability), ~1 req/15s, and observed to route to a different model than requested |
| 2 | **Cloudflare Workers AI** | 3.60 | 10,000 neurons/day free (~tens to hundreds of images), SDXL/FLUX-class, real infra — needs a free Cloudflare account + API token |
| 3 | **Google Gemini free tier** | 3.60 | Best quality (Nano Banana / Imagen) — needs a Google account + key, limits are per-project and opaque |
| 4 | **AI Horde** | 3.60 | Truly free community grid (anonymous key `0000000000`) — slow queues, priority via kudos |
| 5 | **One-time-credit platforms** (fal, Together, DeepInfra, NVIDIA NIM…) | 3.25 | Real commercial infra + FLUX/SDXL, but ~$1 trials, not ongoing free |
| 6 | **Hugging Face Inference Providers** | 2.85 | $0.10/month credits ≈ **one image** — a token, not a pipeline |

Pollinations ranks first **because of the axes PoesIA cares about most right
now** (zero cost, zero friction, ergonomics, deterministic seeds), and it is
*simultaneously* the least reliable of the top four. That tension is the point
of this document — see [Scoring & ranking](#scoring--ranking) and
[What this means for GalerIA](#what-this-means-for-galeria).

Local `diffusers`/ComfyUI would score ~4.3 and beat every cloud option **if a
GPU is available**; for a shareable, key-less, reproducible demo the cloud picks
above are still the practical route.

---

## Ranking criteria ("the aspects")

The goal is not "which API makes the prettiest picture" but "which APIs can
GalerIA rely on for a free, reproducible, shareable auca pipeline today".

| # | Criterion | Weight | What we measure | Why it matters for PoesIA |
|---|-----------|--------|-----------------|---------------------------|
| 1 | **Cost / free generosity** | 20% | Ongoing free allowance (per-day/per-month images), not one-time trials | The repo's README example must be reproducible by anyone, forever, at $0 |
| 2 | **Signup friction** | 15% | No key / free key / free account / card required | A new user must be able to run `poesia galeria illustrate --backend X` within a minute |
| 3 | **API ergonomics** | 15% | Std-lib-compatible (urllib), simple request shape, byte passthrough | GalerIA's `ImageBackend` seam is stdlib `urllib`; SDKs would break the seam discipline |
| 4 | **Image quality** | 15% | Model class actually served (SD1.5 < SDXL < FLUX < Nano Banana/Imagen) | Auca panels are the product's face |
| 5 | **Determinism** | 10% | Seed parameter → same image for same prompt | Matches PoesIA's core thesis (reproducible craft); the README example is regenerated bit-for-bit |
| 6 | **Reliability / longevity** | 10% | Commercial SLA vs community grid vs free-tier queue; funding model | A backend that dies silently breaks the demo |
| 7 | **Rate limits / throughput** | 10% | Images per minute/day on the free tier | A 4-stanza soneto = 4 requests; a full library re-illustration = dozens |
| 8 | **Privacy** | 5% | Account-less, no data retention, prompt visibility | Poetry is personal; prompts should not be broadcast publicly |

Scores are 1–5. **Weights are opinions** — this repo prefers zero-friction,
zero-cost, reproducible illustration over one-time quality; adjust the weights
and re-rank if your priorities differ.

---

## Candidate inventory

### 1. Pollinations.ai

- **What**: open-source (MIT), community-supported gen-AI platform; image API
  is a Cloudflare Worker backed by various models.
- **Models**: docs default to `flux`; `turbo` and others via `model=`; **empirically
  the served model was `sana`** (EXIF) even when `model=flux` was requested.
- **Free tier**: fully free anonymously. **No API key, no signup.** Optional free
  registration (`auth.pollinations.ai`) raises limits and enables `nologo`.
- **API**: `GET https://image.pollinations.ai/prompt/{prompt}?width=&height=&model=&seed=&nologo=&enhance=&private=`
- **Output**: image bytes (observed **JPEG**, not PNG).
- **Determinism**: `seed` parameter (verified in docs; empirically one seed per
  prompt reproduced an identical 11 KB file byte-for-byte on repeat at 256px).
- **Rate limits**: anonymous ≈ **1 request / 15 s**; register for higher.
- **Reliability**: community-funded (Perplexity, AWS Activate, NVIDIA Inception
  sponsors); no SLA. Fine for demos, not for production SLAs.
- **Privacy**: images are public on feeds unless `private=true`; anonymous use
  carries no account link.
- **Evidence**: vendor APIDOCS.md + **live probes** (see empirical log).
- **Fit for GalerIA**: excellent on cost/friction/ergonomics/determinism;
  poor on reliability and rate limits.

### 2. Cloudflare Workers AI

- **What**: serverless inference on Cloudflare's edge network.
- **Models**: text-to-image incl. `@cf/stabilityai/stable-diffusion-xl-base-1.0`,
  `@cf/bytedance/stable-diffusion-xl-lightning`, FLUX variants
  (`@cf/black-forest-labs/flux-2-klein-4b`, …), Leonardo models.
- **Free tier**: **10,000 neurons/day** on the Free plan (resets 00:00 UTC).
  Image cost ≈ 26–37 neurons per 512×512 tile (flux-2-klein) → roughly
  **50–300 images/day** depending on model/size; SDXL-class costs more.
- **Auth**: free Cloudflare account + API token; REST API or Workers binding
  (also an OpenAI-compatible endpoint).
- **API**: `POST https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/{model}`,
  JSON `{prompt, num_steps, guidance, width, height}`.
- **Determinism**: no user-visible `seed` control for most models (best-effort).
- **Rate limits**: bounded by the daily neuron quota; queued GPU on free tier
  during demand spikes.
- **Reliability**: commercial infrastructure, SLAs at paid tiers.
- **Privacy**: Cloudflare account; prompts processed by Cloudflare/partner hosts.
- **Evidence**: official pricing + models pages (fetched 2026-08-03).
- **Fit**: strong #2 — the best "real infrastructure, genuinely free" option;
  loses to Pollinations on friction and determinism.

### 3. Google Gemini API — free tier (AI Studio)

- **What**: Google's API with native image generation.
- **Models**: Nano Banana family (`gemini-2.0-flash-preview-image-generation`,
  current `gemini-3.x-flash-image`), Nano Banana 2/Pro, Imagen 3/4. **Best
  quality of any free option** (strong text rendering, editing, consistency).
- **Free tier**: free API key from AI Studio; per-project rate limits
  (RPM/RPD, images-per-minute), reset daily at midnight Pacific. Exact numbers
  are shown per model in AI Studio and were **not fully retrievable from the
  docs pages fetched** (tables truncated) — treat as "generous for personal
  use, verify in your AI Studio project".
- **Auth**: free Google account + API key.
- **API**: `POST https://generativelanguage.googleapis.com/v1beta/...`
  (JSON, `generateContent` or newer Interactions API); returns base64 PNG.
- **Determinism**: no user-controlled seed for image models — output varies run
  to run (breaks bit-for-bit reproducibility).
- **Reliability**: Google infrastructure; free tier may see rate-limiting.
- **Privacy**: Google account; prompts stored/used per Google's AI policy.
- **Evidence**: official models + rate-limits pages (2026-08-03).
- **Fit**: quality king; the natural "photoreal upgrade" path once a key exists.
  Not the reproducible default.

### 4. AI Horde (Stable Horde)

- **What**: free, community-powered distributed grid; volunteers run workers.
- **Models**: SD1.5, SDXL, FLUX-class and many community checkpoints; model
  availability depends on what workers are running.
- **Free tier**: fully free. **Anonymous API key `0000000000` (10 zeros) works
  with no registration**; registering (OAuth2/pseudonymous) improves queue
  priority via the kudos system. Anonymous is lowest priority and may be
  restricted during high load.
- **API**: `POST https://aihorde.net/api/v2/generate/async` (prompt + params
  incl. width/height/seed/cfg/steps/sampler) → poll `GET /api/v2/generate/status/{id}`.
  Async + polling (not a single GET).
- **Determinism**: seed supported.
- **Rate limits**: queue-based; anonymous requests can take minutes.
- **Reliability**: donation-funded, volunteer workers — queue times and model
  availability vary wildly.
- **Privacy**: anonymous; no account unless registered.
- **Evidence**: official site + GitHub README (2026-08-03).
- **Fit**: genuinely free and key-less like Pollinations, but slower, less
  predictable, and the async API is heavier to wire.



### 5. Hugging Face Inference Providers

- **What**: centralized access to partner inference providers (DeepInfra, Fal,
  Novita, Together, …) via one HF token + router.
- **Free tier**: **$0.10/month credits** for free users ($2 for PRO). A single
  FLUX/SDXL image costs ~$0.001–0.01 → **~1–10 images per month**. Not a
  pipeline; a taste.
- **Auth**: free HF account + user access token.
- **API**: HF `InferenceClient`/`huggingface_hub` or direct HTTP; partner providers
  also available directly.
- **Determinism**: model-dependent; SDXL/FLUX support seeds.
- **Reliability**: commercial providers behind it, but routed/credit model adds
  a layer; `hf-inference` itself is now mostly CPU-only for embeddings/LLMs.
- **Privacy**: HF account; prompts routed through HF then providers.
- **Evidence**: official pricing page (2026-08-03).
- **Fit**: useful as a *discovery layer*; too thin a free tier to power the demo.

### 6. One-time-credit GPU platforms

Commercial, pay-as-you-go inference with a small onboarding credit. Not ongoing
free; included for completeness and as the "first $0 upgrade" ladder.

| Platform | Free on signup | Models | Notes |
|---|---|---|---|
| **fal.ai** | ~$1 (verify — page rate-limited in this pass) | FLUX, SDXL | Clean API, fast |
| **Together AI** | free credits (amount unverified this pass) | FLUX.1, SDXL | Also fine-tuning |
| **DeepInfra** | none now (card/prepay required) | FLUX-1-schnell ≈ **$0.0005/img** | Cheapest per-image |
| **NVIDIA NIM** (build.nvidia.com) | free developer API credits | SDXL, FLUX | |
| **Prodia / Segmind / Novita** | small trial credits | SDXL, SD1.5 | Long tail |
| **Civitai** | credit-based | community models | Buzz economy |
| **SiliconFlow** | trial credits | FLUX, Qwen-Image | CN origin |

- **Ergonomics**: standard REST, OpenAI-style in several cases.
- **Determinism**: seeds supported.
- **Reliability**: commercial (best of the list).
- **Evidence**: mixed; several pages were JS-rendered or rate-limited during this
  pass — verify before relying.

### 7. Regional / other

- **Zhipu CogView-3/4** (CN): free credits for Chinese phone/account; quality
  competitive; auth and ToS are CN-centric.
- **Alibaba Tongyi Wanxiang**: free trial credits; CN account ecosystem.
- **OpenRouter image variants**: OpenRouter now lists image models; free
  `:free` variants exist for some — verification page 404'd this pass.
- These are noted for completeness, not ranked (friction/regionality).

### 8. Local / self-hosted (baseline, not ranked online)

- **diffusers** (repo `illustration-local` extra), **ComfyUI**, **A1111** —
  fully free, unlimited, private, deterministic (seed), highest quality ceiling
  with FLUX/SDXL checkpoints. Requires a GPU (or patience on CPU).
- Scores ~4.3 if ranked with a GPU; **the long-term home for GalerIA** — the
  cloud options above are the zero-hardware, zero-cost path in the meantime.

---

## Scoring & ranking

Scores 1–5 per criterion × weight (see [criteria](#ranking-criteria-the-aspects)):

| Provider | Cost 20% | Friction 15% | Ergonomics 15% | Quality 15% | Determinism 10% | Reliability 10% | Rate 10% | Privacy 5% | **Total** |
|---|---|---|---|---|---|---|---|---|---|
| **Pollinations** | 5 | 5 | 5 | 4 | 5 | 2 | 2 | 3 | **4.15** |
| **Cloudflare Workers AI** | 4 | 3 | 3 | 4 | 3 | 4 | 4 | 4 | **3.60** |
| **Gemini free tier** | 4 | 3 | 3 | 5 | 2 | 4 | 4 | 3 | **3.60** |
| **AI Horde** | 5 | 4 | 3 | 3 | 4 | 2 | 3 | 4 | **3.60** |
| **Credit platforms** (fal/Together/NIM…) | 2 | 3 | 3 | 4 | 4 | 4 | 4 | 3 | **3.25** |
| **HF Inference Providers** | 2 | 3 | 3 | 4 | 3 | 3 | 2 | 3 | **2.85** |

**Tie-breaks in the 3.60 group** (all three are legitimate second picks,
depending on the axis you care about):
- **Cloudflare** beats the others on *reliability + real free throughput*, is
  second only to Pollinations on free volume.
- **Gemini** beats everyone on *quality*; loses on determinism (no seed).
- **AI Horde** beats both on *friction + privacy*; loses badly on reliability.

**Why Pollinations is #1 despite scoring 2/5 on reliability**: it wins the four
axes PoesIA currently needs most — cost, friction, ergonomics, determinism —
which together carry 60% of the weight, and it is the *only* candidate that is
simultaneously key-less, seed-deterministic, and single-GET. Its 2/5
reliability is a warning, not a disqualifier: the implementation must degrade
gracefully (clear error → "use `--backend procedural`") and the README example
must not depend on it.

---

## Empirical test log (live, 2026-08-03, from the dev sandbox)

| Probe | Command / URL | Result | Interpretation |
|---|---|---|---|
| Pollinations 256×256 | `GET image.pollinations.ai/prompt/una luna sobre el mar?width=256&height=256&nologo=true&seed=42` | **HTTP 200**, 11,094 B, **0.89 s**, **JPEG** 256×256, EXIF `manufacturer=sana` | Key-less GET works from a plain sandbox; output is JPEG; small sizes route to `sana` |
| Pollinations 1024×1024, `model=flux`, style tag | `…?width=1024&height=1024&model=flux&seed=42&nologo=true` | **HTTP 200**, 127,434 B, **2.26 s**, **JPEG 768×768**, EXIF `manufacturer=sana` | **Docs ≠ reality**: model param ignored/aliased (sana served), size rounded to 768, output JPEG. PIL opens it fine (RGB). |
| Determinism probe | repeat 256px with same seed | identical 11,094 B file | `seed` works (at least for cached results) |
| **Bug found by live test** | full CLI `--backend pollinations` | **HTTP 500**: `seed Too big: expected number to be <=2147483647` | Prompt-derived seed used the full 32-bit *unsigned* range; Sana requires signed 32-bit. **A mocked unit test would never have caught this.** Fixed by masking `& 0x7FFFFFFF`. |
| **Fixed, full CLI auca sheet** | `poesia galeria illustrate poema.txt --backend pollinations` | **2 panels generated → 1,327,927 B PNG sheet (1706×1046)**, 1636 distinct colours | End-to-end works: poem → stanza split → imagery extraction → live sana images → composed sheet |
| **Service-level determinism** | same prompt+style twice (`seed` clamped) | both responses **68,893 B, byte-identical** | Same seed ⇒ same image from the live service — reproducibility holds online too |
| Response internals | `requestParameters` echoed in error payload | `model:"sana"`, `width:768, height:768`, `nologo:true` | Confirms default model + native 768×768; `nologo` accepted anonymously (docs say it needs an account — it did not, at time of writing) |
| Latency | timing on live calls | ≈ **10–11 s per image** (sana 768) | Plus ~15 s rate-limit gap between anonymous requests → a 4-stanza soneto ≈ 60–75 s |

**What this tells us**: (1) Pollinations is genuinely key-less and fast; (2) we
must treat its response as "image bytes" (JPEG/PNG), never assert a format or
size — GalerIA's `AucaComposer` already opens via PIL so this is fine; (3) model
control is **not** what the docs claim — do not advertise "flux"; (4) the
service is a moving target — pin nothing, degrade gracefully.

---

## What this means for GalerIA

1. **`pollinations` backend — implemented and live-tested 2026-08-03**
   (`src/poesia/galeria/pollinations.py`, `--backend pollinations`):
   - `ImageBackend` Protocol compliance (stdlib `urllib`, byte passthrough)
   - deterministic seed derived from the prompt, **masked to signed 32-bit**
     (`& 0x7FFFFFFF`) — the live 500 caught exactly this: Sana rejects
     seeds > 2^31-1; a mocked test could not
   - graceful `RuntimeError` → CLI catches it and suggests `--backend procedural`
   - `--backend auto` stays **offline-first** (`procedural`): `auto` must never
     make an unsolicited network call; `pollinations` is an explicit choice
   - **verified**: 2-stanza auca sheet composed live (1.3 MB PNG); same
     prompt+seed ⇒ byte-identical images (service-level determinism)
2. **Re-verify at adoption** (free tiers move): Cloudflare daily quota + exact
   neuron cost of the chosen model; Gemini's per-project image limits; the
   credit amounts on fal/Together before recommending them.
3. **Follow-ups ranked by ROI**: Cloudflare (reliability) → Gemini (quality,
   needs a key) → AI Horde (async polling) → local diffusers (long-term).
4. **Keep the README example on `procedural`** (offline, bit-for-bit stable);
   `pollinations` is documented as the free online option in the README's
   GalerIA section.

---

## Honest gaps / open questions

- **Gemini free-tier image rate limits**: docs page tables truncated in fetch;
  numbers per model are visible in AI Studio. Verify before relying on volume.
- **Stability AI platform**: JS-only page; historical free-credit program status
  unverified (platform has moved subscription-heavy). Treated as "paid, verify".
- **fal.ai**: pricing page rate-limited (HTTP 429) this pass; credit amount
  unverified.
- **AI Horde anonymous specifics**: exact anonymous kudos/parallel-job caps not
  verified against swagger this pass; see `https://aihorde.net/api/v2/swagger`.
- **Pollinations model routing**: observed `sana` despite `model=flux`;
  contradicts vendor docs — re-check at adoption, keep the backend model-agnostic.
- **OpenRouter image models**: docs URL 404'd; treated as "emerging, unverified".

*Sources fetched 2026-08-03: pollinations APIDOCS.md (GitHub), developers.cloudflare.com
(pricing, models), ai.google.dev (models, rate-limits), aihorde.net + Haidra-Org/AI-Horde
(GitHub), huggingface.co inference-providers pricing. All free-tier specifics are
subject to change; re-fetch before relying.*


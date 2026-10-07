# GalerIA character comic: handoff (2026-10-07)

**Goal.** Make new pictures of Angel's girlfriend and their dog in new situations, like a
comic, in the exact style of the one drawing he likes: thick black ink on pure white,
chibi proportions, tapered strokes, elegant curves, no grey.

**Status.** Paused, waiting on API keys. Everything needed to continue is in git: this
doc, the research, the reference drawing and every attempt. A fresh clone on any PC is
enough. No image model has been tried yet; every image made so far was hand-built SVG,
and that route is a dead end for drawing (§3). Next step: §5, either the free manual test
(Path A) or the keyed test (Path B).

**This is the single entry point.** The evidence behind every recommendation (sources
dated 2026-10-07) is in
[CHARACTER_CONSISTENT_ILLUSTRATION_RESEARCH.md](CHARACTER_CONSISTENT_ILLUSTRATION_RESEARCH.md),
and the raw notes of its four research tracks are in
[research/research_notes/](research/research_notes/Character%20consistent%20ink%20illustration%20tools/).

---

## 1. Assets and where they live

Everything is in git under
[`seeds/characters/couple-ink/`](../seeds/characters/couple-ink/), next to the other input
material in `seeds/`. Angel decided on 2026-10-07 to commit the drawing (the repo is public).
Generated output still goes to the gitignored `galeria/`.

| Path | What | SHA-256 (first 12) |
|---|---|---|
| `reference/original.jpg` | **The one reference.** 943×691, her seated cross-legged with hands in lap, dog seated to the right, flowers and a sprig as filler | `b8ebe02deb5f` |
| `reference/her_only.png` | Crop of her alone (385×680, plant fragments painted out) | `3e3231e9b4f5` |
| `reference/dog_only.png` | Crop of the dog alone (340×340, sprig painted out) | `7e084be269f7` |
| `attempts/` | Every SVG attempt, render, overlay and side-by-side from this session (§3) | — |
| `tools/render.py` | SVG → PNG via headless Chromium | — |
| `tools/score.py` | Ink IoU and 3 px-tolerant F1 vs the original in a box, plus a red/blue overlay | — |
| `tools/score_parts.py` | Same IoU per facial feature box (bun, dome, fringe, brows, eyes, nose+mouth, ears, jaw, locks) | — |

Check the reference arrived intact: `sha256sum seeds/characters/couple-ink/reference/*`.

**Running the tools on another PC.** The scorers need numpy, Pillow and scipy, which the
`poesia` conda env already has:
`python tools/score_parts.py reference/original.jpg attempts/head_v5.png`. The renderer
needs Playwright, which the `poesia` env does **not** have. On the laptop it was run with
`~/dev/career-assets/.venv/bin/python`. Elsewhere:
`pip install playwright && python -m playwright install chromium`, then
`python tools/render.py in.svg out.png 943 691` (the last two numbers are the viewport).

### What defines the style (read from the pixels, not guessed)

- **Her:** a top bun (ellipse ≈92×68 px); a solid black hair dome that covers the sides to
  the ears; a **centre-parted fringe of 6–7 separate black wedges** fanning from the part and
  tapering to points (one splits in two), with **white forehead showing between them**; two
  small comma-shaped brows at the fringe's outer ends; closed eyes as thick crescents with
  **2–3 lashes at the outer corners only**; a dot nose; a small smile; C-shaped ears with a
  short inner dash; a wide round face (wider than tall); side locks that run from the
  temples past the jaw toward the shoulders.
- **The dog:** a shaggy small dog (Maltese/shih-tzu look): **uneven long tufts with breaks
  in the outline**, ear fur merging into the head, big round black eyes, a small nose and
  mouth, a compact seated body with spiky chest fur, front legs drawn as two lines, and a
  feathery 3–4-tuft tail.
- **Ink:** outlines about 9–12 px at this size; slightly rough brush edges; pure black and
  white (about 14% of pixels are ink); scattered dots and plants as filler.

---

## 2. Facts established this session

- **Claude cannot generate images.** Not Opus, not Claude Code, not on Max. Anthropic's
  vision docs say Claude is "an image understanding model only" (checked 2026-10-07). Max
  buys more Claude usage; it does not include an image model. Claude can only write
  SVG/code and look at images.
- **There is no official Anthropic image tool or MCP.** Any "Claude makes images" setup is
  Claude calling another company's model, via MCP or code.
- **The laptop cannot run image models locally.** Its GPU is a Quadro M1000M with 2 GB.
  The desktop's RTX 3070 has 8 GB, still below the ~16 GB (FP8) that Qwen-Image-Edit
  needs. Whether FLUX.2 klein 4B inference fits in 8 GB is unverified. Plan on cloud or a
  rented GPU. Thresholding and vectorizing run on CPU on either machine.
- **No image-API keys are set** in the environment. The repo's secrets template already has
  slots for `GEMINI_API_KEY`, `OPENAI_API_KEY`, `REPLICATE_API_TOKEN`, `CLOUDFLARE_*`.
- **`galeria` cannot do this yet.** `ImageBackend.generate_image(prompt, style) -> bytes`
  (`src/poesia/galeria/backends.py`) takes text only: no reference image, no seed, no model
  pin. All five backends (Pollinations, Cloudflare, OpenAI, Replicate, procedural) are
  text-to-image, so they would draw a different girl every panel.
- **Gemini image output is probably no longer free.** On 2026-10-07 Gemini's pricing page
  marked it "Not available" on the free tier (one fetch, so confirm it in AI Studio), and
  `gemini-2.5-flash-image` was due to shut down on 2026-10-02.
  [IMAGE_GENERATION_PROVIDERS.md](IMAGE_GENERATION_PROVIDERS.md) was corrected the same day.
  **This backend is a paid backend by design:** reference-image generation has no ongoing
  free API path.

---

## 3. What we tried, and what it showed

All attempts are in `attempts/`. Claude drew everything by placing shapes and coordinates;
no image model was involved.

### 3.1 Autumn walk v1: SVG written by a Python script

`autumn_walk.py` → `autumn_walk.svg/.png`. Her walking the dog on a leash, falling leaves,
sprigs, scattered dots, with an SVG turbulence filter to fake brush wobble.

**Result:** the style family was right, the characters were wrong. The fringe came out as a
sawtooth, the dog looked like a poodle or sheep (evenly scalloped), the lines were clean
vector with no brush quality, the coat was a box and the arms were sticks.

### 3.2 Autumn walk v2: SVG written by hand, with a "brush ink" filter

`autumn_walk_v2.svg/.png`. New filter: turbulence displacement → Gaussian blur (σ 1.2–1.5) →
discrete threshold per RGB channel. **This filter is reusable:** it turns any vector into
pure black and white with rough, rounded brush edges.

**Result:** closer, but `compare_v2.png` (crops of the original next to v2) showed the
features that carry identity were wrong:

- **Her:** the fringe was **inverted** (thick black tongues with thin white gaps, where the
  original has thin tapering wedges over a white forehead); the brows were missing; the head
  was too tall and narrow, so she looked younger; the side locks were too short; the lashes
  were too thin and uniform; the outlines were about 1.5× too thin.
- **The dog:** a symmetric curly puff instead of shaggy uneven locks; eyes too small; it
  stood like a sheep instead of sitting compact; the tail was a blob, not a feathery fan.
- Overall estimate: 50–60% of the way there.

### 3.3 Head trace v3–v5: measured trace plus a scoring metric

Plan: trace her head at the original's exact scale and position, score it, iterate, then
turn the trace into reusable parts that could be reposed.

**Method.** Measured the original with numpy: connected ink components, per-row ink runs,
pixel maps of eyes and brows (`grid_head.png`, `features.txt`, `cols.txt`). Wrote the SVG
in the same 943×691 frame and scored it with `score.py` (box x 200–545, y 30–378/390) and
`score_parts.py`.

**Scorer validated before use:** the original against itself scored 1.000; a blank page
scored IoU 0.000 and recall 0. Ceiling: the original pushed through the same ink filter
scores 0.977 overall (parts 0.93–0.99), so about 0.95 is the most a trace can reach.

| Part IoU | v3 | v4 | v5 | ceiling |
|---|---|---|---|---|
| overall (box to y 378) | — | 0.898 | **0.915** | 0.977 |
| bun | 0.887 | 0.914 | 0.914 | 0.993 |
| dome | 0.919 | 0.942 | 0.942 | 0.982 |
| fringe | 0.873 | 0.880 | 0.880 | 0.960 |
| brows | 0.664 | 0.761 | 0.761 | 0.939 |
| eyes | 0.538 | 0.663 | 0.808 | 0.949 |
| nose+mouth | 0.781 | 0.781 | 0.784 | 0.954 |
| ears | 0.716 | 0.785 | 0.828 | 0.953 |
| jaw | 0.751 | 0.706 | 0.861 | 0.964 |
| lock L / R | 0.738 / 0.716 | 0.749 / 0.726 | 0.825 / 0.829 | 0.943 / 0.925 |

(v3 overall on the y 390 box: IoU 0.862, F1@3px 0.987. The first jaw box also caught the
robe collar; it was split into jaw/lock boxes ending at y 376.)

**Angel's verdict on v5 (`side_v5.png`): worse, despite the higher score.**

- **Gaps in the hair strands:** the white forehead shape reaches above the tops of the
  strands, leaving white notches near the part. The strands have flat, abrupt tops instead
  of partings that start as nothing and widen downward.
- **Irregular eyelashes:** blunt stubs instead of thin, curved, tapering lashes.
- **Thick strokes and inelegant curves**, as before: the jaw and eyes were built from dozens
  of measured points joined by straight segments, copying the JPEG's wobble.

**Root cause.** The metric rewards *where* ink lands, not line *quality* (smoothness, taper,
elegance). Optimising it made the drawing uglier while the number rose. Small features such
as lashes cover too few pixels to move the score. The 2025 SVGenius benchmark predicts this
failure: LLMs break down on complex SVG shapes even at about 16 paths, and a character has
hundreds of segments.

---

## 4. What does not work (do not retry)

| Route | Why it fails |
|---|---|
| Claude drawing the characters in SVG, by script or by hand | Curves come out inelegant; every new pose is new hand geometry; the benchmark predicts this. Ceiling: simple front-facing icons. |
| Tracing by measured points (polylines) | Copies scan noise; produces wobble and flat strand tops. |
| Pixel IoU/F1 as the quality target | Placement only, blind to line quality. At most, use it to check feature *position and size*. |
| Existing `galeria` backends (Pollinations, Cloudflare, OpenAI text, Replicate text) | Text-only: no character consistency. |
| Local diffusion on this laptop | 2 GB VRAM. |
| Training a LoRA straight from the single drawing | Overfits: it redraws the same picture (research §LoRA). |
| PuLID / InstantID | Their face detectors fail on cartoon/anime faces (maintainers confirm). |
| IP-Adapter / InstantStyle alone | Copies the style but loses the specific character. |
| Midjourney | No official API; third-party wrappers break its terms of service. |
| Generative SVG models (OmniSVG, StarVector) | Need 17–26 GB VRAM, flat clipart style, or fail on characters. |
| Centerline vectorizing (autotrace) | Loses the tapered strokes; SVG has no variable-width stroke. |
| Chaining edits from the previous output | Drift and tone shifts compound. Always re-send the original. |

**What does work and is kept:** the ink filter recipe (§3.2), the validated scorer for
placement checks, the clean crops, the feature description in §1, and the research report.

---

## 5. What to do now

### Path A: no keys, no cost (recommended first)

This uses consumer apps Angel may already have. It answers the key question: does any
model keep her fringe, lashes and the dog's fur?

1. In the **Gemini app** (Nano Banana) and in **ChatGPT** (gpt-image), upload
   `reference/original.jpg`. Where the app allows several images, also upload
   `her_only.png` and `dog_only.png`.
2. Use these prompts, **starting a new chat for each one with the original attached** (never
   "now make another"):

   > Draw the same woman and the same dog from the reference image in a new scene: **{scene}**.
   > Keep the woman exactly as drawn: hair in a top bun, centre-parted fringe of separate
   > tapering strands with forehead showing between them, closed eyes with a few lashes at the
   > outer corners, small dot nose, small smile, round wide face, ears showing, long side locks.
   > Keep the dog exactly as drawn: small scruffy dog with uneven shaggy fur, big round black
   > eyes, small nose, feathery tail.
   > Same style: pure black ink line art on a pure white background, thick smooth tapered
   > brush-pen strokes, the same line weight as the reference, chibi proportions, a few small
   > dots and plants as decoration. No grey, no shading, no colour, no hatching, no texture.

   Scenes: `walking together in autumn with falling leaves` · `sitting at a café table` ·
   `the dog jumping for a ball while she laughs` · `seen from behind, walking in the rain
   under an umbrella` · `close-up, she hugs the dog` · `both asleep on a sofa`.
3. Save every output as-is (raw). Bring them to a new Claude Code session and say: "compare
   these against `seeds/characters/couple-ink/reference/` and threshold them". Claude
   compares pairwise against the checklist below and binarises them (§6, stage 1).

**Checklist per image** (pass/fail each):

- bun
- fringe of separate tapering strands with forehead showing
- brows
- closed eyes with outer lashes
- wide round face
- side locks
- dog's shaggy uneven fur
- dog's big eyes
- dog's feathery tail
- no grey or colour
- line weight close to the original

Claude's judgement here is a triage, not the final word: crop the faces before review,
because Claude Code downsizes large images. **Angel's eye is the gate.**

### Path B: with API keys (the durable route)

Keys needed, in priority order. Store each in `secrets/poesia.env.sops.yaml` (decrypt with
the age key; see LOCAL_ONLY.md "Secrets on another machine"), add the name to
`secrets/poesia.env.template.yaml`, and never paste it into chat.

| # | Key (env var) | Where | Unlocks | Price (seen 2026-10-07) | Call shape |
|---|---|---|---|---|---|
| 1 | `GEMINI_API_KEY` (slot exists) | aistudio.google.com, **paid tier with billing**, because image output is not on the free tier | **Nano Banana Pro** `gemini-3-pro-image`: 5 character + 6 object + **3 style** reference slots; my top pick. **Nano Banana 2.1** `gemini-nano-banana-2.1`: 4 character refs, #6 on the Arena edit board, cheapest | Pro $0.134/img; 2.1 $0.0336/img at 1K, about half in Batch | JSON, stdlib-easy |
| 2 | `FAL_KEY` (new) | fal.ai | **Qwen-Image-Edit-2511** (Apache 2.0, 1–3 refs plus a sketch as control; also the stage-3 LoRA base), **Ideogram 3.0 character reference**, **Seedream 5.0** (up to 10 refs), Recraft vectorize, LoRA training/inference | Qwen ~$0.03/MP; Ideogram $0.10–0.20 with a char ref (third-party); Seedream Lite $0.035; Recraft vectorize ~$0.01; Qwen-Edit LoRA training $4/1k steps | JSON, stdlib-easy |
| 3 | `OPENAI_API_KEY` (slot exists) | platform.openai.com | **gpt-image-2.5** (#1 on the Arena image-edit board, 2026-10-06), "one or more" references | gpt-image-2 ~$0.05 medium / ~$0.21 high at 1024² (third-party estimate) | `/images/edits` is multipart (awkward); the Responses API takes JSON with data URLs |
| 4 | `BFL_API_KEY` (new, optional) | bfl.ai | **FLUX.2 pro/max**, up to 8 refs, kept hair detail best in one vendor test. Also an official MCP (`claude mcp add --transport http FLUX https://mcp.bfl.ai`, OAuth) for zero-code trials | $0.045 (pro) / $0.07 (max) per edit | JSON, async polling; result URLs expire after 10 min |

**Minimum useful set: keys 1 and 2.** Together they cover the top pick (Nano Banana Pro),
the cheapest (2.1) and the open-weight fallback (Qwen). Add 3 for the Arena leader. Add 4
only if FLUX is wanted directly; whether fal also serves FLUX.2 with multi-reference was not
verified.

**Budget for the stage-0 test:** 6 models × 6 scenes × 2 seeds = 72 images ≈ **$5–10**.

---

## 6. The staged plan

This is the one copy of the plan; the research report holds the evidence behind it.

| Stage | Action | Cost | Exit criterion |
|---|---|---|---|
| 0 | Fixed-protocol test: Nano Banana Pro, Nano Banana 2.1, gpt-image-2.5, FLUX.2 pro/max, Ideogram 3.0 char ref, Qwen-Image-Edit-2511 (Seedream 5.0 Lite as a cheap 7th). Same 6 scenes (§5), original + both crops re-sent every call, 2 seeds. Keep raw outputs. Score: grey-pixel fraction (luminance 20–235), median stroke width vs original (distance transform along the skeleton), the §5 checklist pairwise, cost/img. | $5–10 | One model passes the checklist on most of 12 panels |
| 1 | Post-process every output: greyscale → upscale 2–4× Lanczos → Otsu/fixed threshold → small morphological close/open → drop specks → optional blur σ≈1.5 + re-threshold at 128. Then optionally **outline**-trace: potrace (`--alphamax 1.0–1.2 --opttolerance 0.2–0.4 --turdsize 10–50`, GPL, as a subprocess) or VTracer (`pip install vtracer`, MIT, `clustering="bw"`, spline mode). Compare with Vectorizer.AI's free watermarked test mode and Recraft vectorize. Tune the threshold on the eyes; lashes are the fragile part. | <$1 | Lashes survive; curves at least as smooth as the original |
| 2 | Code: a new `ReferenceImageBackend` Protocol, separate from `ImageBackend` so the existing backends still type-check: `generate_image(prompt, style=None, *, references: Sequence[bytes], model: str, seed: int \| None) -> bytes`. Lazy stdlib HTTP like `pollinations.py`. A **manifest per panel** (model ID, reference SHA-256, prompt, params, seed). Binarise/vectorise as a separate pure function. Expose through the `poesia galeria` CLI and wrap it in a thin Claude Code skill. Use MCP only for trials. | $0.03–0.13/panel | 20 panels in sequence without drift |
| 3 | Only if stage 2 drifts: bootstrap 40–60 variants with the winner, threshold, curate the 15–30 that pass the checklist, train a LoRA on an **Apache-2.0** base (**Qwen-Image-Edit-2511**, best single open bet, takes a rough sketch as control; or FLUX.2 klein 4B). BFL guidance: 15–40 images, 1,500–3,000 steps, LR 8e-5–1e-4. Run on fal ($0.40–4/run) or a Vast.ai 4090 (~$0.32–0.50/h). | $1–10/run | LoRA beats the hosted winner on the same checklist |

**What would prove this plan wrong:**

- **No model keeps the fringe, lashes and dog fur on most panels** → skip to stage 3, Qwen
  first.
- **Thresholding kills the lashes at every setting** → generate at higher resolution, or
  make lashes a vector-edited part.
- **potrace curves come out wobblier than Vectorizer.AI's** → use Vectorizer.AI for the trace.

**Where the LLM fits:** writing prompts, catching coarse failures (missing bun, wrong dog,
grey), pairwise checklist review, and *editing* a traced SVG (group parts, swap an
expression). Not drawing curves, and not the final judge.

---

## 7. Open decisions for Angel

Settled 2026-10-07: the reference drawing goes in git (§1).

1. **Personal or commercial use?** This decides the licences. Commercial-clean weights are
   Qwen-Image family and FLUX.2 klein 4B (Apache 2.0). FLUX.2 dev, klein 9B and Kontext dev
   are non-commercial unless used through a host whose terms grant commercial rights.
   ControlNet LineArt-Anime is non-commercial.
2. **Which keys and what budget** (§5 Path B). Stage 0 needs about $5–10.
3. **Focus order:** her first or the dog first. Earlier lean: her head first (it carries
   identity), the dog second (the fur needs a different technique).

## 8. Unverified (check before relying on)

- The Gemini free-tier "Not available" reading (one tool-summarised fetch).
- Official per-image prices for gpt-image-2.5; whether OpenAI still offers `input_fidelity`.
- Leonardo's character-reference feature (not researched).
- Whether Google's or OpenAI's terms allow training a LoRA on their outputs (matters for
  stage 3).
- USO's licence.
- Whether the BFL, fal or Replicate MCP servers accept a local file from Claude Code rather
  than a public URL.
- How well Claude judges ink or line art specifically (no evidence found).
- How well pose control (OpenPose) works with chibi proportions or a dog (no source covers
  it; scribble/lineart control from a rough sketch is the safer guess).

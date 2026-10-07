# Test six models, then threshold everything

**Bottom line.** As of 2026-10-07, no tool is proven to hold both your characters *and* your exact thick-ink, pure black/white line style. I found no published benchmark of pure B/W ink fidelity for any model, hosted or open. So this is an empirical question, and you can answer it for about $5–10 in an afternoon. Run the actual drawing through six reference-conditioned models with one fixed protocol, then put every output through a deterministic threshold step. Every raster model emits grey anti-aliasing, so "no grey" has to come from post-processing, not from the model.

On documented interface alone, my prior is Nano Banana Pro. It is the only hosted model with separate character-reference and style-reference slots. Prior is not evidence, though, and practitioner reports conflict on whether GPT Image or Nano Banana keeps identity better. The durable pipeline has three parts:

1. A new reference-capable Protocol in `galeria`, calling the winning hosted model over stdlib HTTP and logging a manifest.
2. Binarise, plus optional potrace/VTracer vectorisation.
3. Only if hosted drift proves unacceptable across ~20 panels: a LoRA on an Apache-2.0 open model, trained on a curated synthetic set. Candidates are FLUX.2 [klein] 4B and Qwen-Image-Edit-2511. Run it on fal or a rented 4090 for a few dollars.

Hand-written SVG from Claude is not a viable drawing route, and the 2025 benchmarks explain why. Vectorising a good raster is the solved part of the problem. Claude's job is prompt writing, failure triage and orchestration, not rendering and not final judgement.

Unless a different date is given, every source below was accessed 2026-10-07. "Anecdotal" marks single-author blogs, forum posts and vendor marketing.

## Seven hosted models take reference images, but only two separate character from style

Every major lab now ships multi-reference image editing. They differ in whether a reference means "this character" or "this style":

- **Gemini.** Nano Banana Pro (`gemini-3-pro-image`) accepts up to 5 character references, 6 object references and **3 style references**. Nano Banana 2.1 (`gemini-nano-banana-2.1`) accepts 4 character references and has no style slot. Flash Lite has no character slot and is documented as "not optimized" for multi-reference work ([Gemini image docs](https://ai.google.dev/gemini-api/docs/image-generation)).
- **Ideogram 3.0.** Exactly **one** `character_reference_images` entry plus several `style_reference_images` ([Ideogram API](https://developer.ideogram.ai/api-reference/api-reference/generate-v3)).
- **Everyone else** steers references through the prompt ("apply the style of image 1"), with no separate slots:
  - FLUX.2: up to 8 references via the API ([BFL FLUX.2 editing](https://docs.bfl.ai/flux_2/flux2_image_editing)).
  - Seedream 5.0: up to 10 references ([fal Seedream 5 Lite](https://fal.ai/models/fal-ai/bytedance/seedream/v5/lite/edit)).
  - GPT Image 2.5: "one or more" references, no documented cap ([OpenAI guide](https://developers.openai.com/api/docs/guides/image-generation)).
  - Runway gen4_image: 1–3 references ([Runway pricing](https://docs.dev.runwayml.com/guides/pricing/)).

Midjourney still has no official API. Third-party wrappers automate its UI against the terms of service ([unifically, 2026-08-18](https://unifically.com/blogs/midjourney-api)), so it is out.

The quality evidence is thin and contradictory:

- **Arena Image Edit leaderboard (updated 2026-10-06, ~31M votes)** ([Arena](https://arena.ai/leaderboard/image-edit)). This is the only large dated benchmark. **gpt-image-2.5-sunburst** leads at 1524, then gpt-image-2.5-flare, gpt-image-2, Grok Imagine 2.0, MAI-Image-2.6 and **Nano Banana 2.1 (1428)**. Seedream 5.0 Pro is 10th, Nano Banana Pro 12th, Qwen-Image-2.1 18th and Ideogram 4.5 20th. No FLUX model is in the top 25. Arena measures general edit preference, not character consistency or line-art fidelity, so use it to build a shortlist, not to pick a winner.
- **Practitioner tests (all anecdotal, single author, mostly photo references) split:**
  - GPT Image 2 beat Nano Banana 2 "by a mile" on reference likeness over 10 prompts ([aiblewmymind](https://aiblewmymind.substack.com/p/nano-banana-2-vs-gpt-images-2)).
  - GPT Image 2 stayed "pixel-stable across 4 sequential edits" while Nano Banana 2 drifted on edit 3 ([ropewalk.ai, ~2026-09-29](https://ropewalk.ai/blog/gpt-image-2-vs-nano-banana-2-vs-imagen-4-vs-flux-2-2026)).
  - The other way: Nano Banana Pro beat FLUX 2 on reference consistency ([morphed.app](https://morphed.app/blog/flux-2-vs-nano-banana-pro)), and Nano Banana beat Kontext on anime-style consistency ([flash-image.art](https://flash-image.art/blog/nano-banana-vs-flux-kontext); a reseller page).
  - On hair detail, which matters for your bun and tapered fringe, FLUX Kontext kept hairstyle details that Nano Banana "altered slightly" ([PicLumen vendor test](https://www.piclumen.com/blog/flux-kontext-vs-nano-banana/)).
  - OpenAI's own guide says GPT Image "may occasionally struggle to maintain visual consistency for recurring characters" ([OpenAI guide](https://developers.openai.com/api/docs/guides/image-generation)).

Treat the evidence on what matters most here as zero: **I found no controlled test of pure B/W ink line-art fidelity, and no test of small-animal identity, for any model.** The indirect signal points toward grey. Widely shared Nano Banana prompts spell out "no shading, no grayscale… pure white" ([Awesome-Nano-Banana-images](https://github.com/PicoTrex/Awesome-Nano-Banana-images/blob/main/README_en.md)), which implies drift to grey is the default failure. Users also report that chained edits shift tone and over-sharpen ([Adobe community report](https://community.adobe.com/bug-reports-403/generate-from-nano-banana-for-the-2nd-time-always-changed-the-image-tone-1483534), anecdotal).

Two rules follow. Re-send the original drawing on every call and never chain from a previous output. Expect line weight and taper to drift first, because these models re-render strokes rather than copy them. Your character's identity rests on a few strong cues (bun, centre-parted fringe strands, closed lashed eyes, the dog's scruff), so it may survive better than photo likeness does. Fringe-strand count and scruff texture are the likely failure points.

## The decisive test costs under $10 and should run today

Compare the shortlist in one script with a fixed protocol:

1. **Inputs.** Send the drawing on every call. Also send a cropped dog-only image as a second reference: separate subject references are the documented way to handle a second character. Use six fixed prompts, e.g. "walking in autumn leaves", "sitting at a café table", "dog jumping for a ball", "back view in rain", "close-up laughing", "asleep on a sofa". Append the same no-grey suffix to each.
2. **Outputs.** Keep the raw PNG before thresholding.
3. **Scoring.** Score each raw output on four things:
   - The fraction of grey pixels (luminance 20–235).
   - Stroke width compared with the reference. Median distance-transform value along the skeleton is one way to measure it.
   - A human pairwise check against a named-trait checklist: bun, fringe strands, lashes, dog scruff and proportions.
   - Cost per image.

The metrics are my design, not a published method. That is the point: nobody has published one for this style.

| Model (call it via) | Why it is on the list | Price per image | Licence of outputs |
| --- | --- | --- | --- |
| Nano Banana Pro (Gemini API) | Only separate character + style slots | $0.134 (1K/2K) ([Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)) | Commercial via the paid API |
| Nano Banana 2.1 (Gemini API) | #6 on Arena edit, cheapest strong option | $0.0336 at 1K, about half in Batch | Commercial via the paid API |
| gpt-image-2.5-sunburst (OpenAI) | #1 on Arena edit, practitioner identity wins | ~$0.05 medium / ~$0.21 high for gpt-image-2 at 1024² (third-party estimate from OpenAI's calculator, [aifreeapi](https://www.aifreeapi.com/en/posts/openai-image-generation-api-pricing)), plus input tokens | Commercial via the paid API |
| FLUX.2 pro/max (BFL) | 8 references; hair-detail anecdote | $0.045 edit (pro) / $0.07 (max) ([BFL pricing](https://docs.bfl.ai/quick_start/pricing)) | Commercial via the API |
| Ideogram 3.0 character ref (Ideogram or fal) | Explicit character slot + style refs | $0.10–0.20 with a character ref (third-party, [Puter](https://developer.puter.com/tutorials/ideogram-api-pricing/)) | Commercial via the API |
| Qwen-Image-Edit-2511 (fal) | **Apache-2.0 open weights: the stage 3 LoRA could later train on this same model** | $0.03/MP (third-party, [pricepertoken](https://pricepertoken.com/fal-ai-pricing)) | Apache 2.0 weights |

Six models × six prompts × two seeds is 72 images, roughly **$5–8**. Seedream 5.0 Lite ($0.035, 10 refs, [fal](https://fal.ai/models/fal-ai/bytedance/seedream/v5/lite/edit)) is a cheap seventh. Its Pro tier advertises "sketch completion" ([fal](https://fal.ai/models/bytedance/seedream/v5/pro/edit)), which nobody has tested on ink.

The six models need four keys: Gemini, OpenAI, BFL and fal. fal also hosts Ideogram Character and Recraft vectorize.

How easy each one is from stdlib `urllib` (my reading of the documented request shapes, untested):

- **Easy, JSON body:** Gemini, BFL and fal. BFL is asynchronous: you poll for the result, and result URLs expire after 10 minutes ([BFL](https://docs.bfl.ai/flux_2/flux2_image_editing)).
- **Awkward, multipart form data:** Ideogram, and OpenAI's `/images/edits`. OpenAI's Responses API takes base64 data URLs in JSON instead.

Recraft V4 Styles is deliberately left off the shortlist. It is the only hosted model that returns **native SVG**, and it builds a reusable style from 1–10 reference images ([Recraft styles docs](https://www.recraft.ai/docs/api-reference/styles)). But it is a style system with no character-reference feature, and nothing shows it can draw tapered thick ink. Its vendor-run "91.6% preferred" figure is marketing ([Runware guide](https://runware.ai/docs/models/recraft-v4-styles/guides/styles-from-references)). Add it as a seventh entry only if style fidelity turns out to be the bottleneck and identity does not.

## Pure black and white is a post-processing guarantee, and vectorising is the solved half

**Diffusion models do not emit binary pixels, and no source shows one that does** ([Wikipedia: image tracing](https://en.wikipedia.org/wiki/Image_tracing) on why anti-aliasing produces grey). The fix is deterministic and runs on CPU, so your 2 GB GPU is irrelevant here:

1. Convert to greyscale.
2. Upscale 2–4× with Lanczos.
3. Apply an Otsu or fixed threshold.
4. Run a small morphological close/open.
5. Drop specks.
6. Optionally Gaussian-blur (σ≈1.5) and re-threshold at 128 to round off pixel stair-steps.

Thick ink survives this well. The lashes are the fragile part, so tune the threshold on the eye region. Thresholding preserves line *weight* but cannot repair line *quality* such as wobble or broken strokes.

Outline tracing adds a vector stage and keeps the tapers. **SVG has no variable-width stroke.** The W3C ruled it out of SVG2 in 2013 ([W3C minutes](https://www.w3.org/2013/02/06-svg-minutes.html)). A tapered brush stroke can therefore only be a filled outline, which is exactly what outline tracers produce. Centerline tracing (autotrace) throws the taper away and is the wrong tool for this style ([autotrace](https://linux.die.net/man/1/autotrace)).

The two Python-callable tracers:

| Tracer | Licence | Settings to start from | Notes |
| --- | --- | --- | --- |
| potrace 1.16 ([potrace](https://potrace.sourceforge.net/)) | GPL | `--alphamax 1.0–1.2 --opttolerance 0.2–0.4 --turdsize 10–50` on a binarised PBM | Unchanged since 2019. Fine as a subprocess, a constraint only if you distribute a combined binary. StarVector's benchmark found it gives "more sharp results" than VTracer and AutoTrace ([arXiv 2312.11556](https://arxiv.org/html/2312.11556v4)). |
| VTracer 1.0.0-alpha.4 ([GitHub](https://github.com/visioncortex/vtracer)) | MIT | `pip install vtracer`, `clustering="bw"`, `mode spline`, `--simplify 1.5` | The MIT alternative. |

Vectorizer.AI is the commercial quality leader by user report only. Its test-mode API is free (watermarked), and production costs $0.05–0.20 per image ([Vectorizer.AI pricing](https://vectorizer.ai/pricing)). Recraft vectorize costs about $0.01 ([fal](https://fal.ai/models/fal-ai/recraft/vectorize)). No independent head-to-head of these four tracers on character ink art exists. Running your one drawing through all four costs pennies and settles it.

**Is a vector route viable? Yes for output, no for drawing.** The SVGenius benchmark (June 2025, 22 models) found frontier LLMs reach 70–80% on SVG understanding but "struggle with structural synthesis". Claude 3.7 Sonnet led image-to-SVG, yet its structural-similarity score fell from 23.7 to 15.5 between easy and hard items. "Hard" averages only 16 paths and ~1,150 control points ([SVGenius](https://arxiv.org/html/2506.03139v1)). A traced chibi character has hundreds of segments, so the inelegant curves you got are what the benchmark predicts, not bad luck. Claude versions after 3.7 are untested.

Generative SVG models do not fix this either. OmniSVG has a character-reference task, but it needs 17–26 GB of VRAM, draws in a flat-fill clipart style, and is scored only by GPT-4o on its own benchmark ([OmniSVG](https://github.com/OmniSVG/OmniSVG)). Its dataset is CC BY-NC-SA. StarVector "fails on illustrations and more complex character images" ([OmniSVG NeurIPS paper](https://papers.nips.cc/paper_files/paper/2025/file/a510f05a574d4203ef3952973672fe2f-Paper-Conference.pdf)).

The vector stage is worth keeping for three jobs: crisp output, smoothing a model's wobble, and letting an LLM *edit* a trace (group parts, swap an expression, transform a limb group). It should not draw curves.

## An open-weight LoRA is the insurance policy, not the starting point

Build stage 3 only if the stage-0 winner drifts unacceptably over about 20 panels, or if per-image cost or vendor lock-in starts to matter.

Training a LoRA on a single image overfits. It reproduces the source composition and leaks background and position ([Civitai single-image LoRA](https://civitai.com/articles/1058/single-image-lora-part-2), anecdotal and likely pre-2025; [T-LoRA, arXiv 2507.05964](https://arxiv.org/abs/2507.05964v1)). The 2025–26 standard practice is to bootstrap a synthetic set instead:

1. Generate 40–60 variants with an edit model, varying pose, angle and scene. The [Floyo Kontext workflow](https://www.floyo.ai/workflows/flux-kontext-single-image-to-charact-u1fosxceuqr5) uses 60 prompts, and [lovisdotio's ComfyUI workflow](https://github.com/lovisdotio/workflow-comfyui-single-image-to-lora-flux) automates 20.
2. Threshold every candidate *before* curating, so the model never learns grey.
3. Keep 15–30 images that are on-model, checking the named traits rather than general resemblance.
4. Train. BFL's guidance is 15–40 images, 1,500–3,000 steps, learning rate 8e-5 to 1e-4 ([HF/BFL klein LoRA blog](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora)).

Your stage-0 outputs are the obvious seed for this dataset. One caveat: I did not check whether Google's or OpenAI's terms restrict using their outputs to train another model. Read them before you do it.

Licence decides the base model:

| Base | Licence | Fit |
| --- | --- | --- |
| **FLUX.2 [klein] 4B** | **Apache 2.0** | LoRA in <1 h on a 4090 (<24 GB) ([BFL klein](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence)) |
| **Qwen-Image-Edit-2509/2511** | **Apache 2.0** | 1–3 refs plus native sketch/edge/keypoint control. ~16 GB at FP8. 2511 (Dec 2025) improves multi-subject consistency ([Qwen-Image](https://github.com/QwenLM/Qwen-Image)) |
| FLUX.2 [dev], klein 9B, FLUX.1 Kontext dev | Non-commercial | Self-hosted commercial use needs a BFL licence. Replicate states commercial use is permitted through its platform ([Replicate](https://replicate.com/black-forest-labs/flux-2-dev); [Kontext licence thread](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/discussions/6)) |
| ControlNet LineArt-Anime | Non-commercial | Avoid in a commercial path ([RunComfy](https://www.runcomfy.com/comfyui-nodes/comfyui_controlnet_aux/AnimeLineArtPreprocessor)) |

**Qwen-Image-Edit-2511 is the best single open bet.** It is Apache-licensed and takes both a reference and a rough-sketch control image, which gives you a "you sketch the panel, it inks it on-model" mode. Put the control image first ([Draw Things wiki](https://wiki.drawthings.ai/wiki/Qwen_Image_Edit_2509_TB_UT_transcript)). A community lineart-interpolation LoRA shows the model can be pushed into the line-art domain ([EQUES](https://huggingface.co/EQUES/qwen-image-edit-2511-lineart-interpolation)). Qwen Image 2.0, by contrast, is API-only.

Tools to skip, with the reason:

- **PuLID and InstantID.** Their face detectors fail on stylised faces ("PuLID doesn't support anime faces", [issue #123](https://github.com/ToTheBeginning/PuLID/issues/123)).
- **IP-Adapter/InstantStyle.** It transfers style but loses fine-grained identity ([AnimeAdapter, arXiv 2605.20237](https://arxiv.org/html/2605.20237v1)).
- **USO.** ByteDance, CVPR 2026, ~16–18 GB, native ComfyUI ([USO](https://github.com/bytedance/USO)). It is the specialised subject-plus-style option, and I did not verify its licence.
- **OpenPose.** It assumes normal human proportions. For chibi panels, scribble or lineart control from your own sketch is the safer guess. No source covers chibi or dog pose.

Where to run it (your 2 GB GPU rules out local runs):

- **Training on fal:** about $0.40–4 per Qwen-Edit run at $4 per 1k steps ([fal trainer](https://fal.ai/models/fal-ai/qwen-image-edit-2509-trainer)). The Kontext trainer is $2.50 per 1k steps.
- **Training on a rented GPU:** a Vast.ai 4090 at ~$0.32–0.50/h ([Thunder Compute, 2026-10-01](https://www.thundercompute.com/blog/vast-ai-vs-thunder-compute)) makes a klein-4B LoRA well under $1.
- **Inference on fal:** `qwen-image-edit-2511/lora` costs $0.035/MP ([fal](https://fal.ai/models/fal-ai/qwen-image-edit-2511/lora)), with no cold-start billing on public endpoints.
- **ComfyUI, only if a custom graph turns out to be necessary:** code against the Comfy API v2. It is beta 0.1.x, and the same calls reach Comfy Cloud, a deployment or a self-hosted pod ([Comfy docs](https://docs.comfy.org/api-reference/v2/overview)). Run it on Modal (L40S ~$1.95/h per-second, third-party copy of pricing, [Spheron](https://www.spheron.network/blog/modal-gpu-pricing-2026-per-second-billing/)) or RunPod Serverless.
- **Not Colab:** it does not guarantee a GPU.

## The galeria backend owns the capability; MCP is only an exploration probe

`ImageBackend.generate_image(prompt, style) -> bytes` cannot carry a reference image, a seed or a model pin. Add a separate `ReferenceImageBackend` Protocol rather than widening the existing one, so the Pollinations, Cloudflare and procedural backends still type-check. Its shape: `generate_image(prompt, style=None, *, references: Sequence[bytes], model: str, seed: int | None)`.

Implement it with lazy stdlib HTTP, following the `pollinations.py` precedent. Write a manifest per panel: model ID, reference SHA-256, prompt, parameters and seed. Then run the binarise/vectorise step as a separate pure function the CLI can toggle. Expose it through the existing `poesia` CLI and wrap that CLI in a thin Claude Code skill.

Anthropic's engineering guidance supports this shape: agents writing code against tools cut one workflow from 150k to 2k tokens ([Anthropic, Nov 2025](https://www.anthropic.com/engineering/code-execution-with-mcp)). Benchmarks of CLI versus MCP conflict. One found CLI 10–32× cheaper ([Scalekit](https://www.scalekit.com/blog/mcp-vs-cli-use)); another found parity, because Claude Code defers schema loading ([Checkly](https://www.checklyhq.com/blog/mcp-vs-cli-token-efficiency/)). Reproducibility, not tokens, decides it here. Hosted gateways choose models dynamically, and the community `nanobanana-mcp-server` auto-routes by prompt keyword ([repo](https://github.com/zhongweili/nanobanana-mcp-server)), so the choices land in a transcript rather than a committed artifact.

MCP still earns a place for zero-code eyeballing before you write the backend:

- **BFL's official hosted server:** `claude mcp add --transport http FLUX https://mcp.bfl.ai`. OAuth, all FLUX.2 models, multi-reference ([flux-mcp](https://github.com/black-forest-labs/flux-mcp)). Whether it accepts a local file from Claude Code, rather than a chat attachment, is unverified.
- **Hugging Face's `hf.co/mcp` Spaces Tools:** free but rate-limited Kontext on ZeroGPU ([HF blog](https://huggingface.co/blog/claude-and-mcp)).
- **fal's hosted MCP:** reaches its whole catalogue with your key ([fal MCP](https://fal.ai/docs/documentation/setting-up/mcp)).

OpenAI, Ideogram and Stability have no vendor MCP server; the GitHub 404s and `gh search` results are recorded in the research notes. Recraft archived its local server on 2026-07-13 in favour of an OAuth remote. Plan for that kind of churn.

Claude cannot generate images: it is "an image understanding model only" ([Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)). It is good at writing prompts and triaging coarse failures (missing bun, wrong dog, grey shading). It is a weak judge of fine style:

- Claude Code's Read tool downsizes images and re-encodes anything still over 500 KB as JPEG, which can erase lash-level detail. Crop the faces before review ([tools reference](https://code.claude.com/docs/en/tools-reference)).
- The best MLLM-judge evidence is from 2024 models. GPT-4o reached 83% concept-preservation agreement with humans on DreamBench++, and Claude 3.5 74% on a related measure ([arXiv 2406.16855](https://arxiv.org/pdf/2406.16855)). Pairwise comparison is the most stable judging format ([MLLM-as-a-Judge](https://arxiv.org/pdf/2402.04788)).

Use Claude for labelled pairwise rubric checks, and keep your own approval as the gate.

## Two claims in IMAGE_GENERATION_PROVIDERS.md are now wrong

`docs/IMAGE_GENERATION_PROVIDERS.md` (2026-08-03) ranks the "Google Gemini free tier" #2 at 3.60 for its image quality. **Gemini's pricing page now marks image output "Not available" on the free tier for every image-output model** ([Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)). That rests on one tool-summarised fetch, so confirm it in AI Studio. If it holds, the row drops out of the free ranking.

The same section lists `gemini-2.0-flash-preview-image-generation`. Separately, `gemini-2.5-flash-image` was scheduled to shut down on **2026-10-02**. Current IDs are `gemini-nano-banana-2.1`, `gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image` and `gemini-3-pro-image` ([Gemini image docs](https://ai.google.dev/gemini-api/docs/image-generation)).

More broadly, that document's free-tier framing does not carry over to this task. Reference-image conditioning has no ongoing free path except rate-limited Hugging Face ZeroGPU Spaces, so the ink-character backend is a paid backend by design. At Nano Banana 2.1 Batch rates, 100 panels cost under $2.

## Conclusion

The staged plan:

| Stage | Action | Cost | Exit criterion |
| --- | --- | --- | --- |
| 0 (today) | Six-model fixed-protocol test, raw outputs scored on grey fraction, stroke width and trait checklist | $5–10 | One model keeps all named traits on most of 12 panels |
| 1 (today) | Threshold + potrace/VTracer, compared with Vectorizer.AI test mode and Recraft | <$1 | Lashes survive; curves at least as smooth as the reference |
| 2 (days) | `ReferenceImageBackend` + manifest + CLI + skill, using the stage-0 winner | $0.03–0.13/panel | 20 panels in sequence without drift |
| 3 (only if 2 drifts) | Bootstrap 40–60 images, threshold, curate 15–30, Apache LoRA on Qwen-Image-Edit-2511 or klein 4B | $1–10 per run | LoRA beats the hosted winner on the same checklist |

This plan rests on one bet: that a hosted model plus thresholding can hold your two characters well enough. Three results would prove it wrong:

- **No shortlisted model keeps the fringe, lashes and dog scruff on most panels.** Skip stage 2's hosted backend and go straight to stage 3. Reach for Qwen first, because it doubles as a stage-0 contestant.
- **Thresholding destroys the lashes at every setting.** Generate at higher resolution, or move the lashes to a vector-edited part.
- **potrace curves come out visibly wobblier than Vectorizer.AI's.** Make Vectorizer.AI the trace stage.

The deeper shift is in what "exact ink style" means. No model guarantees it, so it becomes a two-part contract: the generator supplies identity and composition, and a deterministic, testable post-processor supplies the binary ink. That split makes style fidelity something PoesIA can measure and unit-test.

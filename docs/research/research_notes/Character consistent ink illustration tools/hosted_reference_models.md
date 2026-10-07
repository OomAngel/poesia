# Hosted reference-image models for character- and style-consistent ink illustration (as of 2026-10-07)

Scope: hosted/API models that can take one reference drawing (a thick black-ink, pure B/W chibi woman plus a scruffy small dog) and produce new comic panels that keep (a) character identity and (b) the exact ink style. Generic text-to-image provider coverage is in `docs/IMAGE_GENERATION_PROVIDERS.md`. These notes do not repeat it, except where it is now wrong (see the Gemini free-tier correction below).

All "seen" dates are 2026-10-07 unless stated otherwise. Snippets from third-party aggregators or resellers are labelled as such. No source here is older than 2025, except that Runway's API launch price is from May 2025.

## Which current models support reference-image conditioning, and how (with limits, price, API access)

### Takeaway
Every major lab now ships multi-reference image editing. The documented caps per request are: Gemini Nano Banana 2.1 / 2 at 4 character refs + 10 object refs (14 total); Nano Banana Pro at 5 character + 6 object + 3 style refs; FLUX.2 at 8 refs via API; Seedream 5.0 at 10; Recraft V4 Styles at 1–10 style refs; Runway gen4_image at 1–3; Ideogram 3.0 at exactly 1 character ref plus several style refs. OpenAI documents "one or more" references with no maximum. Midjourney still has no official API. At about $0.03–$0.08 per 1K image, the cheapest strong options are Nano Banana 2.1, Seedream 5.0 Lite, FLUX.2 pro and Qwen Image Edit.

### Cited Findings

**Google Gemini ("Nano Banana" line)**
- Current model IDs: `gemini-nano-banana-2.1` (Nano Banana 2.1, recommended for new projects), `gemini-3.1-flash-lite-image` (Nano Banana 2 Lite, "fastest and cheapest"), `gemini-3.1-flash-image` (Nano Banana 2), `gemini-3-pro-image` (Nano Banana Pro), and `gemini-2.5-flash-image` (original Nano Banana, legacy). — [Gemini image-generation docs](https://ai.google.dev/gemini-api/docs/image-generation)
- Reference caps. All models allow "up to 14 reference images" in total. Nano Banana 2.1 and 3.1 Flash Image: up to 10 object images and up to 4 character images. 3 Pro Image: up to 6 object images, up to 5 character images and "up to 3 images to be used as style references". Flash Lite: 14 object images, no character slot, and documented as "Not optimized" for multi-reference or multi-turn editing. — [Gemini image-generation docs](https://ai.google.dev/gemini-api/docs/image-generation)
- Nano Banana Pro is the only Gemini model with a documented style-reference slot. That matters for "exact ink style". — [Gemini image-generation docs](https://ai.google.dev/gemini-api/docs/image-generation)
- `gemini-2.5-flash-image` "will be shut down on October 2, 2026", so as of today (2026-10-07) it should be gone. Do not build on it. — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Paid per-image prices at Standard tier (Batch/Flex is about half):
  - Nano Banana 2.1: $0.0336 (1K), $0.0504 (2K), $0.0756 (4K)
  - Nano Banana 2 (3.1 Flash Image): $0.045 (0.5K), $0.067 (1K), $0.101 (2K), $0.151 (4K)
  - Nano Banana 2 Lite: $0.0336 (1K only)
  - Nano Banana Pro: $0.134 (1K/2K), $0.24 (4K)
  - Input images on Pro are billed at 560 tokens each, about $0.0011.

  — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- **Free tier: the Gemini pricing page marks image output "Not available" on the free tier for every image-output model.** This contradicts `IMAGE_GENERATION_PROVIDERS.md` §3 (dated 2026-08-03), which presents Gemini image generation as a free option. — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). The page I fetched did not list Imagen models.
- Likeness/content policy: the image docs set no specific rule on drawing real people. They only say you must have the "necessary rights" to uploaded images, must not create content that infringes rights or is meant to "deceive, harass, or harm", and are bound by the Prohibited Use Policy. The docs link to SynthID watermarking, but the fetched text was truncated. — [Gemini image-generation docs](https://ai.google.dev/gemini-api/docs/image-generation)
- Resolution: 1K by default, with 2K and 4K available. 512px only on 3.1 Flash Image. Lite is 1K only. The "K" must be uppercase, because "1k" is rejected. — [Gemini image-generation docs](https://ai.google.dev/gemini-api/docs/image-generation)

**OpenAI GPT Image**
- The current docs name `gpt-image-2.5-sunburst` (recommended "where editing precision matters most") and `gpt-image-2.5-flare` (fast everyday generation). `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1` and `gpt-image-1-mini` are still priced. — [OpenAI image-generation guide](https://developers.openai.com/api/docs/guides/image-generation); [OpenAI pricing](https://developers.openai.com/api/docs/pricing)
- Reference images: "one or more images as a reference", with no documented maximum. The worked example uses 4 input images. Inputs can be URL, base64 data URL or Files API ID. If you send a mask with several images, it applies to the first image. — [OpenAI image-generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- Transparent background is supported (`background: "transparent"` with png/webp). Quality levels are low/medium/high/auto, plus xhigh and max on the 2.5 models. — [OpenAI image-generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- OpenAI's own listed limitation: the model "may occasionally struggle to maintain visual consistency for recurring characters or brand elements". — [OpenAI image-generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- Token prices per 1M tokens:
  - gpt-image-2 / 2.5: $8 image input, $30 image output
  - gpt-image-1.5: $8 image input, $32 image output
  - gpt-image-1: $10 image input, $40 image output
  - gpt-image-1-mini: $2.50 image input, $8 image output
  - Batch is half price.
  - The pricing page lists no free tier for images.

  — [OpenAI pricing](https://developers.openai.com/api/docs/pricing)
- Approximate gpt-image-2 cost per 1024² image (third-party figures derived from OpenAI's calculator, checked 2026-09-06): about $0.006 low, $0.053 medium, $0.211 high. Reference-image input tokens come on top. — [aifreeapi (third-party)](https://www.aifreeapi.com/en/posts/openai-image-generation-api-pricing); [HN thread](https://news.ycombinator.com/item?id=47853328)
- The `input_fidelity` parameter (high-fidelity reference preservation in the gpt-image-1 era) did not appear in the truncated guide text I fetched. Unverified for the 2.x models.

**Black Forest Labs FLUX**
- FLUX.2 editing takes "up to 8 [reference images] via API, up to 10 in playground". Fields are `input_image`, `input_image_2`, and so on. Auth is the `x-key` header. The call is async: you get a `polling_url` and read `result.sample` once the status is Ready. Result URLs expire after 10 minutes. Output is up to 4MP. — [BFL FLUX.2 editing docs](https://docs.bfl.ai/flux_2/flux2_image_editing)
- Style transfer works by prompt, with references indexed by number ("Apply the style of image 1 to the entire new scene"). There is no dedicated character-consistency feature. BFL claims you can swap "people or animals while keeping proportions perfect". — [BFL FLUX.2 editing docs](https://docs.bfl.ai/flux_2/flux2_image_editing)
- Prices:
  - FLUX.2 klein 4B: from $0.014
  - FLUX.2 klein 9B: from $0.015
  - FLUX.2 pro: from $0.03 for text-to-image, $0.045 for edit
  - FLUX.2 flex: from $0.05
  - FLUX.2 max: from $0.07
  - FLUX.1 Kontext pro / max: $0.04 / $0.08
  - FLUX 3 Image: $0.041 (768sq) to $0.607 (4K)
  - FLUX.2 [dev] is local only.

  — [BFL pricing](https://docs.bfl.ai/quick_start/pricing)
- A fine-tuned endpoint `flux-2-klein-9b-kv-finetuned` is in public beta at the base price. It could be relevant for locking a specific ink style through fine-tuning. — [BFL pricing](https://docs.bfl.ai/quick_start/pricing)
- FLUX.1 Kontext natively takes a single image. fal hosts an "Experimental version of FLUX.1 Kontext [max] with multi image handling" at $0.08/image. — [fal Kontext max multi](https://fal.ai/models/fal-ai/flux-pro/kontext/max/multi)
- FLUX 3 Image's reference-image support was not documented on the editing page I fetched.

**Ideogram**
- The Ideogram 3.0 generate endpoint is `POST https://api.ideogram.ai/v1/ideogram-v3/generate`. It uses multipart/form-data with an `Api-Key` header. — [Ideogram API reference](https://developer.ideogram.ai/api-reference/api-reference/generate-v3)
- Reference fields:
  - `character_reference_images`: "currently only supports 1 character reference image", with an optional mask.
  - `style_reference_images`: several images allowed, no count cap stated.
  - Limits: 25MB per image, 50MB per request.
  - The docs set no human-face requirement.

  — [Ideogram API reference](https://developer.ideogram.ai/api-reference/api-reference/generate-v3)
- Character-reference pricing (3.0): $0.10 Turbo, $0.15 Default, $0.20 Quality per image, against $0.03/$0.06/$0.09 without a reference. These are third-party figures, last updated June–August 2026. Character-ref pricing for Ideogram 4.x was not found. — [Puter pricing breakdown](https://developer.puter.com/tutorials/ideogram-api-pricing/); [eesel](https://www.eesel.ai/blog/ideogram-pricing)
- Ideogram Character is also on Replicate and fal. Muapi charges $0.15/image. — [Muapi](https://muapi.ai/comparison/ideogram-character)

**Midjourney**
- As of 2026-08-18 there is no official public API. Third-party "Midjourney APIs" automate the Discord/web UI against the ToS ("You may not use automated tools…"), so accounts risk being banned. PiAPI has discontinued its offering. — [unifically](https://unifically.com/blogs/midjourney-api); [apiframe](https://apiframe.ai/blog/best-midjourney-apis)
- V8.2 has been the default since 2026-07-24. Omni Reference (`--oref`, `--ow` 1–1000) works only on V7. On V8.x, `--edit` with up to 4 reference images replaces it. `--cref` (V6) is now a legacy feature. — [blakecrosley guide (third-party)](https://blakecrosley.com/guides/midjourney)

**Recraft**
- Recraft V4 Styles builds a custom style from 1–10 reference images (PNG/JPG/WEBP, at least 256px on the short edge). No training is needed. Generations then reuse the `style_id`. The Vector variants output native SVG, and Recraft says this is real paths, not traced bitmaps. The family shipped in August 2026. — [Recraft styles docs](https://www.recraft.ai/docs/api-reference/styles); [Runware V4 Styles guide](https://runware.ai/docs/models/recraft-v4-styles/guides/styles-from-references)
- Prices (third-party): V4.1 Vector $0.08/SVG, V4.1 Pro Vector $0.33, style creation $0.044, vectorize $0.011. Endpoint: `https://external.api.recraft.ai/v1/images/generations`. — [search summary of Recraft/third-party pages](https://tech-insider.org/how-to-use-recraft-ai-2026/)
- Recraft says its Precise style mode was preferred 91.6% of the time across 159 styles in a vendor-run blind test. Treat this as vendor marketing. — [Runware V4 Styles guide](https://runware.ai/docs/models/recraft-v4-styles/guides/styles-from-references)
- Recraft is a style system, not a character-identity system. I found no character-reference feature.

**Runway**
- `gen4_image` and `gen4_image_turbo` use `POST /v1/text_to_image`. `referenceImages` is required, with 1–3 images, and is designed for "consistent characters and locations". Prices: 5 credits (720p) or 8 credits (1080p), i.e. $0.05/$0.08. Turbo is 2 credits ($0.02). Credits cost $0.01. There is no per-reference surcharge on gen4_image. — [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/); [Runway Gen-4 Images API launch, May 2025](https://runway.com/news/introducing-runway-api-for-gen-4-images)
- Also on Replicate as `runwayml/gen4-image`. — [Replicate](https://replicate.com/runwayml/gen4-image)

**ByteDance Seedream 5.0**
- On fal, Seedream 5.0 Pro Edit (`bytedance/seedream/v5/pro/edit`) takes up to 10 references. It costs $0.0675 per output up to 1536², or $0.135 up to 2048², plus $0.0045 per extra input image. fal marks the price as tentative. It also supports "sketch completion". — [fal Seedream 5 Pro edit](https://fal.ai/models/bytedance/seedream/v5/pro/edit)
- Seedream 5.0 Lite Edit costs $0.035/image, takes 10 references (the last 10 are kept if you send more) and goes up to 9MP. — [fal Seedream 5 Lite edit](https://fal.ai/models/fal-ai/bytedance/seedream/v5/lite/edit)
- Direct BytePlus price for Pro: $0.045/image up to 2.36MP. The first reference is free, then $0.003 each. — [search summary citing BytePlus; third-party](https://www.therundown.ai/tools/seedream-5-0-pro)

**Alibaba Qwen Image Edit**
- fal endpoints and prices:
  - `fal-ai/qwen-image-edit-2511`: $0.03/MP
  - `fal-ai/qwen-image-edit-2509` (multi-image "Plus"): $0.03/MP
  - `fal-ai/qwen-image-2/edit`: $0.035/image
  - `qwen-image-max/edit`: $0.075
  - Qwen Image 3: $0.075

  — [fal qwen-image-2 edit](https://fal.ai/models/fal-ai/qwen-image-2/edit); [fal qwen-image-edit-2509](https://fal.ai/models/fal-ai/qwen-image-edit-2509); [pricepertoken (third-party)](https://pricepertoken.com/fal-ai-pricing)
- Plus/2509 is described as blending "2-3 reference images". That is third-party wording, not an official cap. — [evolink (third-party)](https://evolink.ai/blog/qwen-image-edit-plus-api-review-guide)
- Qwen-Image-Edit has open weights, so a LoRA endpoint is available on fal ($0.035/MP). That is one hosted route to fine-tuning a specific ink style. — [pricepertoken (third-party)](https://pricepertoken.com/fal-ai-pricing)

### Inferences
- For "one reference drawing → many panels", the documented character-plus-style slots make **Nano Banana Pro** (character + separate style slots) and **Ideogram 3.0** (character ref + style refs) the most purpose-fitting interfaces. Pass the same drawing as both character and style reference. **FLUX.2**, **Seedream 5.0** and **GPT Image 2.5** have no separate slots and do it by prompt referencing ("image 1").
- Recraft V4 Styles Vector is the only option here that returns native vector output. Vector output can be truly two-tone, with no anti-aliased grey pixels in the source. That makes it the strongest candidate for property (b), pure B/W, but it does nothing for identity.
- Cheapest viable loop: Nano Banana 2.1 at $0.0336/1K ($0.0168 batch) or Seedream 5.0 Lite at $0.035, so about 30 panels per dollar. Nano Banana Pro and gpt-image-2 high cost about 4–6× more.
- Plain Python with stdlib HTTP (`urllib.request` + `json` + `base64`). This is my reading of the documented request shapes; I tested none of them.
  - **Easy, JSON body:** Gemini (inline base64 parts), BFL (JSON + polling), Runway (JSON), fal (REST queue with a `Key` header), Recraft.
  - **Awkward, multipart/form-data:** Ideogram, and the OpenAI `/images/edits` endpoint. These need a hand-built multipart body, or `requests`.
  - **OpenAI alternative:** the Responses API accepts base64 data URLs in JSON.
  - **Not callable legitimately:** Midjourney.

### Gaps
- **Leonardo.ai character reference:** API caps, price and current model not researched (tool budget).
- **OpenAI:** `input_fidelity` and the reference-count maximum for gpt-image-2.5 are absent from the truncated guide text. Official per-image prices are only in OpenAI's calculator, not on the pricing page.
- **FLUX 3 Image** reference support is undocumented in what I fetched.
- **Content/likeness policies** for drawing a real, private person from a drawing:
  - Gemini: found only the generic "necessary rights" clause.
  - OpenAI, BFL, Ideogram, Runway, ByteDance: not retrieved.

  The likely risk is low for a stylised chibi drawing of a consenting person, but that is an inference, not a cited finding.
- The Gemini free-tier "Not available" reading comes from one fetch of the pricing page, summarised by a tool. Verify it in AI Studio before relying on it.

## Line-art fidelity: flat B/W preservation and failure modes (line art, animals)

### Takeaway
I found no published, controlled test of any model on pure black/white ink line-art consistency. The evidence is prompt folklore and general consistency tests (mostly photos and colour anime). Assume every raster model will add grey anti-aliasing and sometimes shading or colour. A post-generation threshold step is mandatory for "no grey", and the reference image should be re-sent on every call instead of chaining edits.

### Cited Findings
- No dedicated B/W line-art comparison across Nano Banana, GPT Image and FLUX was found. NightCafe claims (product page, not a test) that GPT Image gives "clean outlines" and Flux "strong contrast and bold inking". — [search synthesis, NightCafe line-art page](https://creator.nightcafe.studio/tools/line-art-generator)
- Widely shared Nano Banana prompts suppress grey explicitly. Examples: "no shading, no grayscale, and no color fill… pure white", "No shading. No cross-hatching… No greyscale. No solid black fills", and a background pinned to `#ffffff`. For shadows, one prompt asks for "strictly black-and-white ink with no grayscale, using dense screen-tone dot patterns". (Anecdotal; the need for these prompts shows that drift to grey is the default failure.) — [Awesome-Nano-Banana-images](https://github.com/PicoTrex/Awesome-Nano-Banana-images/blob/main/README_en.md); [YouTube coloring-page prompt](https://www.youtube.com/watch?v=oYnnqxIc89k); [glbgpt manga/comic guide](https://www.glbgpt.com/hub/how-to-add-color-to-comics-using-nano-banana-pro/)
- Iterative-edit drift on Nano Banana: one user reports that a second edit "always changed the tone… more saturate… sharpen too much". Another reviewer says quality "degrades over time (more prompts)". (Anecdotal.) — [Adobe community bug report](https://community.adobe.com/bug-reports-403/generate-from-nano-banana-for-the-2nd-time-always-changed-the-image-tone-1483534); [Erik Fadiman substack](https://erikfadiman.substack.com/p/nano-banana-everything-you-need-to)
- Fine detail retention: in PicLumen's style-transfer test, FLUX Kontext kept the character's hairstyle details while Nano Banana "altered them slightly". This matters for the bun and the tapered centre-parted fringe. (Vendor blog test, anecdotal.) — [PicLumen](https://www.piclumen.com/blog/flux-kontext-vs-nano-banana/)
- Sequential edits (2026 head-to-head, about late September): "GPT Image 2 — pixel-stable across 4 sequential edits. Nano Banana 2 — slight drift on iteration 3. FLUX 2 Pro — full re-render approach, not true instruction edit." (Single blog.) — [ropewalk.ai](https://ropewalk.ai/blog/gpt-image-2-vs-nano-banana-2-vs-imagen-4-vs-flux-2-2026)
- Reference likeness, photo headshot over 10 prompts: "for character consistency from a reference image, GPT wins this one by a mile" against Nano Banana 2. — [aiblewmymind substack](https://aiblewmymind.substack.com/p/nano-banana-2-vs-gpt-images-2)
- Contrary view: Morphed's 2026 scorecard gives Nano Banana Pro the win over FLUX 2 on character consistency from references, and rates stylized/illustration a tie. — [morphed.app](https://morphed.app/blog/flux-2-vs-nano-banana-pro)
- Anime-style test: Nano Banana was better on expression and consistency, and Flux Kontext "sometimes overcomplicates anime-style prompts". (This is relevant to chibi.) — [flash-image.art](https://flash-image.art/blog/nano-banana-vs-flux-kontext). Caution: several pro-Nano-Banana pages are resellers.
- OpenAI itself documents recurring-character consistency as a known limitation. — [OpenAI image-generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- Seedream 5.0 Pro advertises "sketch completion", a relevant line-art capability that has not been tested here. — [fal Seedream 5 Pro edit](https://fal.ai/models/bytedance/seedream/v5/pro/edit)

### Inferences
- Line weight and taper are the properties most likely to drift: models re-render, they do not copy strokes. Character identity in a chibi with closed eyes rests on a few cues (bun, fringe strands, lashes, the dog's scruff), so it may survive better than photo-likeness does. Fringe-strand count and dog scruff texture are the likely failure points.
- Animals: no source tested small-dog identity specifically. Expect scruffy-texture simplification and changes in breed or proportions. Including the dog's own crop as a separate reference (Nano Banana's character slots, FLUX.2's numbered refs) is the documented mechanism to try.
- Practical pipeline implied by the evidence:
  1. Send the original drawing on every call; never chain from a previous output.
  2. Use the explicit no-grey/no-shading prompt.
  3. Binarise the result with a hard threshold, e.g. PIL `point(lambda p: 255 if p>128 else 0)`.
  4. Optionally vectorise (Recraft vectorize at $0.011) for crisp tapered strokes.

### Gaps
- No controlled, dated benchmark of B/W ink fidelity (grey-pixel fraction, line-width variance) exists in what I found. That is a measurable test PoesIA could run itself with a single fixed reference across 4–5 models.
- No animal-specific consistency evidence for any model.

## Published comparisons and benchmarks of character consistency / image editing (dated)

### Takeaway
The only large-scale, dated benchmark is Arena (formerly LMArena) Image Edit (updated 2026-10-06, about 31M votes, 59 models). It is led by OpenAI's gpt-image-2.5 pair, followed by Grok Imagine 2.0, MAI-Image-2.6 and Nano Banana 2.1. It measures general edit preference, not character consistency or line art. A separate Multi-Image Edit board exists, but I could not read its rankings.

### Cited Findings
- Arena Single Image Edit top 10 (2026-10-06):
  1. gpt-image-2.5-sunburst 1524±5 (preliminary)
  2. gpt-image-2.5-flare 1481±5
  3. gpt-image-2 (medium) 1462
  4. grok-imagine-image-2.0 (canvas) 1439
  5. mai-image-2.6 1428
  6. gemini-nano-banana-2.1 1428±6
  7. grok-imagine-image-2.0 1425
  8. muse-image (Meta) 1403
  9. mai-image-2.5 1401
  10. seedream-5.0-pro 1394

  — [Arena image-edit leaderboard](https://arena.ai/leaderboard/image-edit)
- Further down that board: Nano Banana Pro 2K is 12th at 1390, Nano Banana 2 [web-search] 14th at 1387, gpt-image-1.5-high-fidelity 17th at 1370, qwen-image-2.1 18th at 1369, ideogram-4.5 20th at 1347, Nano Banana 2 Lite 24th at 1314. No FLUX model appears in the top 25. — [Arena image-edit leaderboard](https://arena.ai/leaderboard/image-edit)
- Arena added a separate Multi-Image Edit category (votes where several images were input). qwen-image-2.1 and MAI-Image-2.6 were added on 2026-09-22. — [Arena leaderboard changelog](https://news.lmarena.ai/leaderboard-changelog/)
- Conflicting aggregator: llm-stats (Oct 2026) ranks Gemini 3.1 Flash Image first on a different scale and omits GPT Image 2.5. It does not match Arena's own board. — [llm-stats](https://llm-stats.com/leaderboards/best-ai-for-image-editing)
- Practitioner tests (dates as published, all anecdotal):
  - ropewalk.ai, about 2026-09-29, sequential-edit stability: GPT Image 2 > Nano Banana 2 > FLUX 2 Pro. — [ropewalk.ai](https://ropewalk.ai/blog/gpt-image-2-vs-nano-banana-2-vs-imagen-4-vs-flux-2-2026)
  - aiblewmymind, 10-prompt reference test: GPT Image 2 beats Nano Banana 2. — [aiblewmymind](https://aiblewmymind.substack.com/p/nano-banana-2-vs-gpt-images-2)
  - Morphed: Nano Banana Pro beats FLUX 2 on references. — [morphed.app](https://morphed.app/blog/flux-2-vs-nano-banana-pro)
  - Melies: recommends Kontext Max for character sheets. — [melies.co](https://melies.co/compare/nano-banana-2-vs-flux-pro-kontext-max)

### Inferences
- Arena preference correlates with instruction-following and photo quality. It does not measure ink-style fidelity, so it should only shortlist candidates (GPT Image 2.5, Nano Banana 2.1/Pro, Seedream 5.0 Pro, Qwen 2.1, Ideogram 4.5). It cannot pick a winner for this use case.
- Practitioner tests lean towards GPT Image 2.x for identity stability and towards Nano Banana for stylised/anime work. The two leanings conflict, and n is small (single-author blogs, mostly photo references). A self-run test with the actual drawing is the only decisive evidence.

### Gaps
- Multi-Image Edit leaderboard rankings could not be read (only Single Image Edit content rendered).
- No academic character-consistency benchmark (e.g. a 2025–2026 paper) was retrieved within the tool budget.

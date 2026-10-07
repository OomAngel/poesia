# Vector and line-art routes for elegant black-ink character drawings (as of 2026-10-07)

Scope: whether an SVG/vector route can produce the same characters in new poses in thick black-ink, pure B/W chibi line art (tapered strokes, smooth curves, no grey), and which raster→vector and cleanup tools to use. Research date: 2026-10-07. Claims dated where the source allows; pre-2025 items flagged "possibly stale". Approx. 17 tool calls; vendor/third-party sources labelled.

## Q1. Image→SVG vectorizers: which give the smoothest curves on thick black ink, centerline vs outline, and how to get tapers

### Takeaway
For thick black-ink line art the strongest free/Python-callable option is still potrace (outline tracing, tunable smoothness via `alphamax`/`opttolerance`), with VTracer 1.0 (`--preset bw`, `--mode spline`, `--simplify`) as the MIT-licensed alternative; Vectorizer.AI is the commercial quality leader by user report and is cheap to test (free test-mode API). Tapered strokes come for free from **outline** tracing (the traced shape *is* the brush stroke with its taper); centerline tracing (autotrace) throws taper away because SVG has no native variable-width stroke.

### Cited Findings
**potrace**
- Latest version 1.16, released 2019-09-17 (bug fixes only) — still current as of 2026; GPL-2.0-or-later; a non-GPL "Potrace Professional" exists via Icosasoft for proprietary use. Possibly stale only in the sense of no new releases — [potrace homepage](https://potrace.sourceforge.net/)
- Key options and defaults: `-t/--turdsize` (speckle suppression, default 2), `-a/--alphamax` (corner threshold, default 1), `-O/--opttolerance` (curve optimization tolerance, default 0.2), `-n/--longcurve` (turns curve optimization off; optimization on by default), `-k/--blacklevel` default 0.5; input PBM/PGM/PPM/BMP; companion `mkbitmap` pre-processes greyscale/colour for tracing — [potrace homepage](https://potrace.sourceforge.net/)
- alphamax semantics (2003 paper, stable algorithm): alphamax = 0 → polygon output (no smoothing); alphamax > 4/3 → no corners at all, everywhere-smooth curve; default 1 — [Selinger, Potrace paper, 2003](https://potrace.sourceforge.net/potrace.pdf)
- Potrace finds a globally optimal polygon then fits Béziers, giving good results even on low-resolution input; its fitting is O(n²) and slows on very high-resolution images — [VTracer README](https://github.com/visioncortex/vtracer); [potrace paper](https://potrace.sourceforge.net/potrace.pdf)
- StarVector paper's benchmark (v4, 2023–2025): LIVE, VTracer and AutoTrace produce artifacts on small details; "Potrace offers more sharp results, but it is monochromatic" — [StarVector arXiv 2312.11556](https://arxiv.org/html/2312.11556v4)
- Python bindings: `pypotrace` 0.3 (2021-02-05, GPL, inactive, needs libpotrace-dev to build); `potracer` 0.0.4 (2022-01-26, pure-Python port of potrace 1.16, GPL-2.0+, numpy-only, ~500x slower than C, Python 3.6–3.9) — [pypotrace PyPI](https://pypi.org/project/pypotrace/); [potracer on libraries.io](https://libraries.io/pypi/potracer). Both possibly stale (no 2025–2026 releases found).

**VTracer (visioncortex)**
- MIT licence; current version 1.0.0-alpha.4 for desktop, Rust, Python (`pip install vtracer==1.0.0a4`, pyo3 native wheel) and npm; release date not stated on page (fetched 2026-10-07) — [vtracer GitHub](https://github.com/visioncortex/vtracer)
- Modes `pixel|polygon|spline`; `-f filter_speckle` 0–128; `--simplify <px tolerance>` (suggested 1–2.5) refits smooth runs with fewest cubics, "typically halving file size"; README says `--simplify` is "the knob that actually moves output size and smoothness"; corner/splice thresholds now hidden (defaults 60/45) — [vtracer GitHub](https://github.com/visioncortex/vtracer)
- B/W mode: `--preset bw` / `--clustering bw`, fixed `--threshold 0..255`, or `--adaptive` Bradley–Roth thresholding for uneven scans; Python `vtracer.Config(clustering="bw", adaptive=True)` — [vtracer GitHub](https://github.com/visioncortex/vtracer)
- VTracer "favours fidelity over simplification"; linear O(n) pipeline vs potrace's costly optimal-polygon search — [vtracer GitHub](https://github.com/visioncortex/vtracer); [VTracer docs](https://www.visioncortex.org/vtracer-docs/)

**autotrace (centerline)**
- `-centerline` flag traces an object's centerline instead of outline — [autotrace man page](https://linux.die.net/man/1/autotrace)
- Latest release 0.31.10 (ImageMagick 7 support, CVE fixes, Windows installers); release year not shown on page; repo active (153 commits ahead of release) — [autotrace releases](https://github.com/autotrace/autotrace/releases)
- Inkscape ≥1.0.1 includes Path → Trace Bitmap → "Centerline tracing (autotrace)"; the old fablabnbg plugin was archived 2025-01-03; known Windows crash on ~2000×2000 px images — [inkscape-centerline-trace](https://github.com/fablabnbg/inkscape-centerline-trace); [Inkscape issue 3997](https://gitlab.com/inkscape/inkscape/-/issues/3997)
- Python binding `pyautotrace` v0.0.8 exists (year not shown) — [pyautotrace release](https://github.com/lemonyte/pyautotrace/releases/tag/v0.0.8)
- Inkscape's built-in Trace Bitmap (potrace-based) traces edges only, yielding "double lines" for simple drawings — hence the centerline plugin — [inkscape-centerline-trace README](https://github.com/fablabnbg/inkscape-centerline-trace)

**Tapered strokes / SVG limitation**
- SVG has no native variable-width stroke; W3C ISSUE-2271 (2009) remained unresolved and was ruled out of SVG2 in 2013 minutes; the only way is to make the stroke a filled outline path (how Inkscape's Taper Stroke and Power Stroke LPEs work, storing (location, width) pairs and writing the filled outline to `d`) — [W3C ISSUE-2271](https://www.w3.org/Graphics/SVG/WG/track/issues/2271); [W3C minutes 2013-02-06](https://www.w3.org/2013/02/06-svg-minutes.html); [Engelen, Powerstroke LGM 2012 (possibly stale)](https://wiki.inkscape.org/wiki/images/e/e6/LGM2012_-_Powerstroke.pdf)
- Both Illustrator Image Trace and Vectorizer.AI output filled shapes, not strokes, by default — [svgvector.com Image Trace guide 2026 (third-party)](https://www.svgvector.com/blog/image-trace-illustrator-guide.html)

**Illustrator Image Trace**
- Presets Sketched Art, Silhouettes, Line Art, Technical Drawing produce B/W line-based output; B/W mode has a Threshold slider and "Ignore White" — [Adobe Image Trace help](https://helpx.adobe.com/illustrator/using/image-trace.html)
- Anecdotal: users on Adobe's feature-request forum say Image Trace never gets "straight lines and clean curves right" while Vectorizer.AI does in seconds — [Illustrator UserVoice](https://illustrator.uservoice.com/forums/333657-illustrator-desktop-feature-requests/suggestions/47531525-image-trace-like-vectorizer-ai-does) (anecdotal)
- Third-party: for single-colour high-contrast art "Image Trace + 10 minutes of cleanup produces a usable file"; AI vectorizers give "noticeably cleaner geometry" especially on photographic/blurry sources — [perfectvector.com (vendor blog, possibly biased)](https://perfectvector.com/blog/image-trace-vs-ai-vectorizer)

**Vectorizer.AI**
- API pricing (official page, 2026): monthly plans from 50 credits $9.99 ($0.20/image) to 100,000 credits $4,999.99 ($0.05/image); 1 credit = 1 image; credits roll over up to 5× monthly; web app (no API) $9.99/month unlimited — [Vectorizer.AI pricing](https://vectorizer.ai/pricing). Conflict: a third-party roundup lists "$9.99/mo (limited) or $19.99/mo unlimited" — [svgvector.com (third-party)](https://www.svgvector.com/blog/image-trace-illustrator-guide.html); euro pricing seen on other aggregators. Trust the official page.
- Test-mode API calls are free and need no subscription (watermarked results); response header `X-Credits-Calculated` shows production cost; outputs SVG/PDF/EPS/DXF/PNG — [Vectorizer.AI API docs](https://vectorizer.ai/api/documentation)

**Recraft vectorize**
- Recraft API: Vectorize converts PNG/JPG to SVG for $0.01 — [Recraft API docs](https://www.recraft.ai/docs); also hosted on fal.ai at $0.01/image — [fal recraft/vectorize](https://fal.ai/models/fal-ai/recraft/vectorize)
- The $0.01 vectorize price came from a March 2025 price cut — [Recraft on X, 2025](https://x.com/recraftai/status/1902768444325384468). A third-party guide says Recraft moved to credit-based pricing in Sept 2026 ($0.011 / 11 units) — [tech-insider.org (third-party)](https://tech-insider.org/how-to-use-recraft-ai-2026/); unverified against official page.

### Inferences
- For *thick* ink with tapers, outline tracing is the right mode: the taper is a property of the filled shape and survives tracing. Centerline tracing is the wrong tool for this style (it would need a width-per-point model re-added, i.e. Power Stroke-like reconstruction).
- Smoothness in potrace is mostly governed by input resolution (trace at 2–4× the target size after binarizing) plus `alphamax` ~1.0–1.3 and `opttolerance` 0.2–0.5; raising alphamax toward 4/3 removes corners, which may soften intentional sharp points (eye corners, hair tips). This is a tuning judgement, not a measured result.
- Licence fork: potrace/pypotrace/potracer are GPL — fine for personal pipelines and running the CLI as a subprocess, a constraint only if the user distributes a combined program. VTracer is MIT.
- No published, controlled head-to-head of potrace vs VTracer vs Vectorizer.AI vs Recraft on thick black ink character art was found; ranking among them is by mechanism plus anecdote. Cheapest decisive check: run the same 3–5 reference drawings through all four (Vectorizer.AI test mode and Recraft at $0.01 make this nearly free).

### Gaps
- No independent quantitative benchmark of commercial vectorizers on line art (only vendor blogs and forum anecdotes).
- Recraft's current (post Sept-2026, if real) official per-call price not confirmed on the official docs page.
- VTracer 1.0.0-alpha.4 release date not stated; autotrace 0.31.10 and pyautotrace v0.0.8 release years not shown.

## Q2. Generative SVG models: quality for character drawings and reference-image consistency

### Takeaway
OmniSVG (NeurIPS 2025; 1.1 weights 2025-12-02) is the only open model found that targets anime characters and has an explicit "character-reference" task, but it needs 17–26 GB VRAM and its outputs are flat-colour icon/illustration style, not tapered ink — it cannot run on a 2 GB GPU. StarVector is icon-grade and fails on complex characters. Recraft V4/V4.1 vector generation (API, from ~$0.035–0.08/image) with V4 Styles (1–10 reference images for style) is the practical hosted route, but style references are not the same as character identity consistency.

### Cited Findings
- OmniSVG: built on Qwen2.5-VL; text-to-SVG, image-to-SVG and character-reference SVG generation; "from simple icons to intricate anime characters"; up to 30k tokens — [OmniSVG GitHub](https://github.com/OmniSVG/OmniSVG); [arXiv 2504.06263, Apr 2025](https://arxiv.org/html/2504.06263v1)
- Character-reference task: generates a new SVG that keeps the input character's profile (not a reconstruction); scored ~7/10 average judged by GPT-4o (self-reported, LLM-judge, possibly circular) — [OmniSVG paper NeurIPS 2025](https://papers.nips.cc/paper_files/paper/2025/file/a510f05a574d4203ef3952973672fe2f-Paper-Conference.pdf)
- OmniSVG image-to-SVG (authors' own benchmark): OmniSVG-4B DINO 0.993 / SSIM 0.950 / LPIPS 0.050 vs StarVector-8B 0.895 / 0.881 / 0.231; paper states StarVector "fails on illustrations and more complex character images" — [OmniSVG NeurIPS paper](https://papers.nips.cc/paper_files/paper/2025/file/a510f05a574d4203ef3952973672fe2f-Paper-Conference.pdf)
- OmniSVG releases: 3B legacy 2025-07-22; OmniSVG1.1_4B and _8B 2025-12-02; training code 2025-12-31; code Apache-2.0, MMSVG dataset CC BY-NC-SA 4.0; GPU memory 17 GB (3B/4B) and 26 GB (8B); ~18–40 s for 1–2k tokens; hosted Gradio demo on HF Spaces; community ComfyUI node; no hosted API — [OmniSVG GitHub](https://github.com/OmniSVG/OmniSVG)
- StarVector (CVPR 2025): Apache-2.0; 1B (5.15 GB) and 8B (15 GB) im2svg checkpoints updated 2025-03-19; VRAM requirements only third-party and conflicting (8 GB min for 1B; 16–24 GB+ for 8B); Replicate hosts 8B on L40S — [StarVector HF collection](https://huggingface.co/collections/starvector/starvector-models); [star-vector GitHub](https://github.com/joanrod/star-vector); [DeepWiki GPU page (third-party)](https://deepwiki.com/joanrod/star-vector/2.2-gpu-support-and-resource-management); [Replicate](https://replicate.com/gregpriday/starvector-8b-im2svg)
- InternSVG (ICLR 2026): unified MLLM for SVG understanding/editing/generation incl. long-sequence illustrations — [arXiv 2510.11341](https://arxiv.org/pdf/2510.11341)
- Chat2SVG (CVPR 2025): LLM writes a template from primitives, then SDXL+ControlNet and SAM drive latent and point optimization (needs GPU) — [arXiv 2411.16602](https://arxiv.org/abs/2411.16602); [Chat2SVG GitHub](https://github.com/kingnobro/Chat2SVG). IntroSVG (2026) criticises such optimization pipelines as compute-heavy with "disorganized and difficult to edit" SVG — [IntroSVG arXiv 2603.09312](https://arxiv.org/html/2603.09312)
- SVGDreamer (v7 updated April 2026) — text-guided diffusion-optimized SVG (GPU-based) — [arXiv 2312.16476v7](https://arxiv.org/html/2312.16476v7). VectorFusion, LLM4SVG not individually researched here (see Gaps).
- Other 2026 SVG papers are not character-focused: VFIG (figures, Mar 2026), VecGlypher (font glyphs, Feb 2026), GeoSVG-RL (diagrams), GVR-Coder (documents) — [VFIG](https://arxiv.org/abs/2603.24575); [VecGlypher](https://arxiv.org/pdf/2602.21461); [GeoSVG-RL](https://arxiv.org/pdf/2605.25447); [GVR-Coder](https://arxiv.org/pdf/2607.28073)
- Recraft API vector models: V4.1 (raster+vector, from $0.035, default, model id `recraftv4_1_vector` in example), V4 ("production-grade vectors", from $0.04), V4 Styles ("match any style from 1 to 10 reference images", from $0.035), V2 (cheapest vector, from $0.022); saved Styles reusable across requests — [Recraft API docs](https://www.recraft.ai/docs). Third-party: V4.1 Pro Vector ~$0.33 — [tech-insider.org (third-party)](https://tech-insider.org/how-to-use-recraft-ai-2026/). Earlier V3 pricing $0.08 per vector image (Nov 2024, possibly stale) — [Recraft on X](https://x.com/recraftai/status/1861131720008900753)

### Inferences
- None of the generative SVG models found demonstrates *character identity* consistency across new poses in a tapered-ink style; OmniSVG's character-reference is the closest and is LLM-judged on its own benchmark, with training data in a flat-fill vector-clipart style. Treat as unproven for this use.
- With a 2 GB GPU, every open generative SVG model is out locally (OmniSVG ≥17 GB, StarVector-1B ~8 GB third-party estimate); only hosted demos/APIs (HF Space, Replicate, Recraft) are usable.
- Generating raster with a character-consistent image model and then vectorizing is likely higher quality than direct SVG generation, because vectorizers on clean B/W input are near-lossless while SVG generators still degrade on complex shapes (see Q4).

### Gaps
- Did not individually verify VectorFusion, LLM4SVG, SVGen, Reason-SVG status/quality in 2025–2026.
- No found evidence of Recraft vector outputs in a thick tapered-ink line style, nor whether Recraft can hold a specific character across poses (style refs ≠ identity).
- No independent (non-author) evaluation of OmniSVG character-reference quality.

## Q3. Line-art cleanup / inking tools and Python pipelines

### Takeaway
Neural extractors (AniLines 2025, Anime2Sketch, ControlNet lineart-anime preprocessor) and Krita's Fast Sketch Cleanup (Feb 2025, Sketchy→Ink models) turn rough or coloured raster into clean lines; but for a raster already drawn in pure B/W ink, a classical OpenCV/scikit-image chain (upscale → Otsu/fixed threshold → morphological open/close → remove small components → optional Gaussian blur + re-threshold to smooth edges) before potrace is usually enough and needs no GPU.

### Cited Findings
- AniLines (repo from 2025-02-10; Gradio/HF demo 2025-02-19; HF space back 2025-09-18): extracts lineart from anime images/video; basic vs detail model; claims more detail and fewer artifacts than MangaLineExtraction and Anime2Sketch (self-reported) — [AniLines GitHub](https://github.com/zhenglinpan/AniLines-Anime-Lineart-Extractor)
- Anime2Sketch (2021, MIT, possibly stale): sketch extractor for illustration/anime/manga; can turn photos of hand drawings into clean lineart and simplify freehand sketches — [Anime2Sketch GitHub](https://github.com/Mukosame/Anime2Sketch)
- Krita Fast Sketch Cleanup plugin new version (Feb 2025): neural filter; recommended workflow SketchyModel.xml at scale ≤1.0, then InkModel.xml to "make crisp lines" — [Krita blog 2025](https://krita.org/en/posts/2025/fsc-plugin-new-version/)
- ComfyUI controlnet_aux Anime Lineart preprocessor (last updated 2025-03-11); the paired ControlNet LineArt-Anime model is NonCommercial — [RunComfy node page (third-party)](https://www.runcomfy.com/comfyui-nodes/comfyui_controlnet_aux/AnimeLineArtPreprocessor)
- VTracer has built-in adaptive Bradley–Roth thresholding and speckle filtering, covering part of the cleanup chain — [vtracer GitHub](https://github.com/visioncortex/vtracer); potrace's `turdsize` removes speckles and `mkbitmap` does highpass+scale+threshold pre-processing — [potrace homepage](https://potrace.sourceforge.net/)
- Wolthera's comparison of editable inking strokes across Inkscape, Krita, Blender Grease Pencil, Synfig (2021, possibly stale) — [wolthera.info](https://wolthera.info/2021/10/study-of-editable-strokes-for-inking/)

### Inferences
- Stroke-width normalisation for "thick ink" can be done in raster before tracing: binarize, then morphological dilation (thicken) or erosion (thin) with an elliptical kernel; for uniform weight, skeletonize then re-dilate — but uniform re-dilation destroys tapers, so only normalise if tapers are not wanted. (Standard morphology; no specific source fetched.)
- Edge smoothing trick: Gaussian-blur the binary image (sigma ~1–2 px at 2–4× scale) and re-threshold at 0.5 before potrace — this rounds pixel stair-steps so the tracer fits fewer, longer curves. potrace's own `mkbitmap` performs a related scale+threshold step.
- Neural extractors matter only if the upstream raster model produces grey shading, colour, or sketchy doubled lines; for already-clean ink, they add risk (line drift) without benefit.
- GPU: Anime2Sketch/AniLines are small CNNs that plausibly run on CPU (slow) or 2 GB GPU; not verified.

### Gaps
- No fetched source for exact OpenCV/scikit-image licence versions or CPU runtimes of AniLines/Anime2Sketch.
- No found 2025–2026 dedicated "ink-ification" model producing tapered strokes from uniform lines, other than Krita's InkModel.

## Q4. Can an LLM produce good SVG if constrained differently? Benchmark evidence 2025–2026

### Takeaway
Benchmarks confirm the user's experience: frontier LLMs (Claude led) understand SVG well but are weak at structural synthesis, and quality drops ~40–60% relative from simple to complex SVGs. The published mitigations are (a) restricting the LLM to primitives and short paths then refining by optimization (Chat2SVG), (b) render-and-critique loops (Chat2SVG visual rectification, IntroSVG), and (c) RL fine-tuning — none show elegant hand-quality character linework. Using the LLM to *edit/compose* a vectorized trace (structure, IDs, pose-level transforms) rather than draw curves is the better-supported role.

### Cited Findings
- SVGenius (arXiv 2506.03139, June 2025): 2,377 queries, 22 models, understanding/editing/generation; top models "achieve 70-80% semantic understanding but struggle with structural synthesis (PSS scores rarely exceed 20)" — [SVGenius](https://arxiv.org/html/2506.03139v1)
- SVGenius image-to-SVG: Claude-3.7-Sonnet led every metric at all levels (Easy SSIM 54.02, DINO 89.91, PSS 23.70; Hard PSS 15.47); GPT-4o PSS 23.43→11.67, Gemini 19.80→7.30 Easy→Hard; Easy SVGs average 2.14 paths/133 control points vs Hard 16.02 paths/1,149 points; SVG-specialised LLM4SVG fell to PSS 0.02 on hard — [SVGenius](https://arxiv.org/html/2506.03139v1). Note: the paper's text calls the decline "5–10%" but its table shows ~6–9 absolute points (~40–60% relative); the paper's text also credits GPT-4o with leading multimodal generation although Claude's table value is higher — internal inconsistency in the source.
- SVGenius: "reasoning-enhanced training proves more effective than pure scaling" (e.g. DeepSeek-R1 beat Qwen2.5-72B on text-to-SVG); reasoning models still degrade at the same rate with complexity — [SVGenius](https://arxiv.org/html/2506.03139v1)
- Even SVGenius "Hard" (~16 paths) is far simpler than a character drawing; a potrace trace of a character typically has hundreds of path segments — inference, but consistent with the benchmark's complexity scale — [SVGenius](https://arxiv.org/html/2506.03139v1)
- SGP-GenBench ("Symbolic Graphics Programming with LLMs", 2025-09-05): closed models reach 80–90% on compositional metrics; open Qwen-2.5-7B baseline as low as 8.8; RL improves open models — [emergentmind summary (aggregator)](https://www.emergentmind.com/topics/sgp-genbench)
- VGBench (arXiv 2407.10972, 2024, possibly stale) and SGP-Bench (2024, possibly stale) are earlier understanding/generation benchmarks; InternSVG lists sizes SGP-Bench 4.3k, VGBench 10.1k, SVGenius 2.3k queries — [InternSVG arXiv 2510.11341](https://arxiv.org/pdf/2510.11341)
- Chat2SVG constrains the LLM to "rectangles, ellipses, lines, polylines, polygons, and short paths" on a 512×512 canvas "since the LLM has limitations in synthesizing geometrically complex paths", adds render→VLM critique (two iterations usually suffice), then diffusion-guided point optimization — [Chat2SVG CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Wu_Chat2SVG_Vector_Graphics_Generation_with_Large_Language_Models_and_Image_CVPR_2025_paper.pdf)
- IntroSVG (2026) uses rendering feedback in a generator–critic loop for text-to-SVG — [IntroSVG arXiv 2603.09312](https://arxiv.org/html/2603.09312)
- VectorGym (ServiceNow) evaluation "reveals significant performance gaps" in frontier VLMs on vector tasks — via [SVGenius/related search summary; primary not fetched](https://arxiv.org/pdf/2510.11341)

### Inferences
- The wobbly-curve failure is expected: coordinate-tracing many control points is exactly the "structural synthesis" weakness benchmarks measure. Few-control-point Béziers or primitives (Chat2SVG style) give smoother but more geometric, less "inked" shapes — good for chibi heads/bodies built from ellipses, poor for brush taper.
- Better LLM roles in this pipeline: (1) pose/layout planning; (2) editing a vectorized trace — grouping/naming parts, swapping an expression part, applying affine transforms to limb groups; (3) authoring a centerline skeleton of a few smooth Béziers, then programmatically giving it a tapered width profile (Power-Stroke-style outline offset) rather than drawing outlines by hand. (3) is untested by any source found.
- A render-and-critique loop (LLM sees its own rasterized output) is the cheapest improvement if hand-authored SVG continues; both Chat2SVG and IntroSVG rely on it.

### Gaps
- No benchmark specifically measures curve *elegance*/smoothness (PSS, SSIM, DINO measure fidelity/structure, not aesthetic line quality).
- No published evidence on LLM + programmatic taper-stroke generation for character art.
- Claude versions newer than 3.7 Sonnet not covered by SVGenius; no 2026 leaderboard for current frontier models found.

## Q5. Recommended pipeline (raster → binarize → vectorize → clean SVG), Python-callable, with licences

### Takeaway
Viable and GPU-free: generate the pose as raster with a character-consistent image model → (optional neural line extraction if output isn't clean B/W) → OpenCV/scikit-image binarize + morphology + smooth at 2–4× → potrace (GPL CLI or pypotrace) or VTracer (MIT, `pip install vtracer`) in outline mode → optional SVG optimisation. The vector route's quality ceiling is set by the raster generator; vectorization itself is the solved part. Use Vectorizer.AI ($0.05–0.20/image, free test mode) or Recraft ($0.01) as a quality benchmark/fallback.

### Cited Findings
- VTracer Python API: `vtracer.convert_file(...)`, `convert_bytes(...)`, `Config(clustering="bw", adaptive=True)`; MIT — [vtracer GitHub](https://github.com/visioncortex/vtracer)
- potrace CLI GPL-2.0+; pypotrace GPL (inactive, 2021); potracer GPL-2.0+ pure Python (2022, ~500x slower) — [potrace](https://potrace.sourceforge.net/); [pypotrace](https://pypi.org/project/pypotrace/); [potracer](https://libraries.io/pypi/potracer)
- autotrace centerline available via CLI and pyautotrace (only if single-line strokes are wanted, which loses taper) — [autotrace man page](https://linux.die.net/man/1/autotrace); [pyautotrace](https://github.com/lemonyte/pyautotrace/releases/tag/v0.0.8)
- Vectorizer.AI REST API (free test mode, paid production) and Recraft vectorize API ($0.01) — [Vectorizer.AI API docs](https://vectorizer.ai/api/documentation); [Recraft API docs](https://www.recraft.ai/docs)
- Anime2Sketch MIT; ControlNet LineArt-Anime NonCommercial; OmniSVG code Apache-2.0 but data CC BY-NC-SA; StarVector Apache-2.0 — [Anime2Sketch](https://github.com/Mukosame/Anime2Sketch); [RunComfy](https://www.runcomfy.com/comfyui-nodes/comfyui_controlnet_aux/AnimeLineArtPreprocessor); [OmniSVG](https://github.com/OmniSVG/OmniSVG); [StarVector HF](https://huggingface.co/starvector/starvector-1b-im2svg/tree/main)

### Inferences
- Concrete default recipe (untested here; parameters are starting points):
  1. Raster from upstream model at ≥1024 px; convert to grey.
  2. Upscale 2–4× (Lanczos), Otsu or fixed threshold; `morphologyEx` close then open with small elliptical kernel; drop connected components below N px; Gaussian blur σ≈1.5 and re-threshold at 128 to round jaggies.
  3. Trace: `potrace -s --alphamax 1.0–1.2 --opttolerance 0.2–0.4 --turdsize 10–50` on the PBM; or `vtracer --preset bw --mode spline --simplify 1.5 --filter_speckle 8`.
  4. Scale viewBox back to target size; fill `#000`, no stroke → pure B/W, tapers preserved.
  5. Optional: let an LLM restructure (group/ID parts) but not redraw curves.
- Verdict on viability: the vector route is viable for *output format and cleanliness* (crisp, no grey, smooth curves) but does not by itself solve *character consistency in new poses* — that is a raster-generation problem. Direct SVG generation (LLM or OmniSVG/StarVector/Recraft) is not, as of 2026-10-07, evidenced to deliver elegant tapered ink character art with identity consistency.
- Falsifier for this recommendation: if a side-by-side on the user's actual references shows potrace/VTracer curves visibly wobblier than Vectorizer.AI after the smoothing step, switch the trace stage to Vectorizer.AI API.

### Gaps
- No end-to-end run on the user's own reference images was performed; parameter values are informed starting points, not measured optima.
- Did not verify an SVG optimiser (e.g. svgo/scour) licence or effect on curve quality.

# Open-weight routes for character- and style-consistent ink illustration from a single reference drawing (as of 2026-10-07)

Scope: one thick black-ink, pure B/W chibi line-art drawing of a woman (hair bun, centre-parted tapering fringe, closed eyes with lashes) and her scruffy small dog. Goal: many new comic panels of the same two characters in the same ink style. The local GPU is 2 GB (Quadro M1000M), so everything runs remotely.

Dating convention: each finding carries the date of the source or the release it describes. Items from before 2025 are flagged **[pre-2025, possibly stale]**. Third-party pricing aggregators are labelled as such. Practitioner and community claims are labelled **[anecdotal]**.

---

## 1. LoRA training from ONE image: viability, dataset bootstrapping, base models, tools, cost

### Takeaway
A LoRA trained directly on one image (plus crops and flips) is viable but overfits hard. It tends to reproduce the training composition and leak the background or position. As of 2025-2026 the established practice is to bootstrap a synthetic set of about 20-60 images with an open edit model (FLUX.1 Kontext dev, Qwen-Image-Edit-2509/2511, FLUX.2), hand-curate it to about 15-30 images, and train on that. A second pass on outputs from the first LoRA is common. For an Apache-licensed, cheap-to-train base, FLUX.2 [klein] 4B (Apache 2.0) and Qwen-Image / Qwen-Image-Edit (Apache 2.0) are the strongest current candidates. The SDXL anime family (Illustrious, NoobAI) remains the most mature ecosystem for line-art LoRAs and ControlNets.

### Cited Findings

**Single-image training (direct)**
- [anecdotal, Civitai] The "Single Image LoRA Part 2" kohya_ss workflow recommends upscaling the single image to 2k or more so crops keep detail, then manually inspecting it for upscaler artifacts, which a LoRA can learn as style. Without proper captioning the LoRA "tends to be very overfit and will only produce the same image from the dataset". At 100 repeats it was overtrained by the third epoch. Overfitting without the head can be partly offset by lowering LoRA weight at inference. — [Civitai: Single Image LoRa Part 2](https://civitai.com/articles/1058/single-image-lora-part-2) (article date not confirmed; likely 2023 **[pre-2025, possibly stale]**)
- [anecdotal, Civitai] "Copita" trains an SDXL/Anima *style* LoRA from a single image differently. It creates a matched comparison image and extracts the *difference* as a LoRA, which works like a concept slider (e.g. a "Bold" line-weight LoRA when only line weight differs). Its stated limit: it is poor at concepts that cannot be expressed as a clean two-image difference. It also recommends a bust-up, near-frontal reference with simple clothing and background. — [Civitai: Copita](https://civitai.com/articles/33356/copita-train-an-anima-sdxl-style-lora-from-a-single-image) (date not stated in snippet; article ID suggests 2026)
- Research: T-LoRA (arXiv 2507.05964, Jul 2025) targets single-image customisation. It shows that higher diffusion timesteps overfit more and proposes timestep-sensitive fine-tuning. It also notes that background elements and positional biases from the training image "leak" into generations. — [arXiv 2507.05964](https://arxiv.org/abs/2507.05964v1)
- Overfitting mitigation [anecdotal]: low LR (about 1e-4), modest rank (one cheatsheet suggests dim 32 / alpha 16 for small style sets), 200-500 regularisation images from the base model, inference strength 0.5-0.6, and flip augmentation. Crops or tiny edits "don't create meaningful diversity". A fixed prompt/seed checkpoint grid is the recommended way to pick an early checkpoint. — [Civitai Pro Tips Cheatsheet](https://civitai.com/articles/12229/pro-tips-cheatsheet-lora-training); [Krea: Train a Custom Style](https://www.krea.ai/docs/developers/tutorials/train-image-style); [HF forum notes on one-image Qwen-Image-Edit training](https://huggingface.co/datasets/John6666/forum2/blob/main/qwen_image_edit_one_image_train_1.md)
- [anecdotal] Several guides advise against training on B/W images "unless you want the LoRA to output black and white images". For this use case that is the desired behaviour. — [Civitai Pro Tips Cheatsheet](https://civitai.com/articles/12229/pro-tips-cheatsheet-lora-training)

**Bootstrapping a dataset with an edit model (the 2025-2026 standard practice)**
- The Floyo "Flux Kontext – Single Image to Character LoRA" workflow runs one image through 60 prompts (pose, environment, expression, camera angle) with FLUX.1 Kontext dev at 1024×1024. The user then curates the output, since "some outputs will be poor". It cites about 30 images as the ideal minimum for a FLUX character LoRA and says multi-angle character sheets work best as input. — [Floyo workflow](https://www.floyo.ai/workflows/flux-kontext-single-image-to-charact-u1fosxceuqr5) (2025)
- Open-source ComfyUI workflow `lovisdotio/workflow-comfyui-single-image-to-lora-flux`: Gemini writes 20 prompts, FLUX.1 Kontext generates 20 variations with captions saved, and FLUX.1-dev LoRA training is integrated in ComfyUI. It requires a Gemini API key. — [GitHub](https://github.com/lovisdotio/workflow-comfyui-single-image-to-lora-flux) (2025)
- WeirdWonderfulAI (Jul 2025) argues that Kontext keeps the subject consistent "almost flawlessly" across styles, environments and orientations, and publishes a 50-prompt list. A later post makes the same case for Qwen-Image-Edit. — [Flux Kontext can create LoRA Dataset](https://weirdwonderfulai.art/comfyui/flux-kontext-can-create-lora-dataset/); [Qwen Image Edit can create Character Consistent LoRA Dataset](https://weirdwonderfulai.art/comfyui/qwen-image-edit-can-create-character-consistent-lora-dataset/) [anecdotal]
- HF forum notes call "generate many synthetic variations with a strong generative model (Qwen-Image/Qwen-Image-Edit + ControlNet), then train a second LoRA on the best of them" the most powerful approach. — [HF forum notes](https://huggingface.co/datasets/John6666/forum2/blob/main/qwen_image_edit_one_image_train_1.md) [anecdotal]
- Nano Banana (Gemini 2.5 Flash Image) is closed-weight. At the Qwen-Image-Edit-2509 launch (Oct 2025), Artificial Analysis ranked Qwen-Image-Edit-2509 the leading open-weights editor and #3 overall, trailing only Nano Banana and one other model. Nano Banana is therefore a plausible closed *dataset-generation* step feeding an open LoRA. — [Artificial Analysis on X](https://x.com/ArtificialAnlys/status/1975993986314813889)

**Character LoRA vs style LoRA**
- BFL's FLUX.2 [klein] guidance separates the two: 1500-2500 steps for style LoRAs and 1500-3000 for character LoRAs, LR 8e-5 to 1e-4, and 15-40 images "that share one look". BFL publishes a dedicated *style* training example (ai-toolkit, rank 32 / alpha 32). — [HF blog: Fine-tune FLUX.2 klein under 60 min](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora); [BFL klein style training](https://docs.bfl.ai/flux_2/flux2_klein_training_example) (2026)
- [anecdotal] For a style LoRA, "prioritise visual treatment across different subjects, not a single signature composition". This implies the style set should contain *other* subjects in the same ink, while the character set should contain the *same* characters in varied poses. — [HF forum notes](https://huggingface.co/datasets/John6666/forum2/blob/main/qwen_image_edit_one_image_train_1.md)

**Base models for flat B/W line art (2025-2026)**
- **FLUX.2 [dev]**: 32B, released 25 Nov 2025 under the FLUX Non-Commercial License. Supports up to 10 reference images natively (one third-party site says 4; BFL and Replicate say 10). BFL claims it leads open-weight models in T2I and single- and multi-reference editing. FP8 is said to fit 18-24 GB. Commercial use needs a BFL licence, but Replicate says commercial use through its platform is permitted. — [BFL blog: FLUX.2](https://bfl.ai/blog/flux-2); [HF model card](https://huggingface.co/black-forest-labs/FLUX.2-dev); [Replicate](https://replicate.com/black-forest-labs/flux-2-dev); conflicting count: [aifilms.ai](https://studio.aifilms.ai/blog/flux-2-production-image-generation)
- **FLUX.2 [klein]**: 4B and 9B, each with a distilled (4-step) and a base variant. **4B is Apache 2.0**, 9B is non-commercial. 4B weights are about 13 GB in bf16 and a LoRA run fits under 24 GB (4090/L4). An 1800-step run on a 4090 takes under an hour. Train on Base and load on the distilled model. ai-toolkit and Diffusers are the officially recommended trainers. — [BFL klein blog](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence); [HF blog](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora); [BFL help](https://help.bfl.ai/articles/7108141705-can-i-run-or-fine-tune-flux-2-klein-locally) (released early 2026, about 259 days before the search date per the search index)
- **Qwen-Image / Qwen-Image-Edit-2509 / 2511**: 20B. Every Qwen image model through Dec 2025 (Qwen-Image, Edit, 2509, 2511, 2512, Layered) has Apache 2.0 weights. 2509 (Sep 2025) added 1-3-image multi-reference and native ControlNet inputs (depth, edge, keypoint, sketch). 2511 (23 Dec 2025) improved multi-person consistency. FP8 editing needs about 16 GB. **Qwen Image 2.0 is API-only (no open weights).** — [QwenLM/Qwen-Image GitHub](https://github.com/QwenLM/Qwen-Image); [HF model card 2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509/blob/main/README.md); [invideo explainer, Aug 2026](https://invideo.io/blog/qwen-image-ai-generator/); [Qubrid on Qwen Image 2.0](https://qubrid.com/blog/qwen-image-2-0-qwen-image-edit-2-0-explained-architecture-benchmarks-api-on-qubrid-ai)
- **FLUX.1 Kontext [dev]**: open weights released around 26 Jun 2025 under the FLUX.1 [dev] Non-Commercial License. The licence v1.1 removed the line saying outputs could be used commercially, and BFL said it reverted those sections to match FLUX.1 [dev] NCL. Commercial self-hosting needs a paid BFL licence. — [HF model card](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev); [HF licence discussion #6](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/discussions/6); [BFL announcement](https://bfl.ai/announcements/flux-1-kontext-dev)
- **SDXL anime family (Illustrious / NoobAI / Pony)**: marketing pages describe Illustrious as fine-tuned for "line art precision" (vendor claim, not an independent test). The ControlNet and IP-Adapter ecosystem for these models is the most mature (see section 3). — [dreamfaceapp on Illustrious](https://www.dreamfaceapp.com/blog/illustrious-sdxl-ai) [vendor claim]
- HiDream, Chroma, Z-Image, Lumina2 and OmniGen2 are all supported by ai-toolkit for LoRA training. — [AI-Toolkit guide (localaimaster)](https://localaimaster.com/blog/ai-toolkit-lora-training-guide)

**Training tools**
- **ostris/ai-toolkit** (MIT) supports FLUX.1 (dev, schnell, Kontext), FLUX.2, Chroma, Lumina2, Qwen-Image, Qwen-Image-Edit, HiDream, OmniGen2 and Z-Image. 24 GB covers most configs, and Qwen-Image-Edit targets 32 GB. Ostris showed a Qwen-Image-Edit-2509 LoRA trained with peak VRAM under 10 GB (Oct 2025). — [localaimaster guide](https://localaimaster.com/blog/ai-toolkit-lora-training-guide); [Ostris on X](https://x.com/ostrisai/status/1979250513209364641)
- Edit-model LoRAs (Kontext, Qwen-Image-Edit) are trained on *paired* before/after data. RunComfy guides cover 2509 and 2511 edit-dataset design and the 2511-specific `zero_cond_t` setting. — [RunComfy: Qwen-Image-Edit-2511 LoRA training](https://www.runcomfy.com/trainer/ai-toolkit/qwen-image-edit-2511-lora-training); [RunComfy: 2509](https://www.runcomfy.com/trainer/ai-toolkit/qwen-image-edit-2509-lora-training)
- In-Context LoRA (arXiv 2410.23775, Oct 2024 **[pre-2025, possibly stale]**) on FLUX.1-dev was trained on 1×A100 for 5,000 steps, batch 4, rank 16. — [arXiv 2410.23775](https://arxiv.org/pdf/2410.23775)
- kohya_ss/sd-scripts remains the reference for SDXL/Illustrious workflows in Civitai guides. — [Civitai complete LoRA tutorial](https://civitai.com/articles/21114/complete-lora-training-tutorial-civitai-kohya-runpod-and-colab-explained-step-by-step) [anecdotal]
- Civitai's hosted trainer runs ai-toolkit under the hood for FLUX.2 klein: 500 Buzz for 4B base, 1000 Buzz for 9B base. — [Civitai developer docs](https://developer.civitai.com/orchestration/recipes/training-flux2-klein)

**Typical cost/time per LoRA (hosted trainers)**
- fal `flux-lora-fast-training`: "$2 per training run (scales linearly with steps)". The indexed page is about 15 months old, so verify the live price. — [fal](https://fal.ai/models/fal-ai/flux-lora-fast-training)
- fal `flux-kontext-trainer`: $2.50 per 1000 steps, with a 500-step minimum ($1.25). — [fal Kontext trainer](https://fal.ai/models/fal-ai/flux-kontext-trainer)
- fal `qwen-image-edit-2509-trainer`: $4.00 per 1000 steps, with a 100-step minimum ($0.40). — [fal Qwen Edit trainer](https://fal.ai/models/fal-ai/qwen-image-edit-2509-trainer)
- fal also lists a FLUX.2 [dev] edit trainer. — [fal FLUX.2 edit trainer](https://fal.ai/models/fal-ai/flux-2-trainer/edit)
- Self-run: FLUX.2 klein 4B, 1800 steps, under 1 h on a 4090 → about $0.30-0.50 at Vast.ai 4090 rates (see section 5). — [HF blog](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora)

### Inferences
- For this drawing, the most likely-to-work path is: (1) clean and upscale the original to pure B/W at about 2k; (2) generate 40-60 variants with Qwen-Image-Edit-2511 or FLUX.2 [dev] or Kontext dev, with prompts varying pose, angle and scene, and explicitly "same thick black ink line art, pure black and white, no grey" in every prompt; (3) threshold every candidate (section 6) *before* curating, so the training set is strictly binary; (4) keep 15-30 that are on-model (bun, centre-parted tapered fringe, closed lashed eyes, dog's scruff); (5) train one LoRA covering both characters plus style, or a character LoRA plus a separate style LoRA if the style must transfer to new characters.
- Licence shapes the choice of base: for any commercial output, FLUX.2 klein 4B and Qwen-Image(-Edit) are the clean Apache-2.0 options. FLUX.1 dev, Kontext dev, FLUX.2 dev and klein 9B need a BFL licence, or must be used through a hosted API whose terms grant commercial rights.
- Distinctive small features (lashes on closed eyes, fringe shape) are the most likely to drift in synthetic sets. Curation must check these specifically, not general resemblance.
- A dog is a second subject. Edit models' multi-subject consistency is weaker than single-subject consistency (see section 2), so the bootstrap may need separate solo-dog and solo-woman variants as well as joint ones.

### Gaps
- No published benchmark found that compares base models on *flat binary* line-art fidelity specifically. The ranking above is inferred from licence, ecosystem and general capability claims.
- No primary-source measurement found of how many synthetic images are "enough" for a two-character plus style LoRA. 15-40 is BFL's general guidance.
- The live fal FLUX LoRA trainer price was not verified (the indexed page is about 15 months old).
- Replicate's and fal's current FLUX.2 / klein trainer prices were not fetched.

---

## 2. Adapters and zero-training reference methods: which preserve line art best

### Takeaway
Face-ID adapters (PuLID, InstantID) are the wrong tool. They depend on photo-trained face detectors that fail on anime and cartoon faces. Of the training-free options, the 2025-2026 *edit/multi-reference* models (Qwen-Image-Edit-2509/2511, FLUX.2 [dev], FLUX.1 Kontext dev) are the strongest open options for keeping a character across new scenes. USO (ByteDance, FLUX.1-dev LoRA, CVPR 2026) is the open model built specifically to combine subject *and* style references. IP-Adapter/InstantStyle (2024) transfers style but does not hold character identity. FLUX Redux copies content rather than style. No benchmark tests any of these on pure B/W ink line art, so testing on the actual drawing is required.

### Cited Findings
- **PuLID / InstantID**: the PuLID repo issue #123 says "PuLID doesn't support anime faces" ("No faces detected"). The sd-webui-controlnet maintainer said the "input face must be realistic. These face detection lib cannot handle stylized face". InstantID issue #203 says InsightFace "is not good at identifying anime character". — [PuLID #123](https://github.com/ToTheBeginning/PuLID/issues/123); [sd-webui-controlnet discussion #2841](https://github.com/Mikubill/sd-webui-controlnet/discussions/2841); [InstantID #203](https://github.com/instantX-research/InstantID/issues/203) (2024-2025 issues)
- **IP-Adapter + InstantStyle**: InstantStyle applies the image prompt only in style-specific blocks to separate style from content. ComfyUI IPAdapter Plus added "Style transfer" (2024-03-27) and "Composition only" (2024-04-01) weight types for SDXL and a "Style & Composition" node. **[pre-2025, possibly stale]** — [HF Diffusers IP-Adapter docs](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter); [IPAdapter Plus README mirror](https://huggingface.co/thisisAce/runpod_custom_nodes/blob/main/ComfyUI_IPAdapter_plus/README.md)
- The ICAS paper (Apr 2025) found that IP-Adapter-based methods such as InstantStyle "struggle with maintaining subject identity when multiple entities are present". The AnimeAdapter paper (2026) says IP-Adapter "often fail[s] to preserve fine-grained appearance details" of anime characters. — [ICAS arXiv 2504.13224](https://arxiv.org/html/2504.13224v1); [AnimeAdapter arXiv 2605.20237](https://arxiv.org/html/2605.20237v1)
- A Krita AI Diffusion user (2025) reports that the "noobIPAMARK1" IP-Adapter works well with Illustrious/NoobAI alongside scribble/lineart ControlNet. — [krita-ai-diffusion #1803](https://github.com/Acly/krita-ai-diffusion/issues/1803) [anecdotal]
- **FLUX.1 Redux [dev]** is an image-variation adapter, distilled from Pro, that works like an IP-Adapter. Prompt-guided restyling is only in the paid FLUX1.1 [pro] Ultra API. A developer found that the strength scalar on its 729 reference tokens still yields "a variation of the reference's CONTENT" at any strength. Pooling to 81 tokens gave style-without-subject and 729 gave a clone. **[FLUX.1 Tools era, pre-2025, possibly stale]** — [HF model card](https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev); [arXiv 2507.09595 Demystifying Flux](https://arxiv.org/pdf/2507.09595); [deck-art-studio PR #51](https://github.com/drew-valentine/deck-art-studio/pull/51) [anecdotal]
- **FLUX.1 Kontext dev** (Jun 2025) does localised edits, style transfer and character consistency. Users report trouble with *two-image* style transfer, where the output is affected if the style image contains other subjects or text. — [Medium: Kontext dev](https://medium.com/diffusion-doodles/flux-1-kontext-dev-multimodal-image-editing-19a003714b40); [HF Kontext discussion #53](https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev/discussions/53) [anecdotal]
- **Qwen-Image-Edit-2509** (Sep 2025): 1-3 reference images (person+person, person+scene), "much better" person consistency, native ControlNet inputs (keypoints, edges, sketches), Apache 2.0. A Draw Things tutorial says to put the control image *first*. **Qwen-Image-Edit-2511** (Dec 2025) improves multi-person consistency. — [HF 2509 card](https://huggingface.co/Qwen/Qwen-Image-Edit-2509/blob/main/README.md); [Draw Things wiki](https://wiki.drawthings.ai/wiki/Qwen_Image_Edit_2509_TB_UT_transcript); [Qwen-Image-Edit-2511 guide](https://wanvideogenerator.com/blog/qwen-image-edit-2511-guide)
- A community LoRA, EQUES/qwen-image-edit-2509/2511-lineart-interpolation, generates in-between line-art frames. It is described as experimental. It shows that Qwen-Image-Edit can be fine-tuned to operate natively in the line-art domain. — [HF EQUES 2509](https://huggingface.co/EQUES/qwen-image-edit-2509-lineart-interpolation); [HF EQUES 2511](https://huggingface.co/EQUES/qwen-image-edit-2511-lineart-interpolation)
- **FLUX.2 [dev]** (Nov 2025): up to 10 references natively, which removes FLUX.1's need for a LoRA to hold a character, per BFL. — [BFL blog](https://bfl.ai/blog/flux-2)
- **USO** (ByteDance, arXiv 2508.18966, Aug 2025, CVPR 2026) is fine-tuned from FLUX.1-dev as a LoRA plus projector. It has subject, style, and joint subject+style modes. The first image is the content reference and the rest are style references. It needs about 16 GB with FP8/offload and 18 GB with multiple references. It has native ComfyUI support since 3 Sep 2025. — [GitHub bytedance/USO](https://github.com/bytedance/USO); [HF bytedance-research/USO](https://huggingface.co/bytedance-research/USO); [Comfy blog](https://blog.comfy.org/p/uso-available-in-comfyui)
- **OmniGen2 vs UNO vs DreamO** (all photo-centric benchmarks):
  - OmniContext (OmniGen2's own benchmark, Jun 2025): OmniGen2 overall 7.18 vs UNO 4.71; single-character SC 8.34 vs 6.48; multi-character SC 6.96 vs 2.38. — [OmniGen2 arXiv 2506.18871](https://arxiv.org/html/2506.18871v1) (self-reported)
  - UMO (Sep 2025) multi-identity ID similarity: DreamO 50.24, OmniGen2 40.81, UNO 31.82. DreamO gets confused as the number of references rises. — [UMO arXiv 2509.06818](https://arxiv.org/html/2509.06818)
  - A story-visualisation paper that measures identity *and art style*: DreamO DINO 58.59 vs UNO 56.24. Cross-panel identity CIDS: DreamO 51.5, with the authors' method at 66.6. OmniGen2 was not tested. — [arXiv 2512.01686](https://arxiv.org/html/2512.01686)
  - CogCanvas (2026): attribute fidelity collapses at 4 or more subjects. UNO is the exception. — [arXiv 2606.15867](https://arxiv.org/html/2606.15867)
  - [anecdotal] A YouTube tester found that OmniGen2 keeps overall feel but loses character features and clothing detail more than Kontext does. — [YouTube](https://www.youtube.com/watch?v=dVnWYAy_EnY)
- **In-Context LoRA** (Oct 2024, FLUX.1-dev) generates multi-panel sets in one image for consistency. **[pre-2025, possibly stale]** — [arXiv 2410.23775](https://arxiv.org/pdf/2410.23775)

### Inferences
- For a closed-eyes chibi face with no photo-like features, drop PuLID and InstantID entirely.
- The best training-free starting point is a multi-reference edit model: Qwen-Image-Edit-2511 (Apache) or FLUX.2 dev (NC licence, or a hosted API with commercial rights). Pass the original drawing as reference, a sketch or pose as a control image, and a text description of the new panel. USO is the specialised option if subject and style must be weighted separately.
- Training-free methods will probably drift on small identity details over many panels. A LoRA (section 1) is the stronger guarantee, so the practical design is edit-model bootstrap → LoRA → (optional) edit-model touch-up.
- IP-Adapter style mode with an Illustrious/NoobAI checkpoint plus a lineart ControlNet is a cheaper SDXL alternative for *style* only. It still needs a character LoRA for identity.

### Gaps
- No found source evaluates any adapter or edit model on pure binary, thick-ink line art. All identity and style metrics are on photos or coloured illustration.
- DreamO and UNO specifics (licences, VRAM, ComfyUI status as of 2026) were not fetched from their repos.
- No head-to-head of Qwen-Image-Edit-2511 vs FLUX.2 dev vs USO on stylised characters was found.

---

## 3. Pose/composition control: ControlNet lineart/scribble/openpose (FLUX, SDXL) and sketch-to-image

### Takeaway
On SDXL/Illustrious/NoobAI, xinsir's ControlNet++ Union ProMax (Jul 2024) and Eugeoter's NoobAI-specific ControlNets (Jan 2025) cover scribble, anime lineart and pose. They are the most mature route for turning the user's rough sketches into panels. On FLUX.1-dev, Shakker-Labs Union Pro 2.0 (Apr 2025) officially supports canny, soft edge, depth, pose and gray, and is used with lineart/scribble inputs in community workflows. On the 2025-2026 edit models, control is built in: Qwen-Image-Edit-2509+ accepts sketch, edge and keypoint images directly.

### Cited Findings
- **Shakker-Labs FLUX.1-dev-ControlNet-Union-Pro-2.0** (about 19 Apr 2025): official modes are canny, soft edge, depth, pose and gray (tile dropped). Mode embedding was removed, cutting size from 6.15 to 3.98 GB. Trained 300k steps on 20M images. Suggested conditioning scales are 0.7 (canny/softedge), 0.8 (depth) and 0.9 (pose/gray). An FP8 community build exists. — [HF model card](https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0); [comfyui-wiki news](https://comfyui-wiki.com/en/news/2025-04-19-flux-controlnet-union-pro-2)
- A Floyo workflow runs lineart and scribble through Union Pro 2.0 using AnimeLineArtPreprocessor. These are unofficial modes and probably read as edge input. — [Floyo](https://www.floyo.ai/workflows/flux-controlnet-2-0-all-in-one-b1910af72e3s) [anecdotal]
- **xinsir ControlNet++ Union / ProMax for SDXL** (released 06 and 13 Jul 2024 **[pre-2025, possibly stale]**): type 0 openpose, 2 thick line (scribble/hed/softedge), 3 thin line (canny/lineart/animelineart). Ships test scripts for anime lineart and scribble. Scribble "can support any line width and any line type". — [GitHub xinsir6/ControlNetPlus](https://github.com/xinsir6/ControlNetPlus); [HF xinsir scribble](https://huggingface.co/xinsir/controlnet-scribble-sdxl-1.0)
- Union ProMax "for the most part works fine for illustrious-based models". — [krita-ai-diffusion #1803](https://github.com/Acly/krita-ai-diffusion/issues/1803) [anecdotal]
- **NoobAI-specific ControlNets** (Eugeoter, first uploaded 13 Jan 2025): canny, depth, lineart-anime, lineart-real, mangaline, normal, scribble-pidi, scribble-hed, softedge-hed and tile. — [HF Eugeoter lineart_anime](https://huggingface.co/Eugeoter/noob-sdxl-controlnet-lineart_anime)
- **Qwen-Image-Edit-2509** accepts ControlNet-style inputs natively (depth, edge maps, keypoints, sketches). Line drawings can set structure alone or with a style reference, with the control image placed first. — [Qwen-Image GitHub](https://github.com/QwenLM/Qwen-Image); [Draw Things wiki](https://wiki.drawthings.ai/wiki/Qwen_Image_Edit_2509_TB_UT_transcript)

### Inferences
- For "user draws a rough panel sketch → finished ink panel", two candidate stacks: (a) Illustrious/NoobAI + character/style LoRA + xinsir scribble (type 2) or NoobAI scribble/mangaline ControlNet; (b) Qwen-Image-Edit-2511 with [rough sketch first, original reference second] plus a LoRA trained on Qwen-Image-Edit. (b) is newer and Apache-licensed. (a) has the larger body of community practice for anime line art.
- OpenPose skeletons are designed for normal human proportions. For chibi proportions, scribble or lineart control from a rough sketch is likely more reliable than OpenPose.

### Gaps
- No source found on OpenPose reliability for chibi or super-deformed proportions, or for dogs (animal pose).
- No found FLUX.2-specific ControlNet release was confirmed (FLUX.2 relies on multi-reference input). Not verified.

---

## 4. ComfyUI workflows for comics/consistent characters, and exposing workflows as an API

### Takeaway
As of October 2026 there are several ways to call a ComfyUI workflow from a Python backend. The official route is Comfy Org's Comfy API (launched about late Sep / early Oct 2026, per-second GPU billing, scale to zero) with a v2 HTTP API and Python SDK (still beta, 0.1.x). Third-party hosts are ComfyDeploy (open source, deploys onto RunPod/Modal), RunComfy, ViewComfy and RunPod Serverless's ComfyUI-to-API tool. Self-hosting ComfyUI on Modal or RunPod is also possible.

### Cited Findings
- **Comfy API (official)**: deploys a workflow with its custom nodes, models and dependencies to managed GPUs at `https://<deployment>.run.comfy.app`. Available on paid Comfy plans from "Standard". Per-second billing. Min 0 workers means scale to zero, with a cold start on the next request. CLI: `comfy deploy run --workflow workflow_api.json --deployment <id>`. — [Comfy blog: Comfy API is live](https://blog.comfy.org/p/comfy-api-is-live-deploy-comfyui); [Comfy support](https://support.comfy.org/articles/2703236295-comfy-api-deploy-your-comfyui-workflow-as-an-api) (Oct 2026, described as about a week old at search time)
- **Comfy API v2**: a versioned HTTP API (upload inputs, submit, observe, retrieve) with Python and TypeScript SDKs. The same API works on Comfy Cloud, Comfy API deployments, and self-hosted ComfyUI through a proxy. Beta 0.1.x. The v1 Cloud API is deprecated. — [docs.comfy.org v2 overview](https://docs.comfy.org/api-reference/v2/overview); [v1 Cloud API overview](https://docs.comfy.org/development/cloud/overview)
- **ComfyDeploy**: open-source "Vercel for AI workflows". Upload the workflow JSON and get a serverless endpoint with versioning and rollback, running on RunPod and Modal. — [Medium: 5 ways to deploy ComfyUI 2026](https://aguusstyu888.medium.com/5-top-ways-to-deploy-comfyui-workflows-in-2026-bc8a5e07eff8) [secondary]
- **RunComfy**: build in its cloud ComfyUI, save a version, create a Deployment, `POST /prod/v2/deployments/{id}/inference`, then poll or use a webhook. GPUs from 16 to 141 GB. One review reports cold starts averaging 30-60 s. — [RunComfy API docs](https://docs.runcomfy.com/serverless/custom-workflows); [Wireflow blog](https://www.wireflow.ai/blog/best-comfyui-hosted-api-tools-in-2026) (Wireflow ranks its own product first, so treat as biased)
- **ViewComfy**: deploys workflows as serverless APIs and apps, editable in the normal ComfyUI UI with Manager. — [viewcomfy.com](https://www.viewcomfy.com/)
- **RunPod Serverless ComfyUI-to-API**: an agent reads the exported workflow, generates a Dockerfile and GitHub repo, and deploys. — [Medium: 5 ways](https://aguusstyu888.medium.com/5-top-ways-to-deploy-comfyui-workflows-in-2026-bc8a5e07eff8) [secondary]
- Comic-relevant templates: USO has a native ComfyUI template ("Flux.1 Dev USO Reference Image Generation", Sep 2025). Qwen-Image-Edit has official Comfy templates. — [Comfy blog USO](https://blog.comfy.org/p/uso-available-in-comfyui); [Comfy Qwen-Image-Edit templates](https://comfy.org/workflows/model/qwen-image-edit/)

### Inferences
- A Python backend can stay portable by coding against Comfy API v2. Per Comfy docs, the same calls hit Comfy Cloud, a Comfy API deployment, or self-hosted ComfyUI on a rented pod, so the vendor can change without code changes.
- If no custom ComfyUI graph is needed (plain LoRA inference, or an edit model plus LoRA), fal or Replicate model endpoints are simpler than hosting ComfyUI.

### Gaps
- No primary source found for a dedicated "comic panel / consistent character" ComfyUI workflow that is well evaluated. Existing ones are community templates.
- Comfy API plan prices and GPU rates were not fetched.

---

## 5. Where to run: Replicate, fal.ai, RunPod, Modal, Colab, Vast.ai

### Takeaway
For a low-volume Python backend, per-image hosted endpoints (fal, Replicate) are cheapest in effort: Kontext LoRA or Qwen-Edit LoRA inference costs about $0.035/MP on fal, and LoRA training $1.25-$5 per run. For self-hosted ComfyUI or custom pipelines, Modal and RunPod Serverless bill per second with scale to zero. Hourly pods (RunPod, Vast.ai about $0.30-0.50/h for a 4090) are cheapest for training and batch dataset generation. Colab is cheap but does not guarantee a GPU and is unsuitable as a backend.

### Cited Findings
**fal.ai**
- Pay-per-use credits, no subscription, no permanent free tier. Hosted image examples include FLUX Kontext Pro at $0.04/image. — [fal review (aireiter)](https://aireiter.com/blog/fal-ai-review-2026) [third-party]
- Inference: `flux-kontext-lora` $0.035/MP (rounded up to the nearest MP); `qwen-image-edit-2511/lora` $0.035/MP. — [fal Kontext LoRA](https://fal.ai/models/fal-ai/flux-kontext-lora); [fal Qwen 2511 LoRA](https://fal.ai/models/fal-ai/qwen-image-edit-2511/lora)
- Training: see section 1 ($2 per FLUX LoRA run; Kontext $2.50/1k steps; Qwen-Edit $4/1k steps).
- Custom-deployment GPU list prices per third-party trackers (2026): H100 $3.99/h (as low as $1.89), H200 $4.50/h, RTX PRO 6000 $2.99/h (as low as $1.10). Per-second billing with no idle charges. Trackers disagree (Costbench lists H100 list price at $4.50). — [computecomparison: fal](https://computecomparison.com/provider/fal-ai); [Costbench, Aug 2026](https://costbench.com/software/ai-media-apis/fal-ai/); [PrePrice, Jun 2026](https://preprice.app/ai-costs/fal) [third-party, conflicting]

**Replicate** (acquired by Cloudflare; deal agreed Nov 2025, closed early 2026)
- Per-second: L40S $0.000975/s ($3.51/h), A100 80GB $0.0014/s ($5.04/h), H100 $0.001525/s ($5.49/h). T4 from $0.000225/s. No volume discount. — [replicate.com/pricing](https://replicate.com/pricing); [Spheron analysis 2026](https://www.spheron.network/blog/replicate-pricing-2026-per-second-cost/)
- Some image models are billed per output (since 29 Jan 2025): FLUX Dev $0.025/image, FLUX Schnell $3/1000. — [Spheron analysis](https://www.spheron.network/blog/replicate-pricing-2026-per-second-cost/)
- Cold starts: public models do not bill setup or idle time, but private models and deployments bill all online time. In one worked example, a 2-minute cold start made a 20 s H100 job cost $0.198, about 10× more. Replicate claims fine-tuned (LoRA) models boot in under 1 s. Third-party estimates put custom-model cold starts at 10-30 s typical and 60 s or more for large models. A 2024 HN report cites 2-3 min. — [Replicate blog: fine-tune cold boots](https://replicate.com/blog/fine-tune-cold-boots); [HN 2024](https://news.ycombinator.com/item?id=39413466) **[pre-2025]**; [WaveSpeed review](https://wavespeed.ai/blog/posts/replicate-review-2026/) (competitor, biased)
- FLUX.2 [dev] is hosted on Replicate with commercial use permitted through the platform. — [Replicate FLUX.2 dev](https://replicate.com/black-forest-labs/flux-2-dev)

**RunPod**
- Serverless (product page, Jul 2026): per-second billing from worker start to stop, $0.58/h (16 GB class) to $9.98/h (B300). Flex workers scale to zero. Active workers are always on and discounted (example: B200 $8.64/h flex vs $6.84/h active). — [RunPod Serverless](https://www.runpod.io/product/serverless)
- H100 serverless is about $4.55/h vs a $2.89/h Secure Cloud pod. A100 80GB pod $1.39-1.49/h vs serverless flex $2.72/h. Break-even about 66% utilisation. — [Spheron: RunPod pricing 2026](https://www.spheron.network/blog/runpod-h100-pricing-2026/) [third-party]
- FlashBoot: marketed as sub-200 ms cold start via pre-warmed workers. At launch the Whisper test measured 563 ms min and 42 s max. Loading 7B weights from a network volume takes about 15 s. Cold-start seconds are billed, plus about 5 s idle timeout. — [RunPod FlashBoot launch](https://www.runpod.io/blog/introducing-flashboot-serverless-cold-start); [RunPod: cold starts were never the real problem](https://www.runpod.io/blog/serverless-gpu-cold-starts-flashboot)

**Modal**
- Per-second (third-party copies of modal.com/pricing, Jul-Sep 2026): H100 $0.001097/s ($3.95/h), A100 80GB $2.50/h, A100 40GB $2.10/h, L40S $1.95/h, L4 $0.000222/s (~$0.80/h), A10 $0.000306/s, RTX PRO 6000 $0.000842/s. Starter plan $0/month with $30 credit. Region pinning applies a 1.5-1.75× multiplier. GPU functions are preemptible. — [Spheron: Modal pricing 2026](https://www.spheron.network/blog/modal-gpu-pricing-2026-per-second-billing/); [Beam: Modal pricing explained](https://www.beam.cloud/blog/modal-pricing-explained) (Beam is a competitor)

**Vast.ai**
- Marketplace. RTX 4090 on-demand median about $0.50/h (verified US/CA hosts, reviewed 1 Oct 2026). Cheapest listings: $0.32/h on-demand, $0.17/h spot. Cross-provider median $0.44/h (30 Sep 2026). — [Thunder Compute](https://www.thundercompute.com/blog/vast-ai-vs-thunder-compute); [GetDeploying 4090](https://getdeploying.com/gpus/nvidia-rtx-4090) [third-party]

**Google Colab**
- Pro $9.99/month for 100 CU; Pro+ $49.99 for 600 CU (an older NCSU page says 500). Measured burn (Mar 2026, unofficial): L4 1.71 CU/h (~$0.17/h), A100 40GB 5.40 CU/h (~$0.54/h), A100 80GB 7.52 CU/h (~$0.75/h). A specific GPU is not guaranteed. Sessions are limited to 24 h. — [mccormickml Colab GPUs](http://mccormickml.com/2024/04/23/colab-gpus-features-and-pricing/) (page dated 2024, figures said updated Mar 2026); [Thunder Compute Colab alternatives, Oct 2026](https://www.thundercompute.com/blog/colab-alternatives-for-cheap-deep-learning-in-2025)

### Inferences
- Suggested split: **training and dataset generation** on an hourly RunPod pod or Vast.ai 4090/L40S/A100 (a klein-4B LoRA is under 1 h on a 4090, about $0.50), or a fal trainer at $1.25-$5 per run. **Production inference** via fal/Replicate LoRA endpoints (per image or MP, no cold-start billing for public models) if the pipeline is "model + LoRA". If a custom ComfyUI graph is required, use Modal or RunPod Serverless (Python-native, scale to zero) or Comfy API.
- Qwen-Image-Edit (20B, ~16 GB FP8) and FLUX.2 dev (32B, 18-24 GB FP8) fit on L40S (48 GB) or A100. A 4090 (24 GB) is tight for FLUX.2 dev without offload.
- Modal is the most "Python backend"-native (functions defined in Python). fal and Replicate have Python clients for hosted endpoints.

### Gaps
- Modal, fal and RunPod pricing pages were not fetched directly. Figures come from third-party trackers that partly conflict (flagged above).
- No measured per-image cost found for Qwen-Image-Edit-2511 or FLUX.2 dev on serverless GPUs. Only fal's $0.035/MP rate.
- Modal and fal cold-start latencies for 20-32B image models were not found from primary sources.

---

## 6. Post-processing to pure black/white; models that output clean binary line art

### Takeaway
Diffusion models output anti-aliased greyscale edges and faint grey noise. No source found shows an open model that natively emits strictly binary pixels. The robust route is deterministic post-processing: grayscale, 2-4× upscale, Otsu or fixed threshold, light morphological cleanup, and optionally Potrace to SVG and re-rasterise. Training the LoRA on thresholded images pushes the model toward near-binary output, but a final threshold is still required.

### Cited Findings
- Anti-aliasing makes partially covered pixels grey, so line art "drawn as black on white" ends up with many grey shades. — [Wikipedia: Image tracing](https://en.wikipedia.org/wiki/Image_tracing)
- Potrace accepts only monochrome input (it thresholds first). It traces black/white boundaries into Bézier curves and works best at high resolution. Example pipeline: `magick input.png -threshold 50% input.bmp && potrace input.bmp -s -o out.svg --turdsize 5 --alphamax 1.0 --opttolerance 0.2`. `turdsize` removes specks and `alphamax` sets corner smoothness. — [pixotter: vectorize image](https://pixotter.com/blog/how-to-vectorize-image/); [Wikipedia: Image tracing](https://en.wikipedia.org/wiki/Vectorization_(image_tracing))
- Inkscape Trace Bitmap (Brightness cutoff) and Illustrator Image Trace (B/W preset) both wrap the same thresholding approach. — [svgvector Illustrator guide 2026](https://www.svgvector.com/blog/image-trace-illustrator-guide.html); [LaserGRBL docs](https://lasergrbl.com/usage/raster-image-import/vectorization-tool/)
- A vendor (VectoSolve) claims that classical tracers treat anti-aliasing as geometry and that its CNN vectoriser removes it. This is a marketing claim. — [VectoSolve blog](https://vectosolve.com/blog/ai-image-vectorization-explained) [vendor claim]
- Research on preprocessing for tracing: arXiv 2306.09039 (2023) applies high-pass filtering before autoencoder-based tracing. **[pre-2025, possibly stale]** — [arXiv 2306.09039](https://arxiv.org/pdf/2306.09039)

### Inferences
- In Python, a reasonable pipeline is: `PIL/OpenCV` grayscale → Lanczos 2-4× upscale → Otsu threshold (`cv2.THRESHOLD_OTSU`) → `cv2.morphologyEx` open/close with a 1-2 px kernel → optional `potrace` (pypotrace or CLI) → render SVG back at target resolution with `cairosvg` for even edges. Thick ink strokes survive thresholding well. Fine lashes are the most at risk of breaking or blobbing, so tune the threshold on the lash regions.
- Apply the same threshold to the bootstrap dataset before LoRA training (section 1), so the model never sees grey and grey-noise artifacts are not learned as style.
- Fixed-threshold binarisation keeps line *weight* but cannot fix the model's line *quality* (wobble, broken strokes). Potrace's curve fitting smooths wobble and gives a vector "ink" look.

### Gaps
- No source found evaluates whether any open diffusion model or LoRA produces strictly binary output. "Clean B/W line art" LoRAs on Civitai were not reviewed.
- No source compares Otsu, adaptive and fixed thresholds specifically on diffusion line-art output. The pipeline above is general practice, not a cited result.

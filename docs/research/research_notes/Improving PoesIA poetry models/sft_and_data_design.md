# SFT/LoRA and training-data design for poetry with small open LLMs (7–8B), without losing sense and grammar

Scope: how to build the SFT data and set up LoRA/QLoRA training so that Apertus v1.5 8B (es, en, it, de, fr) gains imagery, development and less repetition, without the loss of sense found in the first adapter. That adapter was trained on ~10k poets' own lines; the judge passed 68% of its Spanish lines vs 93% for the plain model; it stopped mid-clause, invented words, chose words more loosely, and held-out loss stayed ~3.0. Compute: Kaggle 2×T4 fp32, ~5 h, ~10k examples per run; Apertus 70B is available for inference only.

This note does not repeat `poesia-calaveritas/docs/research/research_notes/PoesIA shared poem quality layer/training_and_generation_strategies.md` (LIMA, AlpaGasus, DivPO, DDPO, CrPO, WQRM, LitBench, PoeLM, ALBERTI, Chen et al. diversity, Walsh et al., min-p). It cites those only where a new point depends on them.

All URLs accessed 2026-10-16. "(nr)" marks a source that was not fetched this session: the claim comes from the earlier note or from a well-known abstract and must be checked against the PDF before it is used publicly. Where a measurement's language matters, it is given in brackets: **[en]**, **[es]**, **[ru]**, **[he]**. Most of the evidence below is **English or language-agnostic (code/math)**. None of it is on Apertus.

## Q1. Training units (line, couplet/rhyme pair, stanza, whole poem) and how enjambment is handled

### Takeaway
No study found compares line, couplet, stanza or whole-poem units for LLM poetry SFT, and none trains on, or controls, enjambment. The evidence that applies is indirect but consistent: training targets that are cut-off fragments teach the model to produce fragments and to hallucinate (Fewer Truncations, ICML 2024), and the most successful style fine-tune to date used **self-contained units cut at natural boundaries** (paragraph breaks, 250–650 words), each paired with a teacher-written description of its content (Chakrabarty et al. 2025). For PoesIA this points to targets that end at a syntactic boundary (clause or sentence), not at an arbitrary line break.

### Cited Findings
- **Truncation teaches incoherence.** Standard concatenate-and-split packing cuts documents into incomplete pieces. Best-fit packing, which avoids unnecessary truncation, "reduces closed-domain hallucination effectively by up to 58.3%". It also gives relative gains of +4.7% on reading comprehension, +16.8% on context following and +9.2% on program synthesis. The authors argue that truncation keeps models from learning to write coherent, grounded content from complete context. This is pretraining, not SFT, and English text plus code [en] — [Ding et al., "Fewer Truncations Improve Language Modeling", ICML 2024, arXiv 2404.10830](https://arxiv.org/abs/2404.10830)
- **Self-contained units plus content descriptions (instruction backtranslation) gave the strongest style result.** Books were split into "context-independent excerpts" of 250–650 words at paragraph breaks; GPT-4o re-segmented overlong sections. For each excerpt GPT-4o wrote a content description that kept the sentence order. Each training pair was "Write a [n] word excerpt about the content below emulating the style and voice of [author]" + the description → the original excerpt. Base model GPT-4o, 30 authors, complete works per author (from 2 books to 22), 1 or 3 epochs, LR multiplier 2, batch size 1, generation at temperature 1.0 [en, prose] — [Chakrabarty, Ginsburg & Dhillon, arXiv 2510.13939 v3, Methods](https://arxiv.org/html/2510.13939v3)
- **The same study ran a grammar clean-up after generation.** "A GPT-4o post-processing pass fixed grammar, typos, and inconsistencies" in the fine-tuned outputs before evaluation. Even the best-reported fine-tune therefore did not rely on raw fine-tuned output being grammatical — [arXiv 2510.13939 v3](https://arxiv.org/html/2510.13939v3)
- **Phrase-level units with control codes** (from the earlier note): PoeLM split *prose* into phrases and prepended syllable-count and end-rhyme codes, learning meter and rhyme control without poetic training data [es, eu] — [PoeLM, arXiv 2205.12206](https://arxiv.org/abs/2205.12206) (nr this session)
- **Enjambment in generation, older work only.** A search for enjambment in poetry generation found Gervás (2017), an n-gram, line-based system that targets thematic cohesion and enjambment. Per the search summary, lines are built without a linking mechanism, so any enjambment is incidental. ByGPT5 (English and German quatrains; rhyme, meter and alliteration conditions) and PoeLM have no enjambment control — [Gervás 2017, ACL Anthology W17-3903](https://preview.aclanthology.org/fix_video/W17-3903.pdf) (search-summary only, nr); [ByGPT5, ACL 2023, arXiv 2212.10474](https://arxiv.org/abs/2212.10474v1)
- **Instruction backtranslation as a general method:** a seed model writes instructions for human-written text (self-augmentation), then selects the good pairs (self-curation). Two iterations on LLaMA beat all other LLaMA-based models on the Alpaca leaderboard "without using distillation data" [en] — [Li et al., "Self-Alignment with Instruction Backtranslation" (Humpback), ICLR 2024, arXiv 2308.06259](https://arxiv.org/abs/2308.06259)

### Inferences
- The first adapter's mid-clause stops match the truncation mechanism above: a target that is one enjambed line ends where the poet broke the line, not where the thought ends, so the model learns that a line may stop on an article, preposition or open clause. With ~10k examples, a sizeable share of targets were probably enjambed. **Measure that share first**, e.g. count targets that end without punctuation and whose last token is a function word.
- Options, in order of how directly they follow from the evidence (none is tested on poetry):
  1. **Clause-complete targets:** the answer is the next line *plus* whatever lines complete the clause or sentence (one to three lines). Keep the request's syllable and rhyme targets per line, and have the engine check each line. This is Fewer Truncations' lesson applied at line scale.
  2. **Rhyme pair or couplet as the unit**, when the pair closes a syntactic unit; a natural fit because the request already carries the rhyme partner.
  3. **Keep line units, but filter or tag them:** drop strongly enjambed targets, or add a PoeLM-style control code (`<enj>` / `<end>`) so the model enjambs only when asked. The deterministic engine can label this cheaply (final punctuation, part of speech of the last word).
  4. **Stanza or whole-poem units with a content description** (the Chakrabarty recipe): the closest analogue to the best-evidenced style fine-tune, but it changes PoesIA's line-by-line contract, and stanza targets are long for a 5-hour T4 budget.
- Apertus 70B fits the Humpback/Chakrabarty role: writing the **request** (theme, content description of the stanza) for real poems, so that the **answers stay human** (see Q3).

### Gaps
- No study found of SFT unit size (line vs couplet vs stanza vs poem) for poetry in any language, and none of enjambment-aware chunking for LLM training. The search returned only Gervás 2017, PoeLM and ByGPT5, none of which handles enjambment.
- Fewer Truncations measures pretraining, not instruction-style SFT on short targets. That it transfers to single-line targets is an inference.

## Q2. Mixing poetic with general instruction/prose data to prevent capability loss; "LoRA learns less and forgets less"

### Takeaway
LoRA forgets less than full fine-tuning but still forgets, and that forgetting is now tied to a mechanism (intruder dimensions). The best-evidenced protections are: (a) injecting a small share of general data (as little as **1% of pretraining data** stopped forgetting of the pretraining set, ICML 2025), (b) training on targets close to the model's own distribution (self-distillation, ACL 2024), and (c) training the style adapter on the **base** model and merging it into the instruct model, which cut the IFEval loss to roughly a third of direct LoRA's. Mixing helps most when task data is small (~10k is small).

### Cited Findings
- **LoRA learns less and forgets less.** Llama-2-7B; code and math; instruction fine-tuning (Magicoder-Evol-Instruct-110K, 72.97M tokens; MetaMathQA, 395K pairs, ~103M tokens) and continued pretraining up to 20B tokens. LoRA "substantially underperforms" full fine-tuning in the target domain but preserves base performance outside it better (forgetting = mean of HellaSwag, ARC-Challenge, WinoGrande). It forgets less than weight decay or dropout, and keeps generations more diverse. Full fine-tuning learns perturbations of 10–100× higher rank than typical LoRA [en, code/math] — [Biderman et al., TMLR 2024, arXiv 2405.09673](https://arxiv.org/abs/2405.09673); [HTML v2](https://arxiv.org/html/2405.09673v2)
- **Why LoRA forgets: intruder dimensions.** LoRA weight updates create new high-ranking singular vectors that full fine-tuning does not. Scaling them down after training brings the model back toward the pretraining distribution with only a small drop in task performance. They accumulate over sequential fine-tunes, so LoRA does worse in continual learning [en] — [Shuttleworth, Andreas, Torralba & Sharma, "LoRA vs Full Fine-tuning: An Illusion of Equivalence", arXiv 2410.21228 v3 (Oct 2025)](https://arxiv.org/abs/2410.21228). Venue not stated on the page.
- **A small replay share stops forgetting.** "Injecting as little as 1% of pretraining data in the finetuning data mixture prevents the model from forgetting the pretraining set." Scaling laws fitted across target domains, data amounts and model sizes. Forgetting here is measured as loss on the pretraining set, not as generation quality [en] — [Béthune et al., ICML 2025 (PMLR v267), arXiv 2502.06042](https://arxiv.org/abs/2502.06042); [PMLR page](https://proceedings.mlr.press/v267/bethune25a.html)
- **Mixed SFT data: the amount matters more than the ratio.** General (human-aligned) abilities "plateau after roughly a thousand samples", while math and code keep improving. Mixing helps when data is limited but causes conflicts when data is plentiful. The amount of composition data matters more than the ratio. Learning skills one after another risks catastrophic forgetting. Proposed fix: Dual-stage Mixed Fine-tuning (DMT) [en, LLaMA family; model sizes not given on the abstract page] — [Dong et al., ACL 2024, arXiv 2310.05492](https://arxiv.org/abs/2310.05492)
- **Self-distillation narrows the distribution gap.** Self-Distillation Fine-Tuning (SDFT) has the model itself rewrite the dataset's responses so that they match its original distribution. On Llama-2-chat it "effectively mitigates catastrophic forgetting", performs as well as or better than vanilla fine-tuning downstream, and helps keep helpfulness and safety alignment. Numbers are not on the abstract page [en] — [Yang et al., ACL 2024, arXiv 2402.13669](https://arxiv.org/abs/2402.13669)
- **Style adapter on the base model, merged into instruct (StyleAdaptedLM).** A LoRA trained with next-token loss on unstructured style text on the *base* model, then added to the *instruct* model's weights. IFEval-strict drop relative to the instruct model: StyleAdaptedLM 5.1% / 8.8% / 6.4% (Llama-3.1-8B / Mistral-7B / Qwen2.5-7B); model soups 2:1 7.3 / 9.8 / 8.2%; **direct LoRA fine-tuning 18.6 / 12.7 / 17.1%**; long-context prompting 15.7 / 18.0 / 17.3%. tinyMMLU unchanged. Data: Reddit (3 users, ~1,600 comments each), Enron emails (3 senders), CNN 2,000 / BBC 1,903 articles, ~1,500 marketing emails. Style was close to direct fine-tuning on classifier F1. Human evaluation by **one** copywriter. Adobe preprint, no peer-reviewed venue stated [en] — [Ramu et al., arXiv 2507.18294](https://arxiv.org/html/2507.18294v1)
- **Preserving diversity reduces forgetting.** GEM (entropy-regularised SFT, ICLR 2025) on 3B–70B models matched cross-entropy downstream with "significantly higher output diversity", and "preserving diversity also appears to reduce forgetting" [en] — [Li et al., arXiv 2408.16673](https://arxiv.org/abs/2408.16673)

### Inferences
- The judge's 93% → 68% drop in Spanish sense is a capability loss, and it is large next to what these papers report for LoRA (IFEval −13 to −19% for direct LoRA style tuning). It probably combines forgetting with the unit problem in Q1, and they should be separated. Train once on the **same data with clause-complete targets** and once with **general data mixed in**; whichever closes more of the 25-point gap shows which problem dominates.
- **Replay candidates, cheapest first:**
  1. Spanish (and it/de/fr/en) general instruction or prose data whose **answers Apertus 8B writes itself** (SDFT idea: the targets match its own distribution, so fluency is anchored without pulling the model elsewhere).
  2. Well-formed Spanish prose with literary register (e.g. public-domain prose), at a few percent of tokens.
  3. Dong et al.'s finding that general abilities plateau near ~1k samples suggests that **~1k–2k replay examples** (10–20% of a 10k run) is a reasonable first point; Béthune's 1% is a floor for *pretraining-set loss*, not for sense in generated verse. These ratios are inferences; nothing measured them on poetry.
- **Base-then-merge (StyleAdaptedLM) suits PoesIA's data**, since poets' text is unstructured. Train the adapter on raw stanzas and poems (no request format) on the Apertus 8B *base* checkpoint, then add it to the instruct checkpoint used in the line-by-line loop. This depends on the base and instruct releases sharing an architecture and tokenizer, which needs checking for Apertus v1.5.
- Train each adapter fresh from the base or instruct weights rather than stacking a new LoRA on an old one: intruder dimensions accumulate across sequential fine-tunes (Shuttleworth et al.).

### Gaps
- No study found of replay ratios for **creative or poetry** SFT, nor of forgetting measured as sense or grammar in generated text (all the measurements above are benchmark accuracy or pretraining loss).
- No forgetting measurements in Spanish, Italian, German or French found; all are English or code.
- The SDFT and DMT numbers were not read (abstract pages only).

## Q3. Distillation from a larger teacher with filtering; model collapse and homogenisation; how much human data must remain

### Takeaway
Collapse comes from **replacing** real data with generated data; **accumulating** generated data next to the real data avoided it (Gerstgrasser 2024). Keeping a random 10% of the original data each generation left only "minor degradation" (Shumailov's OPT-125m experiment). For creative text the safest use of a teacher is the one with the best results: let the teacher write the **requests or content descriptions** for human-written text (instruction backtranslation, Chakrabarty's author fine-tune) and use it as a **gate**, not as the author of the answers.

### Cited Findings
- **Model collapse, language-model experiment** (OPT-125m fine-tuned on wikitext2; generated data from 5-way beam search over 64-token blocks): with no original data kept (5 epochs per generation), performance degrades generation by generation; with a random **10% of the original data** kept each generation (10 epochs) there is "only minor degradation". Generated data contains "a large number of repeating phrases"; penalising repetition (penalty 2.0) roughly doubled perplexity, leaving models "as susceptible to Model Collapse, if not more". The perplexity values in the HTML render are garbled (e.g. "3434", likely 34, against a zero-shot baseline of about 115), so read them off Figure 10 before quoting. The claim that tails vanish comes from the Gaussian and VAE experiments; in the LM experiment, generated data had *longer* tails (sequences the original model would not produce) [en] — [Shumailov et al., "The Curse of Recursion", arXiv 2305.17493 v3](https://arxiv.org/html/2305.17493v3); published as [Nature 631 (2024), DOI 10.1038/s41586-024-07566-y](https://www.nature.com/articles/s41586-024-07566-y) (the Nature page was behind a login redirect; content read from the arXiv version)
- **Accumulate, don't replace:** replacing each generation's data with synthetic data "does indeed tend towards model collapse"; accumulating synthetic data alongside the original real data avoids it across model sizes, architectures and hyperparameters (also for diffusion models and VAEs). In a linear-model analysis, test error has a finite upper bound however many iterations are run. Preprint (venue not stated on the page); no numbers on the abstract page — [Gerstgrasser et al., arXiv 2404.01413](https://arxiv.org/abs/2404.01413)
- **Human answers with teacher-written prompts** gave the strongest creative fine-tune found: teacher-written content descriptions plus the original author text, ROUGE-L between generated and original 0.16–0.23, verbatim regurgitations resampled. Expert readers (28 MFA candidates, 3 per pair, 90 pairs, 720 judgments per outcome) preferred the fine-tuned output for stylistic fidelity (OR 8.16, 95% CI 4.69–14.2) and for quality (OR 1.87, CI 1.16–3.02); lay readers (131) preferred it with OR 8.29 and 2.42. Pangram flagged 3% of fine-tuned texts as AI vs 97% of in-context ones. Cliché density mediated 16.4% of the detection effect before fine-tuning and 1.3% (n.s.) after. Cost $25–276 per author (median $81). Corpus size did not predict performance [en, prose] — [arXiv 2510.13939 v3](https://arxiv.org/html/2510.13939v3)
- **Instruction backtranslation** (self-augmentation + self-curation over human web text) beat the other LLaMA-based models on Alpaca without distillation data [en] — [arXiv 2308.06259](https://arxiv.org/abs/2308.06259)
- Synthetic data for subjective tasks tends to be less diverse than human-written equivalents (a point made in the tongue-twister generation paper; seen in a search result, not verified in the PDF) — [Loakman et al., "Train & Constrain", arXiv 2403.13901](https://arxiv.org/pdf/2403.13901) (nr)
- Poetry needs a coherent voice and controlled choices across a body of work, not local fluency alone. In a blinded test, 50 humanities students and graduates labelled GPT-4 poems "human" 52% of the time (78/150) vs 54% (81/150) for poems by established poets; mean accuracy 0.510, not different from chance. The model was **shaped only by prompting** over 14 two-hour workshop sessions (no fine-tuning), and it "did not reliably sustain strict classical meter and rhyme" [he] — [Tohar, Hayat & Leshem, "Creating a digital poet", arXiv 2602.16578](https://arxiv.org/html/2602.16578v1)
- From the earlier note, not repeated in detail: quality-only gates and preference tuning narrow diversity (DivPO, Chung et al., Verbalized Sampling's typicality bias), and LLM poems are already under-diverse and full of stock words (Chen et al. EMNLP 2024; Walsh et al. 2024).

### Inferences
- **Recipe that follows from this evidence for PoesIA:**
  1. **Answers human, requests from the teacher.** Apertus 70B writes the theme or content description, and where useful the prior-line summary, for real poems; the poet's text stays the target.
  2. **Teacher as gate:** Apertus 70B (plus the deterministic engine) scores each *human* target for sense and grammar and drops the ones that would read as nonsense out of context: OCR damage, archaic spellings, heavily elliptical fragments. This targets the "invented words" and "loose word choice" directly.
  3. **If teacher-written verse is used at all** (e.g. to cover a form with few human examples), accumulate it alongside the human set, never instead of it. Cap its share (Shumailov's 10%-real survival point suggests human data should dominate, not the reverse; the exact safe share for poetry is unknown). Dedupe it, and check its diversity against the human lines with Chen et al.'s measures.
- Distilling **teacher verse** would import the teacher's poetic signature (Walsh et al.'s quatrains and stock words), which runs against the goal of imagery and less repetition. Distilling **teacher prose** (descriptions, paraphrases, general instructions) carries less of that risk.

### Gaps
- No study found of teacher-to-student distillation for **poetry** with a measured human-data share; the 10% and accumulation results are on wikitext/OPT-125m and toy or linear setups.
- No evidence on whether Apertus 70B's Spanish verse is good enough to serve as a teacher; it would need measuring with the judge first.

## Q4. Data-quality filtering for poetry corpora (perplexity and classifier filters, modern vs archaic language) and curriculum learning

### Takeaway
Poetry-specific corpus filtering has one direct paper (Russian, spelling and grammar anomaly detection for training data of poem and lyric generators). Beyond that, the usable tools come from the earlier note (memorization thresholds, LLM-judge gating) and from general data-curation work. No evidence was found on curriculum learning for creative or poetry SFT, nor on modern-vs-archaic filtering.

### Cited Findings
- **Linguistic anomaly detection as a pre-training filter for poetry and lyric generators.** Training texts scraped without quality control contain spelling and grammar anomalies; the paper compares unsupervised and supervised anomaly detectors on synthetic and human-labelled data, introduces RUPOR (human-labelled Russian poems for cross-sentence grammatical error detection), and releases evaluation code. Dataset sizes, detector names and scores are not on the abstract page. Single-author arXiv preprint [ru] — [Koziev, "Detecting Spelling and Grammatical Anomalies in Russian Poetry Texts", arXiv 2505.04507](https://arxiv.org/abs/2505.04507)
- **Memorization gate** (from the earlier note): Ratcliff–Obershelp similarity ≥ 0.7 to a training quatrain = memorized (≥ 0.9 per verse, ≥ 0.8 per couplet) [en, de] — [Chen et al., EMNLP 2024, arXiv 2406.15267](https://arxiv.org/html/2406.15267v2)
- **Quality beats quantity for SFT data** (AlpaGasus 9k of 52k by judge score; LIMA 1k), from the earlier note — [arXiv 2307.08701](https://arxiv.org/abs/2307.08701) (nr); [arXiv 2305.11206](https://arxiv.org/abs/2305.11206) (nr)
- **Self-curation by the model** (Humpback): the seed model rates candidate pairs and keeps the high-scoring ones (the rating scale is not on the abstract page) — [arXiv 2308.06259](https://arxiv.org/abs/2308.06259)

### Inferences
- For "invented words", the cheapest gate is lexical: every word in a target line must be in a Spanish lexicon (e.g. a Hunspell `es` dictionary plus the corpus's own proper nouns). Lines with neologisms, archaic forms (*fermosa*, *vido*), or OCR damage can be kept apart and either dropped or kept only with an explicit "archaic register" tag. That is an inference from Koziev's framing, not a measured result.
- A perplexity filter needs care for poetry. Low perplexity under the 8B model selects conventional, cliché-prone lines (the quality the project wants to leave), while very high perplexity flags noise. A **two-sided** filter (drop the top tail, e.g. OCR noise and foreign-language fragments; keep the middle) is the defensible version; the thresholds would need tuning against the judge.
- Curriculum (simple, end-stopped lines first, enjambed and archaic later) is plausible, but no evidence was found; on a single 5-hour run it is lower priority than the unit and mixing fixes.

### Gaps
- No study found on perplexity-based or classifier-based filtering of **poetry** SFT data, or on how filtering affects sense or creativity in generated verse. General perplexity-pruning work (e.g. Ankner et al. 2024, arXiv 2405.20541) was not fetched and is pretraining-scale.
- No study found on modern vs archaic language in poetry training corpora, in any language.
- No study found on curriculum learning for creative-writing or poetry SFT.

## Q5. Hyperparameters for small creative LoRA (rank, LR, epochs, target modules) and their effect on fluency; sampling temperature after SFT

### Takeaway
The two best sources agree. Apply LoRA to the **MLP layers** (or all layers), not attention only. The best LoRA learning rate is about **10× the full fine-tuning rate** (Biderman: 2e-4 to 5e-4 on Llama-2-7B). LoRA is sensitive to **large batches**. Higher learning rates and more epochs learn more and forget more. On entropy, cross-entropy SFT is usually reported to narrow diversity, but a September 2026 preprint shows the direction depends on model and data, and finite-sample SFT can leave a model **over-dispersed**. That fits a ~3.0 held-out loss on high-entropy poetic targets producing loose word choice at temperature 1.

### Cited Findings
- **Biderman et al. settings (Llama-2-7B):** ranks 16, 64, 256 with α = 2r; best LoRA LR code 5e-4 vs full fine-tuning 5e-5; math 2e-4 vs 1e-5. Instruction fine-tuning was run for 1, 2, 4, 8 and 16 epochs. In a Magicoder ablation, attention-only LoRA underperformed MLP-only and all-module LoRA, and most of the gain came from the MLP. Best-practice recommendations quoted in the paper: "using LoRA for instruction finetuning and not continued pretraining"; "if GPU memory allows, targeting 'All' transformer modules with a rank of 256"; "using α=2r"; "sweeping over learning rates between [1e-5, 5e-4], picking the highest value that enables stable training" [en, code/math] — [arXiv 2405.09673 HTML v2](https://arxiv.org/html/2405.09673v2)
- **"LoRA Without Regret"** (Thinking Machines Lab with John Schulman, 29 Sep 2025; a blog post, **not peer-reviewed**): the optimal LoRA LR is "consistently 10x" the full fine-tuning LR (about 15× for runs under ~100 steps, anecdotal). "Attention-only LoRA significantly underperforms MLP-only LoRA", also at matched parameter counts (attention-only r256, 0.25B params, trails MLP-only r128, 0.24B). For small-to-medium instruction datasets LoRA matches full fine-tuning; low ranks fall behind only when capacity runs out. LoRA tolerates large batches less well, and the gap does not close with rank — [thinkingmachines.ai/blog/lora](https://thinkingmachines.ai/blog/lora/)
- QLoRA's original report: adapters on **all linear layers** were needed to match 16-bit full fine-tuning — [Dettmers et al., NeurIPS 2023, arXiv 2305.14314](https://arxiv.org/abs/2305.14314) (nr)
- **Entropy and diversity after SFT, three views:**
  - Cross-entropy SFT fits the observed answers without weighing other plausible ones, which reduces output diversity. GEM (entropy-regularised, reverse-KL-linked SFT) kept performance comparable on 3B–70B models with significantly higher diversity and less forgetting [en] — [Li et al., ICLR 2025, arXiv 2408.16673](https://arxiv.org/abs/2408.16673)
  - "Generation breadth narrows after SFT", attributed to neglect of low-frequency patterns and to forgetting; the authors propose a Tempered Focal (TOFU) loss. Preprint, Apr/May 2026, no numbers on the abstract page — [Klypa & Cherednichenko, arXiv 2605.00195](https://arxiv.org/abs/2605.00195)
  - **"SFT is not inherently biased toward mode collapse or its opposite"**: whether the result is collapse or over-dispersion depends on model and dataset; finite-sample SFT can leave a model under- or over-dispersed relative to the target; more target data moves diversity toward the target level. The collision-probability gap is bounded by √KL(target‖model). Tested on synthetic languages and four LLMs fine-tuned on human survey data and CodeNet. Preprint, 15 Sep 2026, numbers not on the abstract page — [Skobelev, Fithian & Han, arXiv 2609.16454](https://arxiv.org/abs/2609.16454)
- Temperature correlates only weakly with novelty and moderately with incoherence (from the earlier note) — [Peeperkorn et al., arXiv 2405.00492](https://arxiv.org/abs/2405.00492) (nr)
- Fine-tuning settings in the strongest creative result: 1 epoch for the authors with the largest corpora, 3 for the rest, LR multiplier 2, batch size 1, temperature 1.0 at generation, then a grammar post-processing pass — [arXiv 2510.13939 v3](https://arxiv.org/html/2510.13939v3)

### Inferences
- **Reading the first adapter through these results:** held-out loss ~3.0 nats/token is a perplexity of about 20 (e^3), i.e. the targets are high-entropy, and with ~10k examples the model sits in the "finite-sample" regime where over-dispersion is possible (Skobelev et al.). Sampled at the plain model's temperature, a model that has spread its probability mass will choose looser words and, with subword vocabularies, can recombine pieces into non-words. This is a plausible mechanism, not a measured one. **Test it cheaply first:** sweep temperature (e.g. 0.5 / 0.7 / 0.9 / 1.0) and top-p or min-p on the existing adapter and see how much of the 68% → 93% gap the judge recovers. If a lower temperature closes most of it, the adapter is over-dispersed rather than broken.
- **Settings to try for an 8B QLoRA on 2×T4 (inferences from the sources above):** target the MLP plus attention projections (`gate/up/down` + `q/k/v/o`); rank 16–64 with α = 2r (Biderman's r256 is out of reach on T4 memory); LR around 1e-4–2e-4, taking the highest stable value; 1–2 epochs rather than 3+, since more learning means more forgetting; small effective batch (≤ 16–32 sequences). For a ~10k-example run, one epoch at the higher LR and two at the lower is a fair comparison.
- **Measure sense against held-out loss.** Loss on poets' lines will stay high by nature; the judge's sense rate and a lexicon-based non-word rate are the metrics to watch per checkpoint (e.g. every 500 steps), so that training can stop before fluency falls.

### Gaps
- No study found of LoRA rank, LR or epoch effects on **creative or poetic** quality or fluency; all hyperparameter evidence is code, math or general instruction following.
- No direct study found of temperature tuning after creative SFT, or of whether SFT on high-entropy literary text raises output entropy; Skobelev et al. show it *can*, for other data.
- fp32 on T4 (no bf16) may change the stable LR range; no source covers this.

## Q6. Style transfer and author-voice fine-tuning (fine-tuning vs prompting)

### Takeaway
Fine-tuning on an author's own text consistently gets closer to the author's surface style than prompting, and in the largest study (30 authors, expert readers) it also beat expert human imitators on quality. But the evidence is English prose; it fine-tuned a frontier model (GPT-4o) with natural, self-contained units; and it still cleaned grammar after generation. Small-model studies show style uptake at a cost in instruction following unless the adapter is trained on the base and merged.

### Cited Findings
- **Fine-tuning vs prompting with expert readers** (GPT-4o, 30 living authors, complete works): in-context prompting lost to MFA writers 6–8× (earlier note); fine-tuning reversed it (experts OR 8.16 for fidelity, 1.87 for quality). 27 of 30 authors were above parity on fidelity (median win 0.74) and 23 of 30 on quality (median 0.58). Median fine-tuning premium +41.7 points (fidelity) and +16.7 (quality). The reversal is attributed to the removal of detectable AI quirks such as cliché density [en, prose] — [Chakrabarty, Ginsburg & Dhillon, arXiv 2510.13939 v3](https://arxiv.org/html/2510.13939v3)
- **StyleTunedLM** (LoRA on LLaMA-2 for 10 authors from Project Gutenberg; aimed at writers with ~1k–50k tokens of prior work): outputs match the author lexically, syntactically and on surface features, but "struggle with content memorization"; users choose whether named entities and content words are learned. Lists 1k–50k tokens as the target corpus size [en] — [Liu, Diddee & Ippolito, INLG 2024, arXiv 2409.04574](https://arxiv.org/abs/2409.04574v1); [ACL Anthology 2024.inlg-main.34](https://preview.aclanthology.org/new-sigs/2024.inlg-main.34/) (findings taken from the search summary and abstract; the PDF was not read)
- **StyleAdaptedLM** (base-trained LoRA merged into instruct, 7–8B models): style close to direct fine-tuning, with IFEval losses of 5–9% vs 13–19% for direct LoRA (details in Q2) [en] — [arXiv 2507.18294](https://arxiv.org/html/2507.18294v1)
- **Prompt-only shaping of a poet** (GPT-4, 14 workshop sessions) reached chance-level human/machine discrimination on Hebrew free verse with 50 readers, but did not sustain strict classical meter and rhyme [he] — [arXiv 2602.16578](https://arxiv.org/html/2602.16578v1)

### Inferences
- PoesIA's adapter is closer to StyleTunedLM's setting (small model, LoRA, period authors) than to Chakrabarty's (frontier model, whole excerpts). Expect lexical and syntactic uptake (which the first adapter showed as development and less repetition) together with some loss of instruction following and sense, unless the base-then-merge route or a replay mix is used.
- Chakrabarty's units (self-contained excerpts at natural breaks, with a content description) are the transferable part. For verse that means stanzas or sentence-complete spans with a short Apertus-70B-written description of what they say, not isolated lines.
- Because even the GPT-4o fine-tune needed a grammar post-pass, PoesIA's deterministic repair engine plus the judge should stay in the loop after any adapter; an adapter alone is not expected to remove the need for repair.

### Gaps
- No author-voice fine-tuning study found for **verse**, or in Spanish, Italian, German or French.
- StyleTunedLM's quantitative scores were not read (summary only).

### Source list for Zotero capture (all accessed 2026-10-16)

Fetched this session:
- Béthune, L. et al. 2025. Scaling Laws for Forgetting during Finetuning with Pretraining Data Injection. ICML 2025, PMLR 267. arXiv:2502.06042
- Biderman, D. et al. 2024. LoRA Learns Less and Forgets Less. TMLR (Featured Certification). arXiv:2405.09673
- Chakrabarty, T., Ginsburg, J. C. & Dhillon, P. 2025. Readers Prefer Outputs of AI Trained on Copyrighted Books over Expert Human Writers. arXiv:2510.13939 (already cited in the earlier note)
- Ding, H. et al. 2024. Fewer Truncations Improve Language Modeling. ICML 2024. arXiv:2404.10830
- Dong, G. et al. 2024. How Abilities in Large Language Models are Affected by Supervised Fine-tuning Data Composition. ACL 2024. arXiv:2310.05492
- Gerstgrasser, M. et al. 2024. Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data. arXiv:2404.01413
- Klypa, R. & Cherednichenko, O. 2026. Diversity in Large Language Models under Supervised Fine-Tuning. arXiv:2605.00195 (preprint)
- Koziev, I. 2025. Detecting Spelling and Grammatical Anomalies in Russian Poetry Texts. arXiv:2505.04507 (preprint)
- Li, X. et al. 2024. Self-Alignment with Instruction Backtranslation. ICLR 2024. arXiv:2308.06259
- Li, Z. et al. 2025. Preserving Diversity in Supervised Fine-Tuning of Large Language Models (GEM). ICLR 2025. arXiv:2408.16673
- Liu, X., Diddee, H. & Ippolito, D. 2024. Customizing Large Language Model Generation Style using Parameter-Efficient Finetuning. INLG 2024. arXiv:2409.04574
- Ramu, P. et al. 2025. StyleAdaptedLM: Enhancing Instruction Following Models with Efficient Stylistic Transfer. arXiv:2507.18294 (preprint)
- Shumailov, I. et al. 2024. AI models collapse when trained on recursively generated data. Nature 631. DOI 10.1038/s41586-024-07566-y; preprint "The Curse of Recursion", arXiv:2305.17493
- Shuttleworth, R., Andreas, J., Torralba, A. & Sharma, P. 2024/2025. LoRA vs Full Fine-tuning: An Illusion of Equivalence. arXiv:2410.21228
- Skobelev, K., Fithian, E. & Han, X. Y. 2026. Fine-Tuning Fixes Mode Collapse and Over-Dispersion in LLMs. arXiv:2609.16454 (preprint)
- Tohar, V., Hayat, T. & Leshem, A. 2026. Creating a digital poet. arXiv:2602.16578 (preprint)
- Yang, Z. et al. 2024. Self-Distillation Bridges Distribution Gap in Language Model Fine-Tuning. ACL 2024. arXiv:2402.13669
- Belouadi, J. & Eger, S. 2023. ByGPT5. ACL 2023. arXiv:2212.10474 (abstract page only)

Not fetched this session (nr), cited for context:
- Dettmers, T. et al. 2023. QLoRA. NeurIPS 2023. arXiv:2305.14314
- Gervás, P. 2017. ACL Anthology W17-3903 (search summary only)
- Loakman, T. et al. 2024. Train & Constrain. arXiv:2403.13901
- Peeperkorn, M. et al. 2024. Is Temperature the Creativity Parameter of LLMs? arXiv:2405.00492
- Ormazabal, A. et al. 2022. PoeLM. Findings of EMNLP 2022. arXiv:2205.12206
- Chen, Y. et al. 2024. Evaluating Diversity in Automatic Poetry Generation. EMNLP 2024. arXiv:2406.15267
- Zhou, C. et al. 2023. LIMA. arXiv:2305.11206; Chen, L. et al. 2023. AlpaGasus. arXiv:2307.08701

Non-scholarly (no DOI/arXiv, not for Zotero as a paper): Thinking Machines Lab / Schulman, "LoRA Without Regret", blog post, 29 Sep 2025, https://thinkingmachines.ai/blog/lora/

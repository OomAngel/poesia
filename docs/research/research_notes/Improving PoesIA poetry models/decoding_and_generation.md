# Decoding and generation-time strategies for better poetry from a small LLM (Apertus v1.5 8B, 4-bit GGUF), as of October 2026

Scope note: the sibling notes in `poesia-calaveritas/docs/research/research_notes/PoesIA shared poem quality layer/` already cover PoeLM generate–filter–rerank (k = 3000, 30.9 % valid in Spanish), Ou et al. 2023 reverse vs biased decoding (99.23 % rhyme accuracy right-to-left; biased decoding "abruptly changes the end-word"), Van de Cruys 2020 reverse generation, the Greek generate–verify–refine loop (< 4 % → 73.1 % valid), Anthropic's rhyme-planning circuit (~70 % restructuring), Chae et al. 2025 ChatGPT syllable errors (79.8–83.7 %), WQRM reranking (66–72 % expert preference), Self-Refine, Agents' Room, Re3, Tian & Peng 2022 sonnet planning, min-p vs Schaeffer, Peeperkorn on temperature, Verbalized Sampling 1.6–2.1×, and similarity retrieval of exemplars (Liu et al. 2022). Those are referenced here only where needed and not re-derived. Everything below is new material or new numbers. "Not re-fetched this session" marks a claim taken from the abstract or from memory of the paper without opening its full text here.

## 1. Constrained decoding for metre and rhyme (rhyme-first, lookahead, grammars, syllable-aware search, NeuroLogic) and its effect on fluency

### Takeaway
Hard token-level enforcement buys form at a measurable cost in fluency, and only works well when the constraint can be checked on a prefix. Lookahead methods (FUDGE, NeuroLogic A*esque) recover much of that fluency by scoring where a prefix can still go, not just whether it is still legal. For poetry, the one controlled test (FUDGE, iambic pentameter couplets) got 44 % full success against 0 % for the base model, with perplexity rising from 44 to 71. Grammar-constrained decoding (GBNF) distorts the model's distribution, so a "forced" end word is sampled out of proportion to how plausible it is. That is the mechanism behind "Silence drifts like an abril".

### Cited Findings
**Lookahead / future discriminators (FUDGE, NAACL 2021; English)**
- Task: complete a couplet given the first line of each of Shakespeare's 154 sonnets. The completion must (1) be iambic pentameter, (2) rhyme with line 1, (3) end a sentence, all judged by a rule-based checker (CMUdict rhyme sound). FUDGE trains small predictors on prefixes (B1 iambic, B2 "will this end with rhyme sound r with t syllables left", B3 sentence end) and adds their log-probabilities to GPT-2-Medium's next-token log-probabilities. — [Yang & Klein, arXiv 2104.05218, §4.1](https://arxiv.org/abs/2104.05218)
- Results (Table 2, n = 154 prefixes): success G (base GPT-2) **0**, fine-tuned 0.21, PPLM 0, **FUDGE 0.44**, Shakespeare himself 0.45 (the narrow checker rejects archaic pronunciations and elisions). Grammaticality 0.52 (G) vs 0.44 (FUDGE). Perplexity **44.3 (G) → 70.9 (FUDGE)**; fine-tuning 55.8. Dist-1/2/3 rose slightly (0.35/0.74/0.77 → 0.40/0.79/0.78): the authors read the constraint as pushing sampling into lower-probability regions. — [FUDGE PDF, Table 2](https://arxiv.org/pdf/2104.05218v2)
- The FUDGE authors note that a Hafez-style system "which enforces meter and rhyme at each decoding step using a hard constraint, could achieve perfect success rate", but only because metre and rhyme are "prefix-checkable" at the word level ("never selecting a word which immediately violates the constraint"). — [FUDGE §4.1](https://arxiv.org/pdf/2104.05218v2). Hafez itself: Ghazvininejad et al., EMNLP 2016, FSA over rhyme-and-metre-legal word sequences — [aclanthology D16-1126](https://aclanthology.org/D16-1126/) (not re-fetched this session)

**NeuroLogic A*esque (NAACL 2022; English; GPT-2)**
- Adds A*-style estimates of future constraint satisfaction (greedy, beam or sampled lookahead rollouts) to NeuroLogic's beam over lexical constraints. — [Lu et al., arXiv 2112.08726](https://arxiv.org/abs/2112.08726)
- CommonGen (keyword-to-sentence; human eval of 100 test items on a 3-point scale), unsupervised GPT-2: NeuroLogic coverage 96.7 %, overall human 2.50 → **A*esque (greedy) 97.1 %, overall 2.70**; quality 2.64 → 2.78. Supervised: all constrained decoders reach ~97.5 % coverage; the human-rated gain comes from lookahead (2.50 → 2.60). Older constrained beams (CBS, GBS, DBA) scored 2.01–2.23 overall at the same coverage. So **coverage is easy; fluency at equal coverage is what lookahead buys**. — [NAACL 2022 PDF, Table 1](https://aclanthology.org/2022.naacl-main.57.pdf)
- Constrained question generation (zero-shot): coverage NeuroLogic 90.6 % → A*esque **100 %**, meaningfulness 2.49 → 2.74–2.76. — [Table 7](https://aclanthology.org/2022.naacl-main.57.pdf)
- Unconstrained RocStories (GPT-2 fine-tuned): A*esque lookahead raised human "overall" from **2.15 → 2.47** for top-k sampling and 2.32 → 2.63 for beam search, with diversity unchanged or higher. Greedy lookahead has the lowest runtime. Krippendorff α only 0.22–0.30 ("fair"). — [Table 8, footnotes 3–4](https://aclanthology.org/2022.naacl-main.57.pdf)

**Grammar-constrained decoding (GBNF etc.) distorts the distribution**
- Grammar-constrained decoding (GCD) "can distort the LLM's distribution, leading to outputs that are grammatical but appear with likelihoods that are not proportional to the ones given by the LLM"; their ASAp method gives higher-likelihood outputs than GCD on code and structured NLP tasks (no creative tasks). — [Park et al., "Grammar-Aligned Decoding", NeurIPS 2024, arXiv 2405.21047](https://arxiv.org/abs/2405.21047)
- Format restrictions (JSON/XML, constrained output) "significantly" reduce LLM reasoning performance, with stricter constraints hurting more. — [Tam et al., "Let Me Speak Freely?", arXiv 2408.02442](https://arxiv.org/abs/2408.02442) (abstract only; no creative-task numbers)
- llama.cpp GBNF constrains output with formal grammars, supports Unicode character classes and `{m,n}` repetition, and warns that "Grammars currently have performance gotchas (see #4218)"; chains of optional symbols are "extremely slow". The README does not document fixed word lists, though `|` alternation can express them. — [llama.cpp grammars/README.md](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)

**Syllable-aware generation for lyrics (melody constraints = syllable/stress constraints)**
- Lyra (Tian et al., ACL 2023; English): plan (keywords from title/genre) → GPT-2 writes lyrics, with **melody-guided constrained decoding** over syllable counts and stress-vs-duration. Training with auxiliary syllable-counting tasks raised syllable-count success from **23.14 % → 93.60 % (greedy) / 19.87 % → 89.13 % (sampling)**. On 120 test songs, **hard** rhythm constraints raised stress–duration alignment to 89.5 % but raised perplexity from 85 to **108**; the **soft** constraint (α = 0.01) gave 68.4 % alignment (humans 73.3 %) and the best human-rated overall quality (p < 0.05 vs next best except creativity; 1–5 Likert, ≥ 3 raters, Pearson 0.47). — [arXiv 2305.19228](https://arxiv.org/abs/2305.19228)
- Chae et al. (Interspeech 2025; English) reach their 4.4 % syllable error by **training with syllable-count tokens**, not by constrained decoding; per level SCErr is 0.27 % word, 0.79 % phrase, **2.85 % line**, 68.8 % paragraph. Sampling: top-k 20, top-p 0.9, T = 1.0, repetition penalty 1.2. Conditioning at each step improved control but raised perplexity (17.1 → 19.9, "reduces foresight"). No human evaluation. — [arXiv 2411.13100, Table 2](https://arxiv.org/abs/2411.13100)

### Inferences
- PoesIA's failure "Silence drifts like an abril" is the expected outcome of forcing an end word the model did not plan. Ou et al. (sibling note) found biased decoding swapped end words regardless of context. Park et al. show the mechanism: constrained sampling does not respect how likely the model thought the forced continuation was. FUDGE and A*esque show the remedy: **score rhyme candidates by how well the model can reach them from the current context, before committing**. Cheap version for PoesIA: for each rhyme-bank word w, compute the 8B model's log-probability of w (or of the line ending with w) given the stanza so far and the plan, and offer only the top few plausible words. This is a one-step lookahead; it needs logprobs, which llama.cpp exposes.
- Prefer **soft** form pressure plus rejection (Lyra's α = 0.01 beat hard constraints on human quality; FUDGE's form gain cost ~60 % perplexity) over hard grammar enforcement. Keep GBNF for structural scaffolding (line count, newline per line, no prose preamble), not for the end word.
- Line-level syllable control is achievable at ~3 % error with training (Chae) and ~90 % success with auxiliary-task training (Lyra). Untrained instruction models stay far worse (sibling note). So the decoding layer alone will not close the metre gap; it complements the deterministic repair loop.

### Gaps
- No study found that applies FUDGE/A*esque lookahead or GBNF to Spanish, Italian, German or French metre, or to modern 7–8B instruction models. All numbers above are English and GPT-2-era.
- No measured effect of GBNF on poem quality was found. The distortion evidence is from code and structured NLP tasks.
- The FUDGE couplet task had no human evaluation of quality.

## 2. Reranking: best-of-n with judges, classifiers or embeddings; MBR; self-consistency; cost vs gain

### Takeaway
For short creative pieces, the measured gains come from **many samples → deterministic filter → learned or judged ranking** (PoeLM, WQRM, sibling note) and from candidate selection inside an editor (Reffly: match rate 0.51 → 0.82 with selection). MBR has been shown to trade quality against diversity well, but only on directed tasks (MT, captioning, CommonGen), at O(N²) utility cost; no creative-writing MBR study was found. MBR's consensus objective also selects the most typical candidate, which works against originality.

### Cited Findings
- Reffly (melody-constrained lyric **revision**, LLaMA-2-13B-chat + LoRA on 3,500 lyric points): diverse beam search proposes candidates, which are filtered for singability and ranked by prominent-word alignment, with BERTScore similarity to the draft as tie-breaker. Removing candidate selection dropped match rate from **0.82 to 0.51**. — [arXiv 2409.00292, Table 1 ablation](https://arxiv.org/abs/2409.00292)
- MBR overview: selecting the candidate with the lowest expected risk under a utility function improves summarization, data-to-text, translation and style transfer over sampling/beam; not tested on fiction or poetry. — [Suzgun, Melas-Kyriazi & Jurafsky, Findings ACL 2023](https://aclanthology.org/2023.findings-acl.262/) (abstract-level, via search result)
- Diverse MBR and k-medoids MBR (Jinnai et al., Findings ACL 2024): 64–128 epsilon-samples (ε = 0.01–0.02), BERTScore utility. DMBR gives higher diversity than diverse beam search and sampling at equal mean BLEU on WMT'19. Cost is **O(N²) utility calls**: DMBR with 128 samples was 2–4× slower than DBS with k = 4. The authors state that open-ended tasks such as story generation are future work. — [arXiv 2401.05054](https://arxiv.org/html/2401.05054v1)
- A*esque lookahead also acts as a reranker inside sampling: it raised human overall quality for top-k stories from 2.15 to 2.47 at equal diversity (§1). — [NAACL 2022, Table 8](https://aclanthology.org/2022.naacl-main.57.pdf)
- Self-judging is weak for creativity: in Olson et al., Llama3-8B as judge "often gave all stories about 7/9" and was a poor predictor of which of two stories was more creative. **Llama3-70B** as judge agreed with a human annotator **> 70 %** (pair count not stated). — [arXiv 2412.06060](https://arxiv.org/html/2412.06060)

### Inferences
- PoesIA's 8 candidates per line ranked by language/metre/rhyme/reuse is already the right shape. The evidence suggests three upgrades, in order of cost: (a) add a **semantic-progression** term (penalise cosine similarity of the candidate line to earlier lines and stanzas, which targets "restates instead of develops"); (b) add an **end-word plausibility** term (the log-prob lookahead in §1); (c) use a judge model **larger than the generator** or a trained reward model, since an 8B self-judge does not discriminate creativity.
- Do not use plain MBR as the final selector for poems: its consensus utility picks the median candidate, the opposite of what PoesIA needs against repetition. If MBR is used, use it with a *dissimilarity* term (DMBR-style) to choose a varied set of drafts to show the user, not one winner. At N = 8 per line, O(N²) = 64 embedding similarities is negligible; the cost concern only applies to LLM-scored utilities.
- Self-consistency (majority vote) has no meaning for open-ended poems; its closest useful analogue is the "agreement among several form checkers" PoesIA already uses.

### Gaps
- No MBR or self-consistency study on poetry, lyrics or stories found. The cost/gain curve of best-of-N for poems vs N is unmeasured beyond PoeLM's pass rate.
- No numbers found for embedding-based rerankers of poems against human preference (see the sibling `embeddings_for_poetry.md`).

## 3. Sampling methods: contrastive decoding, DoLa, min-p, typical sampling, temperature schedules, anti-repetition

### Takeaway
None of the sampling methods has solid human-evaluated evidence of better *poems*. Contrastive decoding and typical sampling have human evaluations on open-ended prose that favour them over nucleus/top-k, mainly by reducing repetition. DoLa targets factuality and is irrelevant here. Min-p's creative-writing claim was contested (sibling note), and newer samplers (top-nσ, top-H, min-k) are supported mostly by LLM-as-judge. The diversity problem at its root comes from alignment (aligned models favour "pleasant" over original writing). Prompt-level methods (Verbalized Sampling) and output-level avoidance penalties have larger measured diversity effects than truncation samplers.

### Cited Findings
- Contrastive decoding (expert LM log-prob minus amateur LM log-prob, under a plausibility constraint) "significantly outperforms four strong decoding algorithms (e.g., nucleus, top-k)" in automatic and human evaluations on Wikipedia, news and story domains; it targets the short, repetitive text of greedy decoding and the incoherence of sampling. — [Li et al., ACL 2023, arXiv 2210.15097](https://arxiv.org/abs/2210.15097) (abstract only; numbers not re-fetched this session)
- Locally typical sampling: "competitive" quality with nucleus and top-k on story generation and summarization, while "consistently reducing degenerate repetitions". — [Meister et al., TACL 2022, arXiv 2202.00666](https://arxiv.org/abs/2202.00666) (abstract only)
- DoLa (contrasting late vs early layers) was designed and evaluated for **factuality** (TruthfulQA, FACTOR), not creative quality. — [Chuang et al., ICLR 2024, arXiv 2309.03883](https://arxiv.org/abs/2309.03883) (not re-fetched this session)
- Min-p: the reanalysis found that min-p did not outperform baselines in quality, diversity or the trade-off, and that the original human evaluation omitted data — [Schaeffer et al., arXiv 2506.13681](https://arxiv.org/abs/2506.13681). Newer truncation samplers are evaluated mainly by LLM judges: top-H reports up to 25.63 % over min-p "on creative writing benchmarks" with an LLM judge — [arXiv 2509.02510](https://arxiv.org/abs/2509.02510v1); min-k uses DeepSeek-V3.2-Exp as judge on AlpacaEval prompts, with a small human sample on LLaMA3-8B favouring min-k over top-nσ 41–33 (26 ties) — [arXiv 2604.11012](https://arxiv.org/pdf/2604.11012) (both via search snippets only; not verified in full text)
- Avoidance Decoding (EMNLP 2025, stories): penalises similarity to previously generated outputs, concept-level early and narrative-level later; reports up to **2.6× output diversity** and **~30 % less repetition** than strong baselines. — [Park, Yang & Jung, doi:10.18653/v1/2025.emnlp-main.381](https://aclanthology.org/2025.emnlp-main.381/) (abstract only; models and human eval not checked)
- Aligned models "favor pleasant writing over creative originality" in creative writing, and better standard-benchmark performance tends to go with worse randomness and creativity. — [West & Potts, "Base Models Beat Aligned Models at Randomness and Creativity", arXiv 2505.00047](https://arxiv.org/abs/2505.00047)
- Verbalized Sampling, poem task human evaluation (1–4 dissimilarity scale): Direct **1.90**, Sequence 2.07, VS-Standard **2.39**. VS-Standard can lower quality on smaller models (GPT-4.1-mini, Gemini-2.5-Flash), and VS-CoT/VS-Multi avoid the drop. Larger models gain ~1.5–2× more diversity than smaller ones. — [Zhang et al., arXiv 2510.01171](https://arxiv.org/html/2510.01171)
- Temperature at 1.0 with FUDGE's constraint pushed sampling into lower-probability regions and *raised* distinct-n (§1), so constraints already add diversity. — [FUDGE Table 2](https://arxiv.org/pdf/2104.05218v2)

### Inferences
- Apertus 8B is an aligned (instruct) model, so West & Potts predict a "pleasant but same" bias that no truncation sampler fixes. Levers that act on *what has already been said* fit PoesIA's measured problems (repeated words, repeated end words, restating) better: a stanza-level n-gram/lemma penalty (llama.cpp's DRY or repetition penalty applied over the poem, not just the line), an Avoidance-Decoding-style penalty against earlier stanzas, and a ban on reused end words. All of these must leave the rhyme scheme's required repeats intact (e.g. a refrain).
- A temperature *schedule* is plausible but unmeasured for poetry: higher temperature (0.9–1.1) when generating the stanza plan, imagery or candidate end words, and lower (0.6–0.8) when writing the line toward a fixed end word, where fluency matters most. Test it with the existing form gate in the loop rather than adopting it on faith.
- Verbalized Sampling works at the *proposal* stage ("give 5 different directions for stanza 2 with probabilities"). For an 8B model, prefer the VS-CoT variant, since the quality drop was seen on small models.

### Gaps
- No human evaluation of contrastive decoding, typical sampling, min-p, top-nσ or DRY on poetry in any language found. No measurement of the samplers on Apertus.
- No temperature-schedule study for creative text found (the adaptive-temperature work found in searches targets code).
- Contrastive decoding needs a smaller "amateur" model with the same tokenizer; Apertus has no smaller sibling in v1.5 that I verified (unchecked).

## 4. Planning: plan-then-write, content plans per stanza, keyword or storyline planning, hierarchical generation, last word first

### Takeaway
Every lyric and poetry system with a strong human evaluation plans first. Keyword plans (Lyra: +24 % relative overall quality over SongMASS), discourse and rhyme-pair plans (Tian & Peng 2022) and section plans (Agents' Room) all help, and LLMs internally plan the rhyme word before writing the line. The "restates instead of develops" failure is a missing content plan: a per-stanza plan with distinct roles (image, turn, consequence, close) is the generation-time fix with the best support, and it is cheap (one extra call).

### Cited Findings
- Lyra hierarchy: input (title, genre, 3 YAKE salient words) → **BART keyword plan** → GPT-2 lyrics from the plan → melody-constrained decoding. Human ratings: **24 % relative overall-quality improvement** over SongMASS; salient-word coverage 89.4–91.8 %. — [Tian et al., ACL 2023, arXiv 2305.19228](https://arxiv.org/abs/2305.19228)
- Reffly's structure-aware mode (verse/chorus structure planned, then lyrics revised to fit): structural clarity **3.36 vs 1.15** for GPT-4, prosody 3.10 vs 1.31, singability 3.11 vs 1.28 (1–5 Likert, ≥ 3 MTurk raters from 49 qualified, Pearson 0.69; item count not stated). — [arXiv 2409.00292, Table 4](https://arxiv.org/abs/2409.00292)
- Chae et al. plan song form with section tokens (verse/chorus) and syllable budgets per level; the error stays low at line level (2.85 %) but is 68.8 % at paragraph level, so **budgets must be enforced per line, not per stanza**. — [arXiv 2411.13100, Table 2](https://arxiv.org/abs/2411.13100)
- Plan-and-Write (storyline of keywords, then story) improved story coherence over direct generation in human evaluation. — [Yao et al., AAAI 2019, arXiv 1811.05701](https://arxiv.org/abs/1811.05701) (not re-fetched this session)
- Prompted GPT-4 "could not reliably sustain classical rhyme and meter" in Hebrew over a seven-month workshop; the authors attribute this to "the gap between next-word prediction and the planning rhyme requires". — [Tohar, Hayat & Leshem, arXiv 2602.16578](https://arxiv.org/html/2602.16578v1)
- Already in the sibling notes: Tian & Peng 2022 sonnet discourse + rhyme-pair planning; Agents' Room; Re3; Anthropic's evidence that the model activates candidate end words at the newline before writing the line (≈ 70 % restructuring when a planned word is swapped); Ou et al. right-to-left decoding (99.23 % rhyme accuracy).

### Inferences
- Hierarchy for PoesIA: **poem plan** (theme, arc, stanza roles, one concrete image per stanza, words banned from repetition) → **stanza plan** (what this stanza adds that the previous did not; candidate end words chosen *by the model* from its own plan and then checked against the rhyme key) → **line** (write toward the fixed end word). This puts rhyme choice where the model's own planning happens (end-word selection with context) rather than drawing from a bank and forcing it.
- "Last word first" without a reverse model: ask the model for 5–10 end-word candidates per rhyme slot given the stanza plan, keep those that pass the deterministic rhyme check and are not near-copies (lemma/stem check), rank by the lookahead log-prob (§1), then prompt the line ending with the chosen word. This replaces the free rhyme bank as the primary source; the bank becomes a fallback and a filter.
- The development problem can be checked automatically: embed each stanza and reject a stanza whose similarity to an earlier one exceeds a threshold, or whose plan role is not realised (a judge question "what does stanza 3 add?").

### Gaps
- No controlled study found that compares plan-then-write vs direct generation for *short poems* with modern 7–8B models, or in es/it/de/fr.
- No study found on *who* should pick the rhyme word (model-chosen vs lexicon-chosen) with human ratings of sense; the inference above rests on Ou et al., FUDGE and the planning circuit.

## 5. Iterative refinement and editing loops that keep sense; stanza-level editing

### Takeaway
Repair works when an external checker gives precise defects (Greek loop: < 4 % → 73.1 % valid, sibling note) and when the edit is constrained to stay close to the draft (Reffly: revision preserves content and beats GPT-4 on musicality and coherence). Free self-critique by the same small model is the weakest form. Long human-mentored critique loops can bring prompted GPT-4 free verse to indistinguishable-from-human (50 readers, chance), but not classical metre.

### Cited Findings
- Reffly frames lyric control as **revision of a plain-text draft** rather than constrained generation from scratch. Arbitrary-content task (Table 1): match rate **0.82** (Lyra 0.48, GPT-4 0.35), perplexity 310 (GPT-4 635), coherence **2.46** vs GPT-4 1.96, creativity 2.22 vs 1.92, singability 2.32 vs 1.45. Chinese→English song translation: match 0.83 vs 0.35, translation quality 3.04 vs 2.33. Claim: ~25 % better than Lyra and GPT-4 on musicality and text quality. Sample sizes not stated. — [arXiv 2409.00292](https://arxiv.org/abs/2409.00292)
- Tohar et al.: GPT-4, 14 two-hour sessions over 7 months; each session introduced one principle (avoid clichés, punctuation, original metaphor, allusion …) → draft → detailed human critique → revision → the model restates the principle, stored for later sessions. Blinded test with 50 humanities students and graduates, each rating 6 poems (3 human from 20 by established poets, 3 AI from 18): AI poems labelled "human" **52 % (78/150)** vs human poems **54 % (81/150)**; subject accuracy mean 0.510, t(49) = 0.322, p = 0.75. Hebrew free verse; classical rhyme and metre failed. No comparison of critique styles. — [arXiv 2602.16578](https://arxiv.org/html/2602.16578v1)
- LLM Review (blind peer review among agents, independent revision; science-fiction stories, SciFi-100 dataset) reports that smaller models with the framework beat larger single-agent models, and that it "consistently outperforms multi-agent baselines", judged by LLM-as-judge, human annotation and novelty metrics. — [Li et al., arXiv 2601.08003](https://arxiv.org/abs/2601.08003) (abstract only; no numbers verified)
- Earlier poetry polishing: iterative polishing with a quality-aware masked LM for Chinese poetry. — [Deng et al., AAAI 2020, arXiv 1911.13182](https://arxiv.org/abs/1911.13182) (not re-fetched this session)
- Sibling notes: Self-Refine (~20 % average gain, no poetry), Huang et al. (self-correction without external feedback often fails), Chakrabarty et al. 2024 (targeted editing for clichés "shows promise").

### Inferences
- PoesIA's repair re-prompt (defect + rhyme bank) is a generate–verify–refine loop. To keep sense it should (a) give the model the **whole stanza and its plan**, not just the failing line, (b) ask for a minimal edit ("change as few words as possible; keep the image"), and (c) reject repairs whose embedding similarity to the original line falls below a threshold or whose end word is a near copy (Reffly's BERTScore tie-break is the precedent). When a line fails rhyme, offer to repair the *partner* line instead (the rhyme pair can move to a word that fits both), which forced single-line repair cannot do.
- Stanza-level editing: run the deterministic checks per line but run the "development" critique per stanza (redundancy with earlier stanzas, repeated words) and rewrite the stanza with its line skeleton and end words held fixed. This uses an external, checkable signal, which is what separated the successful loops from failed self-correction.
- The Tohar result suggests that **principle-level critiques** (no clichés, one concrete image, no abstraction stacking) can be turned into a fixed checklist prompt that the system applies without a human. That is untested at 8B.

### Gaps
- No measured comparison of line-level vs stanza-level repair for sense preservation found.
- No evidence on how many repair rounds an 8B model can take before quality falls; the Greek loop allowed 15 attempts but reported validity, not sense.

## 6. Steering without training: activation steering, prompt-level control, retrieved exemplars

### Takeaway
Activation steering toward "creative" is demonstrated on Llama3-8B with a single layer-8 vector, but evaluated only with LLM judges and figures, with no quality trade-off measured, and steering is known to be unreliable and to break text at too high a strength. With a quantised GGUF model it is feasible (llama.cpp control vectors) but experimental. Prompt-level methods (Verbalized Sampling, retrieved exemplars by form and theme) are cheaper, measured, and fit an OpenAI-compatible API path that cannot steer activations.

### Cited Findings
- Creativity steering (Olson et al., NeurIPS 2024 Creativity & GenAI workshop): vector = normalised difference of mean layer-8 activations for creative vs uncreative versions of 500 writing prompts (GPT-4o wrote the uncreative counterparts); applied at λ = 3 to Llama3-8B; T = 1.0, top-p 1.0, 256 tokens. Induced stories moved toward the creativity direction; a Llama3-70B judge agreed with a human > 70 % on pairwise creativity. Early-layer interventions "can fail to produce meaningful text", final-layer ones have little effect, middle layers balance quality and creativity. No strength sweep, no numeric quality trade-off, sample sizes not stated. — [arXiv 2412.06060](https://arxiv.org/html/2412.06060)
- Steering reliability: prompt-derived steering shows a net positive effect but "high variance across samples" and often the opposite effect — [Braun et al., ICLR 2025 "Understanding (Un)Reliability of Steering Vectors"](https://iclr.cc/virtual/2025/33377); across 50 behaviours incl. style and persona, trait expression follows an **inverted U** with coefficient strength — [arXiv 2511.18284](https://arxiv.org/abs/2511.18284v2) (both via search snippets; not read in full)
- Verbalized Sampling poem diversity 1.90 → 2.39 (human, 1–4) (§3). — [arXiv 2510.01171](https://arxiv.org/html/2510.01171)
- In-context author-style prompting left expert readers preferring human text 6–8×, while fine-tuning reversed it; similarity retrieval of exemplars beats random selection in general NLG (sibling note, Q3).

### Inferences
- For the hackathon timeline, activation steering is a research bet: it needs a contrastive prompt set per language, a layer and strength sweep, and quality checks with the form gate. It also cannot run on the OpenAI-compatible API path. Rank it after planning, end-word lookahead, repetition penalties and exemplar retrieval.
- Exemplar retrieval for PoesIA: retrieve 2–3 real poems matching **language, metre/stanza form and occasion**, rotate them per request, and run the existing memorisation check on the output. Exemplars anchor form and register; they will not remove the instruct-model "pleasant" signature (West & Potts; the in-context style study), which needs training.

### Gaps
- No activation-steering study on poetry, metre or rhyme, or on non-English creative text, found.
- No study found on llama.cpp control vectors with 4-bit quantisation for style or creativity.
- No measured effect of retrieved real-poem exemplars on poem quality (vs random or none) found.

### Source identifiers for Zotero (new in this note; sibling-note sources not repeated)
- Yang & Klein 2021, FUDGE, NAACL — arXiv:2104.05218, doi:10.18653/v1/2021.naacl-main.276 (DOI from the Anthology pattern; not verified this session)
- Lu et al. 2022, NeuroLogic A*esque Decoding, NAACL — arXiv:2112.08726, aclanthology 2022.naacl-main.57
- Ghazvininejad et al. 2016, Generating Topical Poetry (Hafez), EMNLP — aclanthology D16-1126
- Park et al. 2024, Grammar-Aligned Decoding, NeurIPS — arXiv:2405.21047
- Tam et al. 2024, Let Me Speak Freely? — arXiv:2408.02442
- Tian et al. 2023, Unsupervised Melody-to-Lyric Generation (Lyra), ACL — arXiv:2305.19228
- Chae et al. 2025, Song Form-aware Full-Song Text-to-Lyrics Generation, Interspeech — arXiv:2411.13100, doi:10.21437/Interspeech.2025-1247
- REFFLY: Melody-Constrained Lyrics Editing Model — arXiv:2409.00292 (author list and venue not verified this session)
- Suzgun, Melas-Kyriazi & Jurafsky 2023, Follow the Wisdom of the Crowd (MBR), Findings ACL — aclanthology 2023.findings-acl.262
- Jinnai et al. 2024, Generating Diverse and High-Quality Texts by MBR Decoding, Findings ACL — arXiv:2401.05054
- Li et al. 2023, Contrastive Decoding, ACL — arXiv:2210.15097
- Meister et al. 2023, Locally Typical Sampling, TACL — arXiv:2202.00666
- Chuang et al. 2024, DoLa, ICLR — arXiv:2309.03883
- Top-H Decoding, NeurIPS 2025 — arXiv:2509.02510
- Min-k Sampling 2026 — arXiv:2604.11012
- Park, Yang & Jung 2025, Avoidance Decoding, EMNLP — doi:10.18653/v1/2025.emnlp-main.381
- West & Potts 2025, Base Models Beat Aligned Models at Randomness and Creativity — arXiv:2505.00047
- Yao et al. 2019, Plan-and-Write, AAAI — arXiv:1811.05701
- Tohar, Hayat & Leshem 2026, Creating a digital poet — arXiv:2602.16578
- Li et al. 2026, LLM Review (blind peer review for creative writing) — arXiv:2601.08003
- Deng et al. 2020, Iterative polishing with a quality-aware masked LM for Chinese poetry, AAAI — arXiv:1911.13182
- Olson et al. 2024, Steering LLMs to Evaluate and Amplify Creativity — arXiv:2412.06060
- Braun et al. 2025, Understanding (Un)Reliability of Steering Vectors, ICLR — iclr.cc/virtual/2025/33377 (arXiv id not verified)
- What Can We Actually Steer? A Multi-Behavior Study of Activation Control — arXiv:2511.18284
- Zhang et al. 2025, Verbalized Sampling — arXiv:2510.01171 (already in sibling note; poem numbers new here)

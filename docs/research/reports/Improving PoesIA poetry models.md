# Finish the thought before optimising the poem

The next real gains for PoesIA probably do not need a new training algorithm. They need three cheap fixes to what adapter v3 already does, plus two changes in how lines are generated. All are testable within a few Kaggle runs, and the first costs no training at all. v3 lost Spanish sense (judge pass **93% → 68%**) through two causes that the literature predicts. First, its single-line targets ended where the poet broke the line, so the model learned to stop mid-thought, the same way truncated training text teaches incoherence ([Ding et al. 2024](https://arxiv.org/abs/2404.10830)). Second, training on high-entropy poets' lines left it sampling loosely at temperature 0.9. A September 2026 preprint shows this kind of over-dispersion after finite-sample SFT ([Skobelev et al.](https://arxiv.org/abs/2609.16454)). PoesIA's own split of the judge verdicts shows that **the second cause is the larger one**. Closed lines alone pass only 74% (es) and 68% (de) against 94% and 91% for the plain model. By my arithmetic, closing every line would recover at most about 6 of the 25 Spanish points. So the ordered plan starts with a temperature sweep on v3. It then retrains with clause-complete targets and a 10–20% replay share of the model's own general text, and moves rhyme-word choice from a bank into the model's stanza plan, ranked by its own log-probability. Offline preference tuning (KTO or DivPO-style pairs built automatically) comes only after that, and couplet-level GRPO comes last. GRPO is the least evidenced method for metrical verse: the one full-text rhyme study saw collapsed outputs rise from 2 to 17 in 100 ([Ogawa & Kawahara 2026](https://aclanthology.org/2026.acl-srw.27.pdf)). Evaluation is the binding limit. The Apertus 70B verdict can veto nonsense but cannot rank competent lines, which is a known range-restriction property of LLM sense judges ([Mareček et al. 2025](https://aclanthology.org/2025.eval4nlp-1.9)). And one owner's few dozen blind pairs can only confirm preferences of about 75% or stronger. Almost none of the evidence is on Apertus, and most of it is English, so every step below has to be checked on PoesIA's own four-level scorecard.

## v3 lost sense by two routes, and the larger one is word choice

The starting point is PoesIA's own measurement. In the October baseline the plain 8B was close to the poets *within* the line (Spanish metre at the modal count 85% vs 89%) and far from them *above* it. Its paired lines restate each other at a centred cosine of 0.35–0.41 against 0.07–0.12 for poets. Its consecutive stanzas restate at 0.58–0.64 against 0.18–0.25. It repeats 4.1–7.3 content words per poem against 1.3–2.8 ([TUNING_ROUNDS §1a](../../TUNING_ROUNDS_2026-10.md)). Adapter v3 was a QLoRA trained on 10,242 real-poem lines in the page's request shape, with caps on openings and end words across the set. It fixed much of that. Stanza restatement fell to 0.40–0.42 in all four languages, Spanish content-word repetition fell from 4.6 to 2.6, and Italian metre rose from 83% to 96% and rhyme from 49% to 68%. But **the 70B judge's sense pass fell from 93% to 68% in Spanish and from 91% to 64% in German**, while French held at 93% → 89% ([TUNING_ROUNDS §1b](../../TUNING_ROUNDS_2026-10.md); [b22](../../../reports/eval_2026-10/b22-sense-adapter-v3.json)).

The project already separated two causes, and the split shows which matters more. The adapter closes fewer lines with punctuation (es 67% → 55%, de 98% → 67%), and its open lines pass the judge only 57% of the time. Its *closed* lines also fail more: 74% (es) and 68% (de), against 94% and 91% for the plain model. My arithmetic, assuming the judge scores lines independently: if every Spanish line closed and passed at today's closed-line rate, the pass rate would be about 74%. That recovers about 6 of the 25 lost points. In German it recovers about 4 of 27. **Most of the loss lies inside complete lines**: odd syntax, invented forms ("aufgehebt", "desasalta"), and occasional stutter.

Each cause has a mechanism in the literature. For the open lines, Fewer Truncations found that cutting training documents into fragments teaches models to write incoherently, and that avoiding truncation cut closed-domain hallucination by up to **58.3%** ([Ding et al., ICML 2024](https://arxiv.org/abs/2404.10830)). That result is from pretraining, so carrying it over to one-line SFT targets is an inference. For the closed lines, three effects fit, and they are not exclusive:

- **Over-dispersion.** The held-out loss of about 3.0 nats per token is a perplexity near 20. Skobelev et al. show that SFT is "not inherently biased toward mode collapse or its opposite": finite-sample SFT can leave a model *over*-dispersed relative to its target ([arXiv 2609.16454](https://arxiv.org/abs/2609.16454)). At an unchanged temperature of 0.9, that predicts looser word choice and subword recombinations into non-words.
- **Forgetting.** LoRA "learns less and forgets less" than full fine-tuning, but it still forgets ([Biderman et al., TMLR 2024](https://arxiv.org/abs/2405.09673)). The forgetting has a mechanism: new high-ranking "intruder dimensions" in the weights ([Shuttleworth et al.](https://arxiv.org/abs/2410.21228)). In a direct style-transfer comparison at 7–8B, plain LoRA fine-tuning cost **13–19%** of IFEval-strict ([StyleAdaptedLM](https://arxiv.org/html/2507.18294v1)). v3's 25-point drop in sense is large next to that.
- **Overtuning for form.** The closest published case is Czech. The authors' own LoRA-tuned Llama models "often generated too many non-existent and mostly nonsensical words" while chasing metre and rhyme ([Mareček et al. 2025](https://aclanthology.org/2025.eval4nlp-1.9)). v3 is the same pattern in four languages.

Two further facts set expectations. The strongest published style fine-tune trained GPT-4o on 30 authors' complete works and was preferred by expert readers. Even it ran "a GPT-4o post-processing pass [that] fixed grammar, typos, and inconsistencies" before evaluation ([Chakrabarty, Ginsburg & Dhillon](https://arxiv.org/html/2510.13939v3)). An adapter alone should not be expected to remove the need for PoesIA's deterministic repair and sense gate. And the project's untested alternatives remain open: training on NF4 and serving on Q4_K_M, and imitation of 19th-century syntax without the poets' control of it.

## Retrain on whole thoughts, human answers and a replay share

### Training units should end where the sentence ends

No study compares line, couplet, stanza or whole-poem units for poetry SFT, and none controls enjambment. The research notes found only Gervás's 2017 n-gram system and form-controlled models that ignore enjambment ([research note](../research_notes/Improving%20PoesIA%20poetry%20models/sft_and_data_design.md)). The indirect evidence points one way, though. The best style fine-tune used "context-independent excerpts" of 250–650 words, cut at paragraph breaks. Each was paired with a teacher-written content description, and the original text was the answer. Expert readers preferred the result to expert human imitators for stylistic fidelity (odds ratio **8.16**) and for quality (1.87) ([Chakrabarty et al.](https://arxiv.org/html/2510.13939v3)).

For PoesIA's line-by-line contract, the nearest equivalent is a **clause-complete target**: the poet's next line plus whatever lines complete its clause or sentence, usually one to three lines. The request keeps the syllable and rhyme targets for each line, and the engine checks every line. The rhyme pair is a natural second unit wherever the pair closes a syntactic unit. A third option keeps line units but tags them, in the spirit of PoeLM's control codes ([PoeLM](https://arxiv.org/abs/2205.12206)). An `<end>` or `<enj>` code, which the engine can assign from final punctuation and the part of speech of the last word, would teach the model to enjamb only when asked. The cheapest first step needs no GPU: count how many v3 targets end with no punctuation and a function word as the last token. That share sets the ceiling on how much the unit fix can help.

### Mixing and merging protect fluency better than more poetry

The best-evidenced protections against capability loss are cheap:

- **Replay.** Injecting "as little as **1%** of pretraining data" into a fine-tuning mix stopped forgetting of the pretraining set ([Béthune et al., ICML 2025](https://arxiv.org/abs/2502.06042)). That figure is measured as pretraining loss, not as sense in verse, so 1% is a floor. Dong et al. found that general abilities "plateau after roughly a thousand samples" in mixed SFT, and that mixing helps most when task data is small ([ACL 2024](https://arxiv.org/abs/2310.05492)). That points to **about 1,000–2,000 replay examples, 10–20% of a 10k run**, as a reasonable first point. Nothing has measured that ratio on poetry.
- **Self-distillation.** The safest replay text is general Spanish, Italian, German, French and English instruction or prose data whose answers Apertus 8B writes itself. Self-Distillation Fine-Tuning showed that targets close to the model's own distribution reduce forgetting ([Yang et al., ACL 2024](https://arxiv.org/abs/2402.13669)).
- **Base-then-merge.** StyleAdaptedLM trains a LoRA on unstructured style text with the *base* model, then adds it to the *instruct* weights. That cut the IFEval-strict loss to **5.1–8.8%**, against 12.7–18.6% for direct LoRA, with style close to direct fine-tuning ([Ramu et al.](https://arxiv.org/html/2507.18294v1)). Poets' text is unstructured, so this route fits PoesIA's data. It depends on an Apertus v1.5 8B base checkpoint that shares the instruct model's architecture and tokenizer, which still needs checking. That study's human evaluation used one copywriter.
- **Diversity-preserving loss.** GEM, an entropy-regularised SFT loss, matched cross-entropy downstream with "significantly higher output diversity", and "preserving diversity also appears to reduce forgetting" ([Li et al., ICLR 2025](https://arxiv.org/abs/2408.16673)).

Adapters should be trained fresh from the base or instruct weights, not stacked on earlier ones, because intruder dimensions accumulate across sequential fine-tunes ([Shuttleworth et al.](https://arxiv.org/abs/2410.21228)).

### Hyperparameters: MLP layers, a high-but-stable learning rate, few epochs

Both the peer-reviewed study and the Thinking Machines blog (not peer-reviewed) find that attention-only LoRA underperforms MLP-only or all-module LoRA. They also put the best LoRA learning rate at about **10×** the full fine-tuning rate: 2e-4 to 5e-4 on Llama-2-7B ([Biderman et al.](https://arxiv.org/html/2405.09673v2); [LoRA Without Regret](https://thinkingmachines.ai/blog/lora/)). LoRA also tolerates large batches poorly. More epochs and higher learning rates learn more and forget more.

From those sources, a reasonable setting for an 8B QLoRA on 2×T4 is:

- adapters on `gate/up/down` plus `q/k/v/o`;
- rank 16–64 with α = 2r;
- learning rate about 1e-4 to 2e-4, taking the highest that trains stably;
- one or two epochs;
- a small effective batch.

**These settings are inferred, not measured on creative text.** Held-out loss on poets' lines will stay high by nature, so it is the wrong stopping signal. A sense pass and a non-word rate, computed on the same held-out prompts every 500 steps, should decide when to stop. One hardware fact constrains everything: PoesIA trains in fp32 because Apertus overflows fp16 ([TUNING_ROUNDS §2](../../TUNING_ROUNDS_2026-10.md)). The usual QLoRA advice to use fp16 compute on a T4 therefore does not apply without a test.

### Distillation: the teacher writes requests and gates, humans write answers

Model collapse comes from **replacing** real data with generated data. **Accumulating** synthetic data alongside the real set avoided it across model sizes and architectures ([Gerstgrasser et al.](https://arxiv.org/abs/2404.01413)). In the OPT-125m experiment, keeping a random 10% of the original data each generation left "only minor degradation" ([Shumailov et al., Nature 2024](https://arxiv.org/html/2305.17493v3)). Both results come from wikitext or toy setups, not poetry.

The creative results that worked kept the **answers human** and used the teacher elsewhere:

- **The teacher writes the request.** Instruction backtranslation has a model write instructions for human text and then curate the pairs. It beat other LLaMA-based models on Alpaca "without using distillation data" ([Humpback, ICLR 2024](https://arxiv.org/abs/2308.06259)). Chakrabarty's author fine-tune also used teacher-written content descriptions over original excerpts.
- **The teacher gates the data.** Apertus 70B fits both roles. It can write stanza descriptions and plans for real poems (TUNING_ROUNDS' R3/R4 already plans this). It can also reject human targets that read as nonsense out of context: OCR damage, heavy ellipsis, broken archaic spellings.
- **Not as a source of verse.** Distilling 70B *verse* would import the stock signature of LLM poetry. GPT-4 used "echo" or "whisper" in 75% of its poems ([Walsh et al. 2024](https://arxiv.org/html/2410.15299)). And Apertus 70B behind the engine scored *worse* than the 8B on metre ([technical report](../../../../poesia-apertus/track_2b/technical_report.md)).

### Data curation: calibrate filters on poets, not on prose

Poetry-specific corpus filtering has one direct paper. Koziev detects spelling and grammar anomalies in Russian poem training data and releases the RUPOR test set ([arXiv 2505.04507](https://arxiv.org/abs/2505.04507)). Mareček's "known words" share, the fraction of words found in a lexicon, correlated **0.54** with expert overall impression, and 0.50 within human poems alone ([Mareček et al.](https://aclanthology.org/2025.eval4nlp-1.9)).

PoesIA has already shown how this goes wrong when the lexicon is too small. Its 40k-word list flags 9–21% of the *poets'* words, more than either model's, so it separates nothing ([TUNING_ROUNDS §1b](../../TUNING_ROUNDS_2026-10.md)). The working version needs a full inflected lexicon per language, such as a Hunspell dictionary, plus the corpus's proper nouns. It should be calibrated so that the 5th percentile of human poems sets the floor.

A perplexity filter must be two-sided. Very low perplexity under the 8B selects the conventional, cliché-prone lines the project is trying to leave behind, and only the high tail (noise, foreign fragments) is safe to cut. No study tests curriculum ordering or modern-versus-archaic filtering for poetry. On a single 5-hour run both rank below the unit and mixing fixes.

### Fine-tuning should teach style, not rhyme placement

The cross-language evidence on data scale is unambiguous. Rhyme is learned from examples only at very large scale:

- **ByGPT5** was trained on about **1.4M German and 660k English quatrains**. A 5% subset (33k quatrains) cost **15–40%** of rhyme adherence ([Belouadi & Eger, ACL 2023](https://arxiv.org/pdf/2212.10474)).
- **Fine-tuned Mistral-7B** reached a rhyming level of only 0.192 on Russian, against 0.683 for humans ([Koziev & Fenogenova 2025](https://aclanthology.org/2025.latechclfl-1.6.pdf)).
- **Per-line hints do more than data.** Adding syllable count and ending hints for each verse raised Czech rhyme-scheme accuracy from **49.6% to 89.8%** ([Chudoba & Rosa 2024](https://arxiv.org/abs/2407.12790)).

PoesIA's per-language pools are orders of magnitude smaller than ByGPT5's. The fine-tune should therefore target register, imagery and development, which are the gaps experts report in every language. Rhyme placement should stay with the engine, and the engine's per-line targets belong in every training prompt.

## Use preference tuning offline and on automatic pairs; RL last and short

### Offline methods match the signals PoesIA actually has

PoesIA has three signals: a deterministic form engine, a binary 70B sense verdict, and embedding measures of repetition and novelty. It also has very few owner labels. That mix favours offline methods.

**KTO** learns from unpaired desirable or undesirable labels. It matched or beat DPO from 1B to 30B and tolerated imbalance between the two classes ([Ethayarajh et al., ICML 2024](https://arxiv.org/abs/2402.01306); abstract-level). That is the shape of a one-word verdict that cannot rank. **DivPO** builds pairs from a rare-but-good chosen response and a common-but-weak rejected one, and raised story diversity by up to **74.6%** at similar win rates ([DivPO](https://arxiv.org/abs/2501.18101v4)). **Deviation-weighted DPO** weights pairs by embedding deviation, but it needs more than three, ideally four or five, responses per prompt ([Chung et al.](https://arxiv.org/html/2503.17126v1)). **ORPO** and **SimPO** need no reference model, which saves T4 memory. On general chat, ORPO, KTO and SimPO land within a fraction of a point of each other (MT-Bench 8.93 / 8.78 / 8.98) ([arXiv 2506.03690](https://arxiv.org/pdf/2506.03690)). None of these has been tested on poetry.

The research notes infer a pair recipe ([research note](../research_notes/Improving%20PoesIA%20poetry%20models/rl_and_preference.md)):

1. Sample 8–16 candidates per request from the adopted SFT model.
2. Hard-filter them with the engine.
3. Run the 70B veto.
4. Score repetition (inter-line cosine) and novelty (distance from the other candidates and from earlier outputs).
5. Pick the *chosen* response from the form-valid, sense-OK, low-repetition, higher-novelty candidates.

*Rejected* responses come in two kinds, which should be tracked as separate subsets. Form failures teach form. Valid but typical, repetitive candidates teach development. Form-fail pairs are deterministic, and DPO can overfit such pairs because the implied reward gap grows without bound ([IPO, Azar et al.](https://arxiv.org/abs/2310.12036)). They therefore call for IPO or a capped β.

Sampling for offline pairs can use a frozen model on any server. On-policy RL cannot, so offline pairs are also the cheaper route.

### Owner pairs calibrate the automatic rule; they cannot train it yet

The smallest creative preference datasets with published results are tens of thousands of comparisons. DDPO used about 95.8k prompts, and LitBench and WQRM used thousands of pairs ([research note](../research_notes/Improving%20PoesIA%20poetry%20models/rl_and_preference.md)). Fifty to three hundred owner pairs fall far below that.

Their value is as a check. They test whether the automatic chosen/rejected rule agrees with Angel (reported with an interval), choose β and checkpoints, and serve as the final acceptance test. They should go into training only as a small, upweighted slice, and only after the rule is shown to agree with him.

Preference data also carries a typicality bias: annotators prefer familiar text. Verbalized Sampling names this as a cause of mode collapse ([Zhang et al.](https://arxiv.org/pdf/2510.01171v1)). DivPO's pairing counters it directly.

### RL with verifiable rewards: what one rhyme study saw

There is little direct evidence for poetry RL. The one peer-reviewed GRPO rhyme study read in full is Ogawa & Kawahara (ACL 2026 SRW): Japanese rap, a 3B policy, rollout n = 4, learning rate 5e-7, best checkpoint at 0.3 epoch. On 100 held-out themes it found:

- **Rhyme length did not change** (2.390 → 2.380).
- **The share of outputs with low repetition rose** from 47% to 64%.
- **Collapsed outputs rose from 2 to 17 of 100.** At higher learning rates the model "degenerated into repetitive generations largely independent of the prompt".

The authors' own reading is "a change in the quality distribution rather than a uniform improvement". They warn that rhyme metrics mislead because repeating a phrase matches vowels perfectly. They chose checkpoints by low format collapse and preserved diversity, not by total reward, and their stated next step is DPO on scored candidates ([Ogawa & Kawahara](https://aclanthology.org/2026.acl-srw.27.pdf)). A Tang-poetry GRPO paper exists, but its full text could not be verified ([npj Heritage Science](https://www.nature.com/articles/s40494-025-02087-x)). No GRPO study with syllable or metre rewards in a European language was found.

### Creative-writing RL that works gates the reward instead of summing it

Creative-writing RL that reports human-evaluated gains combines a constraint verifier with a quality model. **RLMR** gives constraint-violating samples **negative advantage** inside GRPO and reports a **72.75%** expert win rate across 8B–72B models ([arXiv 2508.18642](https://arxiv.org/abs/2508.18642)). **Writing-Zero** replaces scalar reward models with a pairwise generative judge, arguing that scalar models invite "over-explanation and length bias" ([arXiv 2506.00103](https://arxiv.org/abs/2506.00103)). For PoesIA this means four design rules:

- **Gate, don't sum.** A form failure gets a fixed negative reward. Sense, repetition and novelty terms only rank form-valid candidates, and they are multiplied by both the form gate and the 70B veto, so novel nonsense scores zero.
- **Penalise identity rhymes.** Every rhyme reward needs a term against identical rhyme words and rhymes made by repeated morphology (-ción/-ción, -mente/-mente).
- **Fix the loss settings.** Use TRL's `dr_grpo` or `dapo` loss, which avoid the length bias of the per-sequence normalisation ([Dr. GRPO](https://arxiv.org/abs/2503.20783)). Use a small non-zero β, because TRL's default is β = 0, with no KL anchor at all ([TRL docs](https://huggingface.co/docs/trl/main/en/grpo_trainer)).
- **Check the judge for length bias.** The open 70B judge closest to Apertus in a 2026 bias study, Llama-3.3-70B, shifted **+0.44** toward length-expanded answers ([arXiv 2604.23178](https://arxiv.org/pdf/2604.23178)). Fixed forms limit how much length can vary, but this still needs checking for Apertus.

### Compute decides the unit

Memory is not the obstacle. Unsloth's rule of thumb puts 4-bit GRPO at about one GB of VRAM per billion parameters, and it publishes a Kaggle notebook for Llama 3.1 8B with vLLM. vLLM supports the T4's compute capability 7.5 ([Unsloth](https://unsloth.ai/docs/basics/reinforcement-learning-rl-guide); [vLLM](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html)). **Time is.**

At PoesIA's measured ~45 tokens/s per GPU, my rough budget arithmetic gives:

- **Whole poem.** A sonnet is about 200 tokens. A group of eight takes about 35 s to generate, or roughly a minute per step with training and judging, which leaves about 300 steps in 5 hours. That only just meets Unsloth's guidance of "at least 300 steps".
- **Couplet.** About 30 tokens. A group of eight takes about 5 s, leaving 1,000–2,000 steps.

GRPO, if it is tried at all, belongs at the couplet. The reward there is dense, and the 70B veto is reliable at that length. Rollouts from an external server that never receives the new weights are off-policy. That breaks GRPO but suits the offline pairs above. Two things need a 20-minute smoke test before any 5-hour run: whether vLLM on a T4 accepts LoRA weight sync for Apertus's architecture, and whether it runs in a precision Apertus does not overflow.

## Plan the stanza, let the model pick the rhyme word, repair minimally

### Hard constraints buy form at a measured cost in fluency

The decoding literature quantifies the form–fluency trade:

- **FUDGE.** On Shakespeare couplet completion, adding future discriminators for metre, rhyme and sentence end raised full success from **0 to 44%** (Shakespeare himself scored 45% under the same narrow checker). Perplexity rose from **44 to 71** ([Yang & Klein, NAACL 2021](https://arxiv.org/pdf/2104.05218v2)).
- **Lyra.** Hard rhythm constraints raised stress alignment to 89.5% but pushed perplexity from 85 to 108. The soft constraint got the best human quality ratings ([Tian et al., ACL 2023](https://arxiv.org/abs/2305.19228)).
- **NeuroLogic A\*esque.** Coverage is easy and fluency at equal coverage is the hard part. All constrained decoders reached about 97% keyword coverage, but only lookahead raised human ratings (2.50 → 2.70) ([Lu et al., NAACL 2022](https://aclanthology.org/2022.naacl-main.57.pdf)).
- **Grammar-constrained decoding.** It "can distort the LLM's distribution", producing outputs at likelihoods out of proportion to what the model assigns them ([Park et al., NeurIPS 2024](https://arxiv.org/abs/2405.21047)).

That last result is the mechanism behind lines like "Silence drifts like an abril". A forced end word is sampled no matter how implausible it is in context.

The decoding fix that follows is a one-step lookahead on rhyme words:

1. Have the model propose 5–10 end words per rhyme slot from its stanza plan.
2. Keep those that pass the deterministic rhyme key and are not near-copies by lemma.
3. Rank them by the 8B's log-probability of the word, or of a line ending in it, given the stanza so far. llama.cpp exposes these log-probabilities.
4. Write the line toward the winner.

The bank becomes a fallback and a filter. This rests on Ou et al.'s finding that biased decoding swaps end words without regard to context, and on interpretability evidence that models plan end words at the newline ([Anthropic 2025](https://transformer-circuits.pub/2025/attribution-graphs/biology.html)). It has not been tested on poems. GBNF grammars should keep only structural jobs: line count, one line per newline, no prose preamble.

### Plans drive development; budgets are enforced per line

Every lyric or poetry system with a strong human evaluation plans first:

- **Lyra's keyword plan** gave a 24% relative gain in overall quality ([Tian et al.](https://arxiv.org/abs/2305.19228)).
- **Reffly's structure plan** scored structural clarity 3.36 against GPT-4's 1.15 ([arXiv 2409.00292](https://arxiv.org/abs/2409.00292)).
- **Chae et al.'s song model** shows where budgets must live: syllable error is 2.85% at line level but 68.8% at paragraph level ([arXiv 2411.13100](https://arxiv.org/abs/2411.13100)). Syllable budgets therefore belong on each line, never on the stanza.

PoesIA's "restates instead of develops" failure is a missing content plan. A poem plan with stanza roles (image, turn, consequence, close), one concrete image per stanza and a list of words banned from repetition costs one extra call. It also maps onto Angel's criteria: a gist, and a strong ending ([POETICS #10](../../POETICS.md)).

### Reranking: larger judges, progression terms, no plain MBR

Candidate selection is where most of the measured gain sits. In Reffly, removing the selection step dropped the match rate from **0.82 to 0.51**. PoeLM's unconditioned fluency rerank lifted human preference against layman poems from 39.3% to 42.7% ([PoeLM](https://arxiv.org/pdf/2205.12206)).

Three upgrades to PoesIA's eight-candidate ranker follow:

- **A semantic-progression term**: centred cosine to earlier lines and stanzas, penalised.
- **The end-word plausibility term** above.
- **A judge larger than the generator.** Llama3-8B as a self-judge "often gave all stories about 7/9", while Llama3-70B agreed with a human more than 70% of the time ([Olson et al.](https://arxiv.org/html/2412.06060)).

Plain MBR should not choose the final poem. Its consensus utility picks the most typical candidate, and no creative-writing MBR study exists. Diverse MBR can choose a *varied set* to show the user, at O(N²) cost ([Jinnai et al.](https://arxiv.org/html/2401.05054v1)).

### Sampling and repetition control

No sampler has a human-evaluated win on poetry:

- **Min-p.** A reanalysis found its claimed gains did not hold up ([Schaeffer et al.](https://arxiv.org/abs/2506.13681)).
- **Newer truncation samplers** are supported mainly by LLM judges.
- **DoLa** targets factuality.
- **Contrastive decoding** needs a smaller same-tokenizer "amateur" model, and no Apertus v1.5 sibling has been verified.

Aligned models "favor pleasant writing over creative originality" ([West & Potts](https://arxiv.org/abs/2505.00047)), so the levers that matter act on what has already been said. Candidates include:

- a stanza-wide n-gram or lemma penalty (DRY or a repetition penalty applied across the poem, not just the line);
- an Avoidance-Decoding-style penalty against earlier stanzas, reported at 2.6× diversity and about 30% less repetition in stories ([Park, Yang & Jung, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.381/));
- a ban on reused end words.

All of them must leave required repeats, such as a refrain, intact. Verbalized Sampling raised human-rated poem dissimilarity from **1.90 to 2.39** (1–4 scale). Its standard variant cost quality on small models, so the VS-CoT variant suits an 8B ([Zhang et al.](https://arxiv.org/html/2510.01171)). A temperature schedule is plausible but unmeasured: higher when planning and proposing end words, lower when writing a line toward a fixed word.

### Refinement keeps sense only with external defects and minimal edits

Repair works when an external checker names the exact defect: the Greek loop went from under 4% to **73.1%** valid ([Chatzikyriakidis & Natsina 2026](https://aclanthology.org/2026.latechclfl-1.9.pdf)). Self-correction without such a signal often fails ([Huang et al.](https://arxiv.org/abs/2310.01798)). Iterative form refinement in German sonnet translation bought form at the cost of grammaticality and meaning ([Klumpp 2026](https://aclanthology.org/2026.latechclfl-1.18/)).

PoesIA's repair prompt should therefore:

- show the whole stanza and its plan, not just the failing line;
- ask for the fewest changed words;
- reject a repair whose embedding similarity to the original falls below a threshold (Reffly's BERTScore tie-break is the precedent);
- offer to repair the *partner* line when a rhyme fails, which forced single-line repair cannot do.

A related result from Hebrew free verse: principle-level critiques (no clichés, original metaphor), developed over 14 workshop sessions with GPT-4, brought readers to chance at telling its poems from human ones (52% vs 54% judged human). The same model still failed classical metre and rhyme ([Tohar et al.](https://arxiv.org/html/2602.16578v1)). Turning such principles into a fixed checklist is untested at 8B.

**Activation steering** is a research bet. It was shown on Llama3-8B with a single layer-8 vector, judged only by an LLM, and with no measured quality trade-off ([Olson et al.](https://arxiv.org/html/2412.06060)). It also cannot run on the OpenAI-compatible API path.

## Measure each level with validated instruments; the owner settles only large gaps

### What the automatic instruments can and cannot do

Mareček et al. give the only per-metric validity table for poetry: 100 Czech poems rated by three experts. Correlation with expert overall impression:

- **Human-rated meaning dominates**: semantics **0.90**, syntax **0.87**.
- **Human-rated form barely registers**: metre 0.16, rhyme 0.28.
- **The best automatic predictors** are an LLM semantics score (0.59) and the known-words share (0.54).
- **LLM-rated "metre" and "rhyme"** are a halo of meaningfulness. They correlate only 0.17 and 0.21 with the human form ratings.

The decisive detail for PoesIA is in their Table 3. **The LLM's semantics score correlates 0.69 with experts on generated poems but 0.26 within human poems.** The judge works only across a wide quality range ([Mareček et al.](https://aclanthology.org/2025.eval4nlp-1.9)).

PoesIA's Apertus 70B shows exactly this profile. It passes 90% of real lines and 8% of shuffled ones, and it passes the plain 8B's lines as often as poets' lines ([TUNING_ROUNDS §1a](../../TUNING_ROUNDS_2026-10.md)). It can say "not worse than competent". It cannot say "better". The adoption rule's demand that an adapter be "better on sense" therefore cannot be met by this instrument. It needs the owner, or a harder instrument.

Two mechanisms could make a same-family judge favour the 8B:

- **Familiarity.** Judges reward low-perplexity text regardless of source ([Wataoka et al.](https://arxiv.org/abs/2410.21819)).
- **Labels.** In a constraint-selection task, self-preference disappeared under blind evaluation ([Chae et al. 2026](https://arxiv.org/abs/2608.18091)).

Judges also favour *similar* models, not only themselves ([Goel et al., ICML 2025](https://arxiv.org/abs/2502.04313)). PoesIA can test the familiarity account cheaply. Log the 70B's per-token log-probability for each line, then compare pass rates for poet lines and 8B lines inside matched perplexity bins.

### Harder controls and per-language grammar gates

The real-versus-shuffled control is the easy case. Laban et al. showed that a fine-tuned model saturates the global shuffle test at 97.8%. On block shuffles, models fell from 94% to 78% while humans stayed near 95% ([Laban et al., ACL 2021](https://aclanthology.org/2021.acl-short.134/)).

Any sense or development instrument should therefore also be tested on three harder negatives:

- a line swapped within its own poem;
- a line swapped with a metre- and rhyme-matched line from another poem;
- stanzas in shuffled order.

A stanza-order discriminator trained on human poems also gives a direct **development score**. A poem whose stanzas could come in any order sits at chance, which is the "list of images, no arc" failure.

For grammar, acceptability classifiers exist but are weak outside English and Italian. On MELA, supervised XLM-R scored MCC 60.6 (en), 53.5 (it), 34.1 (es), 26.7 (de) and 19.0 (fr). GPT-4o two-shot reached 61.4 in Spanish ([MELA](https://arxiv.org/html/2311.09033v3)). Spanish has EsCoLA, with 11,174 labelled sentences ([Bel et al. 2024](https://aclanthology.org/2024.lrec-main.554)). Italian matters most here, because the 70B rejects 40% of real Italian lines and cannot gate Italian at all. An ItaCoLA-trained classifier is the obvious candidate. It should be scored at sentence level, joining enjambed lines, and calibrated so that human poems' 5th percentile sets the floor. No acceptability, grammar-correction or coherence tool has been validated on verse in any language.

### One rater, few pairs: design for the power that exists

A single expert's absolute rating of a poem is noisy. From Kaufman et al.'s expert reliability (α = 0.832 over 10 poets), my Spearman-Brown estimate of one rater's reliability is about **0.3**. The same study found lay and expert ratings correlated only **r = 0.216** ([Kaufman et al. 2008](https://doi.org/10.1080/10400410802059929)).

Relative formats need less effort for the same reliability:

- **Best-worst scaling** matched rating-scale reliability with **30%** of the annotations ([Kiritchenko & Mohammad](https://arxiv.org/abs/1712.01765)).
- **RankME** raised the intraclass correlation (ICC) for quality from 0.41 to 0.68 ([Novikova et al.](https://aclanthology.org/N18-2012/)).

With an exact sign test at α = 0.05, 40 decisive pairs detect a 75% preference with 90% power, but a 65% preference only 44% of the time. A few dozen pairs therefore settle only large gaps ([research note](../research_notes/Improving%20PoesIA%20poetry%20models/evaluation.md)).

Combining the owner's pairs with judge verdicts through prediction-powered inference keeps the intervals valid ([Angelopoulos et al., Science 2023](https://arxiv.org/abs/2301.09633)). The gain is bounded, though. When the judge is no more accurate than the model it judges, no method saves more than half the human labels ([Dorner et al., ICLR 2025](https://arxiv.org/abs/2410.13341)). By the notes' 1/(1 − ρ²) rule, a judge at Mareček's ρ ≈ 0.6 stretches the owner's pairs by about 1.5×, not 10×.

Owner sessions should therefore:

- use best-worst choices over sets of four;
- spend most judgements on comparisons the instruments are unsure about;
- keep about 20% of judgements on wide-gap pairs, to validate the instruments;
- report every result with its interval, as "not decided" whenever the interval crosses 50%.

| Level | Instrument with external support | Status on PoesIA |
|---|---|---|
| Line | metre counter (es 93.5% vs expert scansion); inflected-lexicon non-word rate; acceptability classifier at sentence level; 70B veto | metre validated; 40k list failed; classifier untested; veto works es/de/fr, not it |
| Rhyme pair | phonetic rhyme key with identity and morphology rejection; share of rhyme words from the bank vs poets' share; matched-swap control | key validated; "rhyme earned" measure defined, not validated |
| Stanza | centred redundancy; repeated content words; local-swap control | redundancy separates 8B from humans; controls not yet run |
| Whole poem | consecutive-stanza restatement; stanza-order discriminator; theme fit (centred, poem level, AUC 0.93); owner best-worst choices | restatement measured; order discriminator not built; owner protocol not run |

## Per language, form came from engines and meaning stayed the gap

Across five languages and eight years of work, the pattern is the same. **Form correctness came from explicit per-line targets plus an external checker and selection, and the remaining human-judged gap is meaning, cohesion and imagery.** No study fine-tunes an open 7–8B multilingual model on metrical verse in several of these languages. Nor does any compare decoding-time constraints with fine-tuning on the same model and language.

| Language | Best-measured system | What worked | What failed or is missing | PoesIA v3 signal |
|---|---|---|---|---|
| Spanish | PoeLM (760M, trained on prose with structure codes, k = 3,000 samples per poem); The Tiny Poet (117M GPT-2, 5,262 poems, backtracking) | 30.9% of candidates valid; preferred over an expert poet's stanza 37.3% of the time ([PoeLM](https://arxiv.org/pdf/2205.12206)) | Tiny Poet "may lack of cohesion and meaning"; annotator κ 0.2153 ([Stoia et al. 2025](http://journal.sepln.org/sepln/ojs/ojs/index.php/pln/article/download/6684/4075)); no LLM metre study | metre 86 → 93%, sense 93 → 68% |
| Italian | Zugarini et al. 2019 (syllable LSTM, 2,000-candidate scoring) | rhyme acceptable to experts (3.37 vs Dante's 4.50) | metre 1.90 vs 4.45, likely because accent positions were not scored ([arXiv 1908.08861](https://ar5iv.labs.arxiv.org/html/1908.08861)); no LLM study | metre 83 → 96%, rhyme 49 → 68%; judge unusable |
| German | ByGPT5 (byte-level, 1.4M quatrains) | beat GPT-2 on rhyme by 5–20%; preferred over ChatGPT on rhyme scheme in 85% of pairs ([ByGPT5](https://arxiv.org/pdf/2212.10474)) | all models under-diverse, LLaMA-3-8B included ([Chen et al. 2024](https://arxiv.org/html/2406.15267v2)); refinement costs grammar ([Klumpp 2026](https://aclanthology.org/2026.latechclfl-1.18/)) | openings collapsed 0.36 → 0.20; sense 91 → 64% |
| French | Van de Cruys 2020 (2,000-candidate scoring, topic prior) | adding a topic constraint lifted meaningfulness to 3.55 | rhyme alone *lowered* meaningfulness 2.59 → 2.18 ([ACL 2020](https://aclanthology.org/2020.acl-main.223.pdf)); no alexandrine accuracy for any neural model | metre 90 → 87% (143-poem pool); sense held |
| English | Zest (planning plus constrained decoding) | 100% rhyme, 75.6% metre ([Tian & Peng 2022](https://ar5iv.labs.arxiv.org/html/2205.01821)) | chat-LLM tics ("echo", "whisper") ([Walsh et al.](https://arxiv.org/html/2410.15299)); best LLM 3.20 vs human 4.22 overall ([POEMetric](https://arxiv.org/abs/2604.03695)) | not in the v3 table |

Three lessons transfer to PoesIA.

- **Pair every rhyme constraint with a content constraint.** Van de Cruys's French result is the clearest data point: rhyme alone cost meaning, and rhyme plus topic recovered it.
- **The Italian checker must score accents, not only syllable counts.** The endecasillabo needs stresses on the 6th and 10th, or the 4th, 8th and 10th, syllables, and the one Italian generator failed on exactly that.
- **Small pools carry the most risk.** German's pool (DLK, uniform 19th-century verse) and French's (143 poems) are where v3 lost openings and metre. These two languages need either more data under the caps, or a lower weight in the mixed adapter, before the next run.

## Ordered experiments, cheapest and best-evidenced first

Each step runs on the seeded benchmark, against both the plain model and the current best, and is read on all four levels. The table says what decides each step, what the evidence establishes, and what is only inferred. The "≥" thresholds below are working proposals, not results from the literature.

| # | Experiment | Cost | Adopt if (deciding measure) | Known | Inferred |
|---|---|---|---|---|---|
| 1 | Temperature and min-p/top-p sweep on v3 (T = 0.5 / 0.7 / 0.9) and on the plain model | inference only | sense pass for es/de closed lines moves toward the plain model's 94%/91%, while stanza restatement stays ≤ 0.45 and repetition stays at v3 levels | v3 was sampled at 0.9; the closed-line deficit is the larger cause | over-dispersion is the mechanism (shown on other data only) |
| 2 | Count enjambed v3 targets; check judge controls: local swap, matched swap, stanza shuffle, perplexity-binned familiarity | CPU and 70B calls | the instrument separates each control pair, or is dropped for that use (TUNING_ROUNDS rule) | global shuffle saturates; LLM sense judges are range-restricted | harder negatives will expose what the 70B cannot rank |
| 3 | Decoding on the plain model: poem-wide repetition and end-word reuse penalties; semantic-progression term in the ranker | inference only | content words repeated per poem and pair restatement fall toward the human range with no drop in sense pass | repetition penalties cut story repetition about 30%; ranker selection carries most gains | that this carries over to verse and to Apertus |
| 4 | v4 SFT: clause-complete targets, otherwise same data and caps; MLP and attention LoRA, 1 epoch, sense checked every 500 steps | one Kaggle run | sense pass ≥ plain minus 5 points in es and de; v3's development and repetition gains kept | truncated targets teach fragments; open lines pass 57% | the pretraining result carries over to short SFT targets |
| 5 | v4 plus 10–20% self-distilled general replay (Apertus 8B's own answers) | one Kaggle run | closes more of the closed-line gap than #4 | replay of 1% stops pretraining-loss forgetting; general skills plateau near 1k samples | that the ratio and the sense metric behave the same way for verse |
| 6 | Stanza plan, model-proposed end words checked by the key and ranked by 8B log-probability, minimal-edit stanza repair | inference only | bank-word share of rhyme lines drops toward the poets' share; rhyme-line sense pass rises; owner prefers it in a best-worst session | forced words distort the distribution; plans lift human ratings for lyrics and stories | model-chosen words beat bank words on sense for poems |
| 7 | Base-then-merge style adapter on raw stanzas (if an Apertus base checkpoint matches the instruct model) | one Kaggle run | style metrics like #4 with smaller sense and format loss | IFEval loss 5–9% vs 13–19% for direct LoRA at 7–8B | the same holds for verse and for Apertus |
| 8 | Owner best-worst sessions (40–60 judgements) on the winners of #1–#7 | owner time | interval excludes 50% | one rater settles only gaps of about 75% or more | that the owner's choices agree with any automatic sense score |
| 9 | Offline KTO or DivPO-style pairs from 8–16 samples per request; IPO or capped β for form-fail pairs | one or two Kaggle runs | beats the adopted SFT model on diversity and the four-level scorecard, sense not worse, owner agreement with the automatic rule ≥ wide-gap stratum | DivPO raises diversity at similar quality; KTO matches DPO on general tasks | that a binary 70B verdict works as a KTO signal for poetry |
| 10 | Couplet GRPO with a gated reward (form gate gives negative advantage, sense veto, anti-identity rhyme term, diversity multiplied by both gates); `dr_grpo`, small β, vLLM on the second T4 after a 20-minute smoke test | several Kaggle runs | beats #9 at couplet level with no rise in the collapse rate on held-out prompts | rhyme GRPO shifted the distribution and raised collapse 2 → 17/100 | that it fits T4 time and precision for Apertus |

Several options are deliberately left out: plain MBR as the final selector, activation steering, contrastive decoding, switching tokenizers for rhyme, whole-poem GRPO, self-play, and teacher-written verse as main training data. Each either lacks evidence, works against originality, or does not fit the compute.

## Conclusion

This research changes the diagnosis. v3 was framed as "fine-tuning on poets costs sense", but the sense loss turns out to be mostly a word-choice and sampling problem inside complete lines, not an enjambment problem. That makes the cheapest test the most informative one, and it can run today on the existing adapter. It also explains why the literature's form-first systems in every language ended up with the same verdict from experts, "valid but lacking meaning". The levers that move meaning are a content plan, a rhyme word the model can actually reach, a training mix that keeps the model's own fluency, and a selector that does not reward typicality. Constraints and rewards on form do not move it.

The second change concerns what "better" can mean for PoesIA. With a same-family judge that saturates on competent lines and one owner who can settle only large preferences, an adapter that is slightly better in sense cannot be detected, only one that is no worse. The practical consequences are concrete. Build the harder controls and the per-language grammar gates before trusting any small sense gain. Spend owner judgements where the instruments disagree. Treat every RL or preference method as a way to shift the distribution, as the one rhyme-GRPO study observed, and check it on collapse and diversity before reading its reward.

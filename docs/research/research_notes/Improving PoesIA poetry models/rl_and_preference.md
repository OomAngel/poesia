# RL and preference optimisation for constrained poetry generation (PoesIA, Apertus 8B, 2x T4)

Scope: which RL and preference methods could improve PoesIA poems at line, rhyme-pair, stanza and whole-poem level on a Kaggle 2x T4 budget with an Apertus 70B judge, and how to avoid reward hacking. All URLs accessed 2026-10-16. "(nr)" = a well-known paper not re-fetched this session: the arXiv id and headline claim are stable, but check exact numbers in the PDF before publishing them. This file does not repeat the evidence already in `poesia-calaveritas/docs/research/research_notes/PoesIA shared poem quality layer/training_and_generation_strategies.md` (DivPO, DDPO/DORPO, CrPO, Verbalized Sampling, WQRM, LitBench, PoeLM, min-p). It points to that file where those papers bear on a question here.

Measured results vs claims: "measured" means numbers reported in the paper's experiments. "Claim" means an abstract-level or documentation statement whose numbers were not verified here.

## Q1. RL with verifiable rewards (GRPO, RLOO, PPO, DAPO) for constrained generation: results, reward design, reward hacking, compute

### Takeaway
There is very little direct evidence for poetry. The one peer-reviewed GRPO paper on rhyme with a full text read this session (Japanese rap, 3B model, ACL 2026 SRW) found a small gain: GRPO **shifted the distribution** (more good outputs *and* more collapsed ones, 17/100 vs 2/100) rather than raising the mean. Collapse into repetitive, prompt-independent gibberish appeared whenever the learning rate was large enough to move the reward fast. Creative-writing RL that works at scale (RLMR, Writing-Zero) combines a **hard constraint verifier** with a **learned/generative quality reward**, and treats constraint violations as negative advantage instead of adding them to the score. The GRPO variants (Dr. GRPO, DAPO) mainly fix length and normalisation biases. Those biases matter for PoesIA because a length bias interacts with poem length.

### Cited Findings

**Poetry/lyrics RL with a rule-based reward (measured)**
- Japanese rap, GRPO on Sarashina2.2-3B (first given continued pre-training on 36,766 synthetic rhyming two-bar pairs made with Mistral-Small-3.1-24B). The reward is a weighted sum R = Σ w_k r_k over {format, num_bars, len_range, len_balance} (weight 1.0 each, values ±1) and {rhyme, penalty} (weight 4.0). r_rhyme = 1 − normalised position-weighted vowel/moraic-nasal edit distance over the last ≤5 morae, with phonetically graded vowel substitution costs. r_penalty = −Jaccard(char sets of the last 5 surface characters) "to prevent the model from obtaining a high r_rhyme by simply repeating the same ending expression" — [Ogawa & Kawahara, ACL 2026 SRW, pp. 340–351](https://aclanthology.org/2026.acl-srw.27/) ([PDF](https://aclanthology.org/2026.acl-srw.27.pdf))
- Same paper, compute and hyperparameters: 8 GPUs data-parallel (ABCI 3.0), global batch 16, **rollout samples n = 4**, temperature 0.9, KL coefficient 0.001, entropy coefficient 0. Learning-rate sweep {2e-6, 1e-6, 5e-7}. The selected checkpoint was step 117 (0.3 epoch) at lr 5e-7. Themes: 8,921 words, split 7:2:1 at theme level — [PDF, §3.3.2 and Table 4](https://aclanthology.org/2026.acl-srw.27.pdf)
- Same paper, reward hacking/collapse: "With larger learning rates, the total reward sometimes increased temporarily; however, we also observed output collapse ... where the model degenerated into repetitive generations largely independent of the prompt" (e.g. "Kogetokutokutokutokutoku"). The authors therefore **did not select checkpoints by total reward**. They selected on (i) minimal format collapse, (ii) no extreme loss of diversity, (iii) rising rhyme reward. They also state that automatic rhyme metrics mislead because "repeating the same phrase allows the vowel sequences at the ends of the two bars to match perfectly" — [PDF §3.3.2, §4.1](https://aclanthology.org/2026.acl-srw.27.pdf)
- Same paper, results (100 held-out themes, 3 raters in their twenties who listen to Japanese rap, 5-point scales). Mean rhyme length 2.390 → 2.380 (no change). Low repetition 2.957 → 3.073. Unpredictability 2.083 → 2.177. Share of outputs scoring ≥3: low repetition 47% → 64%, unpredictability 9% → 22%. **Collapsed outputs 2 → 17 of 100**. The authors' own reading: "a change in the quality distribution rather than a uniform improvement", and "training stability remains a major challenge". Their proposed next step is to use the GRPO model to generate scored candidates for **DPO/PPO** — [PDF §4.3, §5](https://aclanthology.org/2026.acl-srw.27.pdf)
- A GRPO study on classical Chinese (Tang) regulated verse with a multi-part reward (tones, rhyme, parallelism, word count) is reported in npj Heritage Science 2025 ("Large language models learning to write rhyming Tang poetry: A Xunzi Yayun R1 case study"). The search snippet gives a GRPO total score of 83.25 (tone 77.74, rhyme 77.36). The full text was paywalled/redirected and **not verified**, so treat it as a lead only — [npj Heritage Science, s40494-025-02087-x](https://www.nature.com/articles/s40494-025-02087-x). A second search for it found nothing more.
- Older poetry RL: "Generate and Revise" casts poem revision toward a target meter/rhyme scheme as an RL (PPO) task — [Zugarini et al., arXiv 2102.04114](https://arxiv.org/pdf/2102.04114) (nr). A Greek rhyme paper proposes RL from phonological feedback only as future work — [arXiv 2601.09631](https://arxiv.org/html/2601.09631v4)
- No 2025–2026 arXiv paper was found that applies GRPO with explicit syllable/metre rewards to European-language poetry (two searches, one extended). See Gaps.

**Creative-writing RL with mixed rewards (measured, abstract level)**
- RLMR combines a **writing reward model** (subjective quality) with a **constraint verification model** (format, word limits) inside GRPO. The constraint weight is adjusted dynamically from writing quality within each sampled group, and "samples that violate constraints receive negative advantage". Across 8B–72B models: IFEval 83.36% → 86.65%, and a **72.75% win rate** in expert pairwise human evaluation on their WriteEval benchmark (sample size not on the abstract page; language not stated) — [RLMR, arXiv 2508.18642](https://arxiv.org/abs/2508.18642)
- Writing-Zero argues that scalar reward models trained on preferences "are prone to reward hacking, such as over-explanation and length bias". It replaces them with a **pairwise generative reward model** using writing principles and "self-principled critique". Its BRPO algorithm uses a bootstrapped response from the same rollout group as the comparison reference, and it trains without SFT. The claim is better resistance to reward hacking than scalar-RM baselines (numbers not on the abstract page) — [Writing-Zero, arXiv 2506.00103](https://arxiv.org/abs/2506.00103)
- Seed1.5-Thinking used a pairwise generative RM (scored by P("YES") vs P("NO")) for non-verifiable tasks and reports more stable RL when verifiable and non-verifiable data are mixed — [arXiv 2504.13914](https://arxiv.org/pdf/2504.13914) (abstract-level via search; nr)
- IP-GRM (ICML 2026 poster) generates evaluation principles from the question alone before scoring the response, and claims this suppresses reward hacking in GRPO on creative writing — [ICML 2026 listing](https://icml.cc/virtual/2026/poster/63602) (not read in full)

**GRPO-family algorithm facts that matter for poem length**
- GRPO (group-relative advantages without a value model) was introduced in DeepSeekMath — [Shao et al., arXiv 2402.03300](https://arxiv.org/abs/2402.03300) (nr). RLOO (leave-one-out REINFORCE) matched or beat PPO in RLHF with fewer models in memory — [Ahmadian et al., ACL 2024, arXiv 2402.14740](https://arxiv.org/abs/2402.14740) (nr)
- Dr. GRPO: GRPO has an "optimization bias" that "artificially increases response length (especially for incorrect outputs)". The unbiased variant improves token efficiency (43.3% AIME 2024 with a 7B base) — [Liu et al., arXiv 2503.20783](https://arxiv.org/abs/2503.20783)
- DAPO adds clip-higher, dynamic sampling (drops groups with all-equal rewards), a token-level loss and overlong reward shaping — [Yu et al., arXiv 2503.14476](https://arxiv.org/abs/2503.14476) (nr)
- TRL implements these as `loss_type` values: "grpo" (per-sequence 1/|o_i| normalisation, which "introduces a response-level length bias"), "dapo" (token-level, the default) and "dr_grpo" (divide by a constant, recommended = max completion length). The default **β (KL) = 0.0** ("the KL divergence term is not used"; 0.001 is cited as DeepSeek-R1's value). Default num_generations = 8. `scale_rewards` = "group" (default), "batch" or False. Multiple reward functions are summed, or weighted by `reward_weights`. Default `multi_objective_aggregation` = "sum_then_normalize" — [TRL GRPOTrainer docs](https://huggingface.co/docs/trl/main/en/grpo_trainer)
- RLVR narrows exploration: RL-trained models win at pass@1, but base models have higher pass@k at large k, i.e. RL sharpens the distribution rather than adding new capability — [Yue et al., arXiv 2504.13837](https://arxiv.org/abs/2504.13837) (nr). This is the same diversity-narrowing pattern the earlier notes document for DPO/RLHF in creative writing.

**General reward-hacking evidence**
- Proxy reward over-optimisation: gold quality rises then falls as optimisation pressure (best-of-n or RL KL distance) grows — [Gao, Schulman & Hilton, arXiv 2210.10760](https://arxiv.org/abs/2210.10760) (nr)
- Much of the measured RLHF "improvement" can come from length: optimising for length alone reproduced most of the reward gains in their settings — [Singhal et al., "A Long Way to Go", arXiv 2310.03716](https://arxiv.org/abs/2310.03716) (nr)
- Spurious or random rewards improved Qwen2.5-Math with RLVR but not other model families, a warning that "reward went up" can reflect model priors rather than the reward — [Shao et al., "Spurious Rewards", arXiv 2506.10947](https://arxiv.org/abs/2506.10947) (nr)

### Inferences
- **Reward design for PoesIA (derived from the rap paper + RLMR):** gate, don't sum. Format/metre/rhyme failures should give a fixed negative reward (or negative advantage), so the sense/diversity terms only rank among form-valid candidates. A plain weighted sum lets the policy trade sense for rhyme points.
- Every rhyme reward needs an **anti-identity term**: penalise the same rhyme word or the same final surface characters (the rap paper's Jaccard penalty; PoeLM's "no two rhyming lines end in the same word"). The PoesIA engine should treat identical rhyme words, and rhymes made by repeating morphology (e.g. -ción/-ción, -mente/-mente), as weak or invalid. This is the most direct hack in the evidence.
- **Checkpoint selection by validation diversity and the 70B sense verdict, not by training reward.** The rap paper had to do this, and collapse showed up within a fraction of an epoch.
- Use `loss_type="dr_grpo"` or `"dapo"` and a small non-zero β (e.g. 0.001–0.04). With TRL's β=0 default and a 4-bit policy there is no anchor against drift into gibberish. A non-zero β loads a reference model, but with LoRA the reference is the base weights with the adapter disabled (TRL/PEFT behaviour, verify), so it costs little memory.
- The best-evidenced unit for RL here is **short**: a line or a rhyme-pair (couplet), where the verifiable reward is dense, the rollouts are cheap and a 70B "nonsense" veto is reliable. Whole-poem RL multiplies rollout cost about 5–10× and the reward becomes sparse (one bad line fails the poem).

### Gaps
- No GRPO/RLVR study on syllabic metre (Spanish/Italian syllable counting with synalepha, or English/German accentual metre) was found. Results for metre are extrapolated from Japanese rhyme and Chinese tonal-form work.
- The Tang-poetry GRPO paper could not be read in full (paywall redirect). Its numbers, base model and evaluation size are unverified.
- RLMR and Writing-Zero languages and human-evaluation sample sizes were not on the abstract pages. The full PDFs were not read.

## Q2. Offline preference methods (DPO, ORPO, KTO, SimPO, IPO, DivPO, deviation-weighted DPO): pair construction, data sizes, mode collapse

### Takeaway
On this budget, offline preference optimisation on **automatically built pairs** is the safer first step. Pairs come from best-of-N with the form engine, the 70B verdict and embedding-based repetition and novelty. Use a diversity-aware pairing rule (DivPO/DDPO), because quality-only pairs amplify typicality bias. The Apertus 70B one-word verdict maps directly onto **KTO** (unpaired desirable/undesirable labels). The owner's tens to hundreds of blind pairs are too few to train on alone; they are best used as the held-out calibration and acceptance set.

### Cited Findings
- DPO (reference-model KL-constrained preference loss without an explicit reward model) — [Rafailov et al., NeurIPS 2023, arXiv 2305.18290](https://arxiv.org/abs/2305.18290) (nr)
- IPO: DPO can overfit when preferences are (near-)deterministic, because the implied reward gap goes to infinity and the KL regulariser becomes ineffective. IPO's squared loss keeps a bounded margin — [Azar et al., AISTATS 2024, arXiv 2310.12036](https://arxiv.org/abs/2310.12036) (nr). This is relevant because checker-built pairs (pass vs fail metre) are deterministic.
- KTO learns from **binary per-example labels** (desirable/undesirable) rather than pairs. It matched or exceeded DPO from 1B to 30B and tolerated heavy desirable/undesirable imbalance — [Ethayarajh et al., ICML 2024, arXiv 2402.01306](https://arxiv.org/abs/2402.01306) (nr). A later paper notes that KTO needs an extra tunable hyperparameter and uses pass-through gradients — [arXiv 2506.07492](https://arxiv.org/pdf/2506.07492)
- ORPO: a single-stage SFT + odds-ratio preference loss with **no reference model** (memory-friendly on T4) — [Hong et al., EMNLP 2024, arXiv 2403.07691](https://arxiv.org/abs/2403.07691) (nr)
- SimPO: a length-normalised, reference-free reward with a target margin. It "outperforms DPO by up to 6.4 points on AlpacaEval 2 and by up to 7.5 points on Arena-Hard"; the best Gemma-2-9B-it model reached 72.4% LC win rate on AlpacaEval 2 — [Meng et al., NeurIPS 2024, arXiv 2405.14734](https://arxiv.org/abs/2405.14734). Third-party comparisons put ORPO, KTO and SimPO within a fraction of a point on MT-Bench (8.93 / 8.78 / 8.98) — [arXiv 2506.03690](https://arxiv.org/pdf/2506.03690). There is no clear winner on general chat, and none of these papers is about poetry.
- Diversity-aware pairs: DivPO (chosen = rare and high-quality, rejected = common and low-quality; +74.6% story diversity at similar win rate) and DDPO/DORPO (pairs weighted by embedding deviation; **needs >3, ideally ≥4–5 responses per prompt**) are documented with numbers in the earlier notes — [DivPO, arXiv 2501.18101](https://arxiv.org/abs/2501.18101v4); [Chung et al., arXiv 2503.17126](https://arxiv.org/html/2503.17126v1) (see training_and_generation_strategies.md Q1)
- Mode collapse: RLHF reduces output diversity relative to SFT across summarisation and instruction following — [Kirk et al., ICLR 2024, arXiv 2310.06452](https://arxiv.org/abs/2310.06452) (nr). Preference data carries a *typicality bias* (annotators prefer familiar text), which Verbalized Sampling identifies as a cause of mode collapse — [arXiv 2510.01171](https://arxiv.org/pdf/2510.01171v1)
- The rap-GRPO authors themselves plan to move from GRPO to building "scored or preference datasets" from the trained model's candidates, then DPO/PPO, to gain stability — [Ogawa & Kawahara PDF §5](https://aclanthology.org/2026.acl-srw.27.pdf)
- Data scale actually used in the creative-writing preference papers: DDPO about 95.8k prompts with about 4.4 human responses each; CrPO more than 200k human responses (earlier notes). No poetry preference study with ≤1k pairs was found.

### Inferences
- **Automatic pair recipe (inferred):** for each prompt (form, language, theme), sample N = 8–16 candidates from the current model, then:
  1. Hard filter with the form engine.
  2. Run the 70B verdict.
  3. Compute an embedding-based repetition score (max inter-line cosine) and a novelty score (distance from the other candidates and from a corpus of earlier outputs).
  4. Choose *chosen* = form-valid, verdict OK, low repetition, and among the higher-novelty valid candidates (DivPO). Choose *rejected* = either a form failure (teaches form) or a valid-but-typical, repetitive candidate (teaches development).

  Keep the two rejection types as separate subsets and track them separately. Form-fail pairs are deterministic, so prefer IPO or a capped β there.
- **KTO fits the judge:** the 70B verdict is binary and cannot rank. KTO uses exactly that signal, without inventing a ranking among OK outputs. Ranking among OK outputs should then come only from the cheap measurable terms (form score margin, repetition, novelty), never from the judge.
- **Owner pairs:** 50–300 blind pairs are below the scale of every published creative preference result. Use them to (a) check that the automatic chosen/rejected rule agrees with the owner (agreement rate with a confidence interval), (b) pick β and checkpoints, and (c) serve as a final acceptance test. Only fold them into training as a small upweighted DPO/IPO slice once the automatic rule is validated.
- ORPO and SimPO need no reference model, which saves T4 memory. ORPO can also absorb the "development-improving" SFT data and the preference signal in one pass. Weighing the earlier SFT-on-poets result (development up, sense down), ORPO with the poets' lines as SFT targets and sense-rejected samples as the rejected side is a plausible single-run experiment.

### Gaps
- No study found of DPO/KTO/ORPO/SimPO on poetry or metrical verse, nor any minimum-pair-count curve for creative preference tuning.
- No evidence on how well a binary judge verdict works as a KTO signal for creative text.

## Q3. Self-play, self-critique, RLAIF and constitutional revision for creative writing; LLM-judge biases

### Takeaway
AI feedback can replace human labels for alignment-style tasks (RLAIF ≈ RLHF on summarisation and dialogue). For writing quality, the stronger results come from **pairwise, principle-based generative judges**, not scalar scores. Judges have documented biases (position, verbosity, self-preference), and self-correction without an external signal is unreliable. PoesIA's split of a deterministic form engine, an external 70B judge (a different size from the 8B policy) and embedding measures is the right shape. The judge's role should stay **veto/pairwise**, never an absolute quality score that the policy can climb.

### Cited Findings
- RLAIF reached performance comparable to RLHF on summarisation and helpful/harmless dialogue — [Lee et al., arXiv 2309.00267](https://arxiv.org/abs/2309.00267) (nr). Constitutional AI: critique-and-revise against written principles, then RL from AI preferences — [Bai et al., arXiv 2212.08073](https://arxiv.org/abs/2212.08073) (nr). Self-Rewarding LMs: the model judges its own outputs to build iterative DPO pairs — [Yuan et al., arXiv 2401.10020](https://arxiv.org/abs/2401.10020) (nr)
- LLM judges show position, verbosity and self-enhancement biases; GPT-4 agreed with humans at about the human–human level on MT-Bench — [Zheng et al., NeurIPS 2023, arXiv 2306.05685](https://arxiv.org/abs/2306.05685) (nr). Self-preference bias was quantified, with GPT-4 showing a significant degree of it — [Wataoka et al., arXiv 2410.21819](https://arxiv.org/pdf/2410.21819). Judges recognise and favour their own generations — [Panickssery et al., arXiv 2404.13076](https://arxiv.org/abs/2404.13076) (nr)
- Length bias varies by judge. In a 2026 bias-mitigation study, Llama-3.3-70B's preference shift on length-expanded pairs was **+0.44**, Gemini 2.5 Pro +0.40, while GPT-4o (−0.04) and Claude Sonnet 4 (−0.12) were neutral or favoured concision — [Judging the Judges, arXiv 2604.23178](https://arxiv.org/pdf/2604.23178). The 70B open judge closest to Apertus 70B in that study is length-biased.
- Writing-Zero's critique of scalar RMs (over-explanation, length bias) and its pairwise principle-based GenRM fix — [arXiv 2506.00103](https://arxiv.org/abs/2506.00103). IP-GRM (principles generated before seeing the response) — [ICML 2026](https://icml.cc/virtual/2026/poster/63602)
- Self-correction without external feedback often fails or degrades outputs — [Huang et al., arXiv 2310.01798](https://arxiv.org/abs/2310.01798) (nr). Expert-edit-based writing reward models (WQRM, 66–72% expert preference) and LitBench (best off-the-shelf judge 73% agreement with humans on story pairs) are in the earlier notes.
- Non-expert readers prefer AI poems and misread the complexity of human poems as incoherence, so lay-calibrated judges reward simplicity — [Porter & Machery, Sci. Rep. 2024, DOI 10.1038/s41598-024-76900-1](https://pmc.ncbi.nlm.nih.gov/articles/PMC11564748) (earlier notes)

### Inferences
- Apertus 70B and the 8B share a family and training data. Self-preference findings suggest the 70B may favour 8B outputs that sound like Apertus (low perplexity to itself), which is exactly the typicality the project wants to escape. Mitigations: use the judge only as a coherence veto, randomise and swap positions in any pairwise use, length-match candidates (poems of a fixed form are already near equal length, which helps), and audit judge-vs-owner agreement on the owner's blind pairs.
- **Constitutional-style revision at line level** is evidence-compatible if the critique comes from the deterministic engine ("line 3 has 9 syllables, needs 8; rhyme 'corazón/razón' repeats 'zón'"). External, verifiable feedback is what the self-correction literature says is missing. Revision pairs (draft → repaired) are also free DPO/KTO data.
- Self-play between policy versions (SPIN/self-rewarding style) is risky here because the only quality judge cannot rank; it would amplify typicality. No poetry evidence for it was found.

### Gaps
- No study of judge bias specific to poetry or to Apertus was found. Language effects (judge bias in es/it/de/fr vs en) were not covered by the sources read.

## Q4. Feasibility on Kaggle 2x T4 (16 GB each, no bf16): GRPO memory and time with an 8B 4-bit policy + LoRA; rollouts on an external server

### Takeaway
Memory is feasible: Unsloth's own rule of thumb puts QLoRA-4-bit GRPO at about "model parameters = VRAM" (about 8 GB for 8B), and Unsloth publishes a Kaggle GRPO notebook for Llama 3.1 8B with vLLM. vLLM supports the T4 (compute capability 7.5). **Time is the binding constraint.** At the measured ~45 tokens/s/GPU in fp32 HF generation, whole-poem GRPO gets only a few hundred prompt groups per 5 h run, below Unsloth's "at least 300 steps" guidance. Line- or couplet-level GRPO, or vLLM rollouts on the second T4, are the realistic routes. TRL's server mode supports rollouts from a separate vLLM process, but that server must receive weight updates. An external inference API without weight sync makes the training off-policy, which suits offline DPO/KTO data generation, not GRPO.

### Cited Findings
- Unsloth: "For GRPO's GPU VRAM requirements for QLoRA 4-bit, the general rule is the model parameters = the amount of VRAM you will need ... The more context length you set, the more VRAM. LoRA 16-bit will use at minimum 4x more VRAM." "With 15GB VRAM, Unsloth allows you to transform any model up to 17B parameters like Llama 3.1 (8B) ..." Claim: at 20K context with 8 generations, 54.3 GB vs 510.8 GB for standard implementations on Llama 3.1 8B — [Unsloth RL guide](https://unsloth.ai/docs/basics/reinforcement-learning-rl-guide)
- Unsloth throughput claim: "On 1x A100 40GB, expect 4000 tokens/s or so with Unsloth's dynamic 4bit quant of Llama 3.2 3B Instruct. On a 16GB Tesla T4 (free Colab GPU), you can get 300 tokens/s" (the model behind the T4 figure is ambiguous, probably the 3B). Unsloth also "removed double memory usage when loading vLLM and Unsloth together", saving about 5 GB for Llama 3.1 8B — [Unsloth RL guide](https://unsloth.ai/docs/basics/reinforcement-learning-rl-guide)
- Unsloth guidance: wait at least about 300 steps for the reward to rise, use ideally 500+ rows of data, start RL from an instruction-tuned model so that the probability of a correct answer is above zero, and build rubric-style partial rewards rather than all-or-nothing scores — [Unsloth RL guide](https://unsloth.ai/docs/basics/reinforcement-learning-rl-guide)
- The Unsloth notebooks README lists, under "Kaggle Notebooks → GRPO & Reinforcement Learning", "Llama3.1 (8B) | GSM8K Math + vLLM" — [unslothai/notebooks README](https://raw.githubusercontent.com/unslothai/notebooks/main/README.md)
- vLLM GPU requirement: "compute capability 7.5 or higher (e.g., T4, RTX20xx, A100, ...)" — [vLLM GPU installation docs](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html). The page does not mention bf16; T4 lacks bf16, so fp16 is the only half-precision option (general hardware fact, not from that page).
- TRL vLLM integration: **colocate** mode (the default; vLLM shares the trainer GPU, `vllm_gpu_memory_utilization` default 0.3, `vllm_enable_sleep_mode` for OOM) or **server** mode ("vLLM runs in a separate process (and using separate GPUs) and communicates with the trainer via HTTP"; "make sure that the server is using different GPUs than the trainer, otherwise you may run into NCCL errors"). An external server is addressed with `vllm_server_base_url`, and the documented server launch uses an NCCL weight-transfer config. Reward functions may be `async`, run concurrently with `asyncio.gather`; they must return a list of floats, and `None` skips a sample — [TRL GRPOTrainer docs](https://huggingface.co/docs/trl/main/en/grpo_trainer)
- Scale actually used in the one rhyme-GRPO paper: a 3B policy, 8 GPUs, n = 4 rollouts, best checkpoint at 117 steps (0.3 epoch) — [Ogawa & Kawahara](https://aclanthology.org/2026.acl-srw.27.pdf)
- QLoRA (4-bit NF4 base with LoRA adapters) enables finetuning a 65B model on one 48 GB GPU — [Dettmers et al., arXiv 2305.14314](https://arxiv.org/abs/2305.14314) (nr)

### Inferences (budget arithmetic; not measured)
- Rollout cost at the measured **45 tokens/s per GPU**, treating it as aggregate throughput. Batched generation may beat this; measure it.
  - **Whole poem** (sonnet ≈ 14 lines × ~12–15 tokens ≈ 200 tokens): G = 8 gives ~1,600 tokens, about 35 s per prompt group, plus backward and judge latency, so roughly 60 s per step. A 5 h run is then ~300 steps of one prompt each: borderline against Unsloth's "≥300 steps" and with no headroom.
  - **Rhyme-pair/couplet** (~30 tokens): G = 8 gives ~240 tokens, about 5 s generation, so roughly 1,000–2,000 steps per run. This unit is feasible.
  - **Single line** with a fixed rhyme target: cheaper still.
- **2x T4 split:** run vLLM (fp16, 4-bit or AWQ 8B) on GPU1 in TRL server mode, with the trainer (QLoRA, 4-bit) on GPU0. This matches TRL's "separate GPUs" requirement. Whether vLLM on T4 accepts the LoRA weight sync for an Apertus architecture must be tested in a 20-minute smoke run before any 5 h run, per the "smoke-test locally before remote GPU" practice.
- **Apertus 70B as a reward:** call it from an `async` reward function in a batch per group. Latency per step adds directly to wall time, so cache verdicts by text hash. The verdict is binary, so it adds variance only between OK and nonsense; within the OK set the advantage comes from the form and embedding terms.
- **External inference server for rollouts:** a remote endpoint serving the frozen Apertus 8B (no weight sync) makes rollouts stale after the first update. That breaks on-policy GRPO but is exactly right for **offline** best-of-N data generation for DPO/KTO/ORPO. Recommended budget order: (1) offline automatic pairs from external-server sampling → KTO/ORPO/DivPO on the T4s; (2) only then, couplet-level GRPO with the gated reward, if the offline round plateaus.
- fp32 compute on T4 is slow, and fp16 risks overflow in training. Keep the 4-bit base with fp16 compute and fp32 LoRA/optimizer states (the usual QLoRA setup on T4). This is an inference to verify against the project's own earlier fp32 choice.

### Gaps
- No measured GRPO throughput was found for an 8B model on T4 (the Unsloth 300 tok/s figure is for an unclear model and is a vendor claim).
- No public report was found on Apertus 8B (custom architecture) under vLLM on Turing, or under Unsloth's fast_inference.

## Q5. Rewarding diversity/novelty without hurting coherence

### Takeaway
Several 2025–2026 methods add a **group-level diversity reward** to GRPO (GAPO, DPWriter, "Escaping the Obvious") or a diversity-weighted preference loss (DivPO, DDPO). All claim diversity gains without quality loss, but the coherence checks are often weak: GAPO measures "quality" on math and code benchmarks. The safest measured result for creative text is still DDPO/DivPO (earlier notes). Prompt-level Verbalized Sampling gives 1.6–2.1× diversity with no training. In every case diversity must be rewarded **only among form-valid, sense-OK candidates**. Otherwise novelty is cheapest to buy with nonsense, which is what the rap collapse looked like.

### Cited Findings
- GAPO extends GRPO with rewards "computed over the group as a whole" and a frequency-aware reward that pushes towards uniform sampling over valid completions. It claims more diverse outputs while keeping accuracy on GSM8K, MATH, HumanEval and MMLU-Pro (no creative coherence metric on the abstract page) — [GAPO, arXiv 2511.12596](https://arxiv.org/abs/2511.12596)
- DPWriter adds "Diverse Planning Branching" (divergence injected at the planning phase of a semi-structured long CoT) and a "group-aware diversity reward". It claims it "significantly improves output diversity without compromising generation quality" on creative-writing benchmarks (no numbers on the abstract page) — [DPWriter, arXiv 2601.09609](https://arxiv.org/abs/2601.09609)
- "Escaping the Obvious" (NeurIPS 2026 listing) post-trains Qwen3-14B with GRPO, rewarding outputs that link the prompt topic to a semantically distant second topic, and evaluates on analogy, **poetry** and flash fiction for within-prompt and global diversity alongside coherence (search abstract only, not read) — [NeurIPS 2026 listing](https://neurips.cc/virtual/2026/163768)
- RLCS: story generation with entropy-based reward shaping and a generative RM — [arXiv 2601.07149](https://arxiv.org/pdf/2601.07149.pdf) (not read)
- Verbalized Sampling (1.6–2.1× creative diversity, training-free); DivPO (+74.6% story diversity); DDPO (100% vs 0% human "more diverse" vs GPT-4o, with quality preferred 68% vs 24%) — see training_and_generation_strategies.md Q1/Q2 ([arXiv 2510.01171](https://arxiv.org/pdf/2510.01171v1), [arXiv 2501.18101](https://arxiv.org/abs/2501.18101v4), [arXiv 2503.17126](https://arxiv.org/html/2503.17126v1))
- Collapse under a creative RL reward included loss of diversity, with outputs "largely independent of the prompt". The rap authors used "no extreme reduction in output diversity" as a checkpoint criterion — [Ogawa & Kawahara](https://aclanthology.org/2026.acl-srw.27.pdf)

### Inferences
- PoesIA diversity reward, levelled to the unit of generation:
  - **Line:** a penalty on stock-phrase n-grams (a cliché list per language) and on repeated content words within the poem.
  - **Rhyme pair:** a penalty on identical or morphological rhyme, plus a bonus for rhyme-word rarity (corpus frequency) capped so that rare-but-obscure words are not over-rewarded.
  - **Stanza/whole poem:** embedding-based development, i.e. moderate consecutive-stanza distance (not too similar = repetition, not too far = incoherence; a band, not a maximum), plus within-group dispersion (GAPO/DDPO style) across the G samples of the same prompt.
  - Apply all diversity terms **multiplied by** the form gate and the sense verdict (zero if either fails). This stops "novel nonsense" from scoring.
- Track per run: distinct-n, mean pairwise embedding distance within the group, rhyme-word type/token ratio, the 70B nonsense rate and the collapse rate on a fixed held-out prompt set. A run that raises reward while the nonsense or collapse rate rises is reward hacking by definition (the rap pattern) and should stop early.

### Gaps
- None of the group-diversity GRPO papers was read in full, so their human-evaluated coherence and sample sizes are unknown. "Escaping the Obvious" is the only one known to include poetry; its full text was not read.
- No multilingual (es/it/de/fr) evidence on diversity rewards was found.

## Scholarly sources (for Zotero)

Accessed 2026-10-16. (nr) = not re-fetched this session.

- Ogawa, H. & Kawahara, D. 2026. Constructing a Japanese Rap Lyric Generation Model with GRPO. ACL 2026 Student Research Workshop, pp. 340–351. ACL Anthology 2026.acl-srw.27
- (lead, unverified) Large language models learning to write rhyming Tang poetry: A Xunzi Yayun R1 case study. npj Heritage Science 2025. DOI 10.1038/s40494-025-02087-x
- Zugarini et al. 2021. Generate and Revise: Reinforcement Learning in Neural Poetry. arXiv:2102.04114 (nr)
- RLMR: Reinforcement Learning with Mixed Rewards for Creative Writing. 2025. arXiv:2508.18642
- Writing-Zero: Bridge the Gap Between Non-verifiable Tasks and Verifiable Rewards. 2025. arXiv:2506.00103
- ByteDance Seed. 2025. Seed1.5-Thinking. arXiv:2504.13914 (nr)
- IP-GRM ("Unbiased Principles, Robust Rewards"). ICML 2026 poster 63602 (not read)
- Shao et al. 2024. DeepSeekMath (GRPO). arXiv:2402.03300 (nr)
- Ahmadian et al. 2024. Back to Basics: Revisiting REINFORCE-Style Optimization (RLOO). ACL 2024. arXiv:2402.14740 (nr)
- Liu et al. 2025. Understanding R1-Zero-Like Training: A Critical Perspective (Dr. GRPO). arXiv:2503.20783
- Yu et al. 2025. DAPO: An Open-Source LLM Reinforcement Learning System at Scale. arXiv:2503.14476 (nr)
- Yue et al. 2025. Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model? arXiv:2504.13837 (nr)
- Gao, Schulman & Hilton 2022. Scaling Laws for Reward Model Overoptimization. arXiv:2210.10760 (nr)
- Singhal et al. 2023. A Long Way to Go: Investigating Length Correlations in RLHF. arXiv:2310.03716 (nr)
- Shao et al. 2025. Spurious Rewards: Rethinking Training Signals in RLVR. arXiv:2506.10947 (nr)
- Rafailov et al. 2023. Direct Preference Optimization. NeurIPS 2023. arXiv:2305.18290 (nr)
- Azar et al. 2024. A General Theoretical Paradigm to Understand Learning from Human Preferences (IPO). AISTATS 2024. arXiv:2310.12036 (nr)
- Ethayarajh et al. 2024. KTO: Model Alignment as Prospect Theoretic Optimization. ICML 2024. arXiv:2402.01306 (nr)
- Hong, Lee & Thorne 2024. ORPO: Monolithic Preference Optimization without Reference Model. EMNLP 2024. arXiv:2403.07691 (nr)
- Meng, Xia & Chen 2024. SimPO: Simple Preference Optimization with a Reference-Free Reward. NeurIPS 2024. arXiv:2405.14734
- Explicit Preference Optimization: No Need for an Implicit Reward Model. 2025. arXiv:2506.07492
- Robust Preference Optimization via Dynamic Target Margins. 2025. arXiv:2506.03690
- Kirk et al. 2024. Understanding the Effects of RLHF on LLM Generalisation and Diversity. ICLR 2024. arXiv:2310.06452 (nr)
- Lee et al. 2023. RLAIF: Scaling Reinforcement Learning from Human Feedback with AI Feedback. arXiv:2309.00267 (nr)
- Bai et al. 2022. Constitutional AI: Harmlessness from AI Feedback. arXiv:2212.08073 (nr)
- Yuan et al. 2024. Self-Rewarding Language Models. arXiv:2401.10020 (nr)
- Zheng et al. 2023. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS 2023. arXiv:2306.05685 (nr)
- Wataoka, Takahashi & Ri 2024. Self-Preference Bias in LLM-as-a-Judge. arXiv:2410.21819
- Panickssery, Bowman & Feng 2024. LLM Evaluators Recognize and Favor Their Own Generations. NeurIPS 2024. arXiv:2404.13076 (nr)
- Judging the Judges: A Systematic Evaluation of Bias Mitigation Strategies in LLM-as-a-Judge Pipelines. 2026. arXiv:2604.23178
- Huang et al. 2023. Large Language Models Cannot Self-Correct Reasoning Yet. arXiv:2310.01798 (nr)
- GAPO: Group-Aware Reinforcement Learning for Output Diversity in Large Language Models. 2025. arXiv:2511.12596
- DPWriter. 2026. arXiv:2601.09609
- Escaping the Obvious: Reinforcement Learning for Conceptually Diverse Generation. NeurIPS 2026 (listing 163768; not read)
- RLCS. 2026. arXiv:2601.07149 (not read)
- Dettmers et al. 2023. QLoRA: Efficient Finetuning of Quantized LLMs. NeurIPS 2023. arXiv:2305.14314 (nr)
- Greek rhyme: LLMs Got Rhythm? Hybrid Phonological Filtering for Greek Poetry Rhyme Detection and Generation. arXiv:2601.09631
- Already in the earlier notes (not repeated): DivPO 2501.18101; Chung et al. 2503.17126; CrPO 2505.14442; Verbalized Sampling 2510.01171; WQRM 2504.07532; LitBench 2507.00769; PoeLM 2205.12206; Porter & Machery 10.1038/s41598-024-76900-1

Documentation (not for Zotero; cite with access date 2026-10-16): TRL GRPOTrainer (huggingface.co/docs/trl/main/en/grpo_trainer); Unsloth RL guide (unsloth.ai/docs/basics/reinforcement-learning-rl-guide); unslothai/notebooks README; vLLM GPU installation (docs.vllm.ai).

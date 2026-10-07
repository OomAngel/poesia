# Retraining plan: bigger base model, bigger corpus (2026-10)

> **Status:** plan, written 2026-10-04 on the desktop. No training has run yet, and no
> memory figure below has been measured on the GPU. **Decision recorded:** Angel decided
> on 2026-10-04 to retrain, which settles `GENERATION_QUALITY_PLAN.md` gap #9
> ("re-train vs deprioritize").
> Reproduce the model-size table with `scripts/estimate_qlora_vram.py`.

## 1. The question

The existing adapters were trained on an RTX 2000 Ada (8 GB, 2026-07-28 to 08-07). Retraining
now happens on the desktop RTX 3070. That raises two questions: which base models can that
GPU train, and does the master corpus (85,027 poems, ~58% English; §4) improve on the current adapters?

## 2. Hardware: same memory, more speed

| | RTX 2000 Ada (July runs) | Desktop RTX 3070 (`AngelThuis`) |
|---|---|---|
| VRAM | 8 GB according to the poesia records (the desktop card of that name has 16 GB; the laptop card has 8 GB) | 8 GB, Ampere sm_86 |
| Free for training | — | 5.1 GB measured 2026-10-04 with apps open. The 5900X has no integrated GPU, so the 3070 also drives the display. **Budget about 6.5 GB with GPU-using apps closed (estimate).** |
| Speed | — | Probably 1.5–2× faster (more memory bandwidth and many more cores). Not timed. |

The 3070 buys faster iteration, not more memory. If the RTX 2000 Ada was the 16 GB desktop
card, the 3070 is the smaller GPU. That doesn't change the table below, which is computed
for the 3070.

## 3. Which base models fit

### Method

`scripts/estimate_qlora_vram.py` reads each model's safetensors headers from Hugging Face,
which gives exact tensor shapes without downloading the weights. It sorts every tensor into
transformer linear weights (quantised to NF4), input embedding, `lm_head`, or the
vision/audio tower (left out, since training is text-only). It reports two layouts:

- **default:** NF4 body, with the embedding and `lm_head` kept in bf16. This is
  bitsandbytes' default skip list and what every July run used.
- **best:** NF4 body, `lm_head` also quantised to NF4, and the embedding kept in CPU RAM.
  An embedding lookup is a cheap gather, and `lm_head` is frozen under LoRA, so neither
  change touches what LoRA learns. A model whose embedding is tied to `lm_head` (Gemma, and
  the small Qwen models) can't do either, so "best" equals "default" for those.

**+train** adds a flat 1.5 GB for LoRA weights, optimiser state, activations under gradient
checkpointing (seq 300, batch 1–2), logits and the CUDA context. **That 1.5 GB is an
estimate, not a measurement.** Run on 2026-10-04:

| Model | Released | Body (B) | Embedding (B) | lm_head (B) | Tied | default | best | +train | Fits 6.5 GB? |
|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-3B-Instruct (*current challenger, for scale*) | 2024-09 | 2.77 | 0.31 | — | yes | 2.1 | 2.1 | 3.6 | yes |
| Qwen3.5-2B | 2026 | 1.43 | 0.51 | — | yes | 1.8 | 1.8 | 3.3 | yes |
| Qwen3-4B-Instruct-2507 | 2025-08 | 3.63 | 0.39 | — | yes | 2.7 | 2.7 | 4.2 | yes |
| Qwen3.5-4B | 2026 | 3.69 | 0.64 | — | yes | 3.2 | 3.2 | 4.7 | yes |
| Salamandra-7B-instruct-2606 (BSC; heavy Spanish pretraining) | 2026-06 | 5.67 | 1.05 | 1.05 | no | 7.1 | 3.5 | 5.0 | yes, best layout only |
| Qwen3-8B | 2025-04 | 6.95 | 0.62 | 0.62 | no | 6.1 | 3.9 | 5.4 | yes, best layout only |
| **Qwen3.5-9B** | 2026 | 7.16 | 1.02 | 1.02 | no | 7.8 | 4.3 | 5.8 | **yes, best layout only: the ceiling** |
| EuroLLM-9B-Instruct-2512 | 2025-12 | 8.10 | 0.52 | 0.52 | no | 6.3 | 4.5 | 6.0 | yes, best layout only |
| Gemma 4 E4B | 2026-04 | 4.03 | 3.49¹ | — | yes | 9.1 | 9.1 | 10.6 | no¹ |
| Gemma 4 12B | 2026-04 | 10.90 | 1.01 | — | yes | 7.7 | 7.7 | 9.2 | no |
| Mistral-Nemo 12B | 2024-07 | 10.91 | 0.67 | 0.67 | no | 8.4 | 6.0 | 7.5 | no |
| Qwen3-14B | 2025-04 | 13.21 | 0.78 | 0.78 | no | 10.0 | 7.3 | 8.8 | no |

All sizes in GB except the parameter counts. ¹ Most of E4B's embedding is per-layer
embeddings, which the architecture is designed to keep off the accelerator. The script can't
model that, so E4B might fit after all. Untested.

Mixture-of-experts models (Qwen3.5-35B-A3B, Gemma 4 26B-A4B) compute with only 3–4B
parameters per token, but all their weights still have to be stored: about 18 GB at 4-bit.
They would live in CPU RAM and stream over PCIe (the card runs at x8) on every step, which
is far too slow for training. Llama 3.1 8B is gated, so the script couldn't read it; at
8B with a 128k vocabulary it sits between Qwen3-8B and EuroLLM-9B, and it's older than both.

### What this corrects

`LOCAL_ONLY.md` and `docs/archive/EXPERIMENTS_PLAN.md` §2 said 8B-class models "won't fit 8 GB" and need
≥ 16 GB. That holds for the **default** layout, the only one the July runs used. With the
**best** layout, the estimate says models up to ~9B fit. Both claims stay unproven until the
smoke run in §6 step 4.

### Measured 2026-10-05: Qwen3-8B fits, barely

Smoke run (`mlops/configs/smoke_qwen3_8b.yaml`, 40 steps, batch 1 × 8 accumulation,
`max_length` 300, LoRA r=16 on attention, `memory_layout: low_vram`): **peak 7.32 GB
allocated, 7.51 GB reserved**, with 7.4 GB free when it started (GPU-heavy apps closed).
Loss 3.60 → 2.03. Steady-state throughput about **140 tokens/s** (111 averaged with warm-up).

The table's "+train" column assumed 1.5 GB of training overhead; the real overhead is about
3.4 GB (activations under checkpointing plus fp32 logits over the 151,936-token vocabulary).
So **Qwen3-8B is the practical ceiling**, not 9B: Qwen3.5-9B (≈4.3 GB of weights, a
248k vocabulary) would need a shorter `max_length` or Unsloth to fit.

How `low_vram` is implemented (`poesia.device`): lm_head quantized to NF4, whole model on
GPU 0, then the input embedding moved to CPU RAM with two hooks, and no
`prepare_model_for_kbit_training` (its fp32 upcast alone costs ~2.5 GB on 8B). Two traps
found on the way: accelerate's own CPU placement copies the weights to the GPU every step
(and failed under WSL), and a single-GPU device map leaves no `hf_device_map`, so
`accelerate.prepare` moves the embedding back; the script records `hf_device_map = {"": 0}`.

### Picks

- **Largest that fits: Qwen3-8B** (measured above). Earlier pick, superseded: Qwen3.5-9B. It's the newest and most downloaded dense model in the
  range that fits, and from the same family as the current adapters. Two catches. First, 24
  of its 32 layers use linear attention, which needs the `flash-linear-attention` and
  `causal-conv1d` packages (both missing from the `poesia` env on 2026-10-04). Without them
  it falls back to a slower path that uses more memory, which at the ceiling can break the
  fit. Second, the "best" layout needs a code change in `scripts/train_poetry_lora.py` (an
  empty bitsandbytes skip list and the embedding placed on CPU).
- **Largest with no new dependencies: Qwen3-8B.** Standard transformer, 0.4 GB more headroom.
- **Spanish specialist: Salamandra-7B.** Worth one run for the Spanish share of the corpus
  (~42%) and Spanish metre; training is mainly English (§7). Weaker as a general model.
- **Fair comparison at the current size: Qwen3.5-2B or Qwen3-4B-2507.** These separate "newer
  base model" from "bigger model".

The environment already supports these architectures: transformers 5.14.1 includes `qwen3`,
`qwen3_5` and `gemma4`. Unsloth would add headroom, but it's still blocked by version pins
(`docs/archive/EXPERIMENTS_PLAN.md` §3).

## 4. The larger corpus

| Fact | Source |
|---|---|
| **2026-10-04: master corpus of 85,027 poems (49,128 English, 35,899 Spanish, 9,405 sonnets)**, deduplicated, ADSO gold removed (`scripts/build_corpus.py`). Before: 12,340 unique. Added (counts before cross-source dedup, so they sum to 85,754): POSTDATA (22,291 es), public-domain English (33,234), Poetry Foundation (12,322), DISCO v5 and Golden-Age corpora (5,034), Gutenberg (533) | `CORPUS_SOURCES.md` |
| Deduplication across files is done in `corpus_master` (full text + first line; 19,227 copies dropped). The per-source files still contain the duplicates | `CORPUS_SOURCES.md` "Known limitations" |
| **The training path to the new corpus:** `scripts/build_fixed_dataset.py` reads `corpus_master/poems.jsonl` (it falls back to globbing `training_data_structured/*.jsonl` only when the master corpus is missing) and writes `mlops/data/train_fixed.jsonl`, the file `train_v2_fixed.yaml` trains on. The other configs still name specific curated files (`sonetos_*`, `master_train*`, `multiform_train`) | the script, `mlops/configs/` |
| History (2026-08-01): the old glob over `training_data_structured/*.jsonl` produced the 38K-example `v2-fixed` dataset, *before* the 08-31 expansion | `memory-bank/activeContext.md` |
| The champion `poetry-lora-distilled` trained on `training_data_distilled/`: 57,862 bytes, about 100 Groq-distilled sonnets (`dvc.yaml`: `distill_sonetos.py --count 100`) | `dvc.lock` |
| **The corpus was rebuilt on the desktop 2026-10-04** from git history (`f8b2017^`) and the fetch scripts, without the DVC remote (`CORPUS_SOURCES.md` "Rebuilding the corpus"). **The adapters are still only on the laptop's D: drive** (`models/` is 36 KB here). | checked 2026-10-04 |
| Copyrighted modern poets (Paz, Sabines, Neruda, the Poetry Foundation set) are in by Angel's decision: training a personal model, poems never shared | 2026-10-04 |

### What the previous runs say about more data

Training on more, broader data has lost twice so far:

- `v2-fixed` (38K line examples from the whole structured corpus): 4.80 and 4.88.
- `multiform` (1,246 poems across 5 forms): 7.93 and 9.29.

Both lost to `distilled`, which trained on about 100 clean sonnets (0.90 and 1.29). Neither
loss is a clean test of corpus size. `v2-fixed` also changed the prompt format, and
`multiform` changed the task. Still, nothing yet shows that more raw poetry improves the
metric, which today rewards exact Spanish hendecasyllables (an English metre target is part of
§6 step 2). Human-written verse has irregular metre, and
the auto-split Gutenberg files contain some table-of-contents and dedication noise.

Retraining therefore treats corpus size as a hypothesis to test, not an assumed win. §6
varies one factor per run.

### Evidence quality (correcting an earlier reading)

Every adapter score comes from 3 themes (luna, mar, tiempo) with unseeded generation. The
ranking of the top two flipped between runs: 2026-09-01 had `qwen3b` 1.00 and `distilled`
1.29; 2026-09-08 had `distilled` 0.90 and `qwen3b` 1.13. So "3B did not beat 1.5B" isn't
supported. Their order is within noise. The large gaps (≤ 1.3 against ≥ 4.8) are real at
this sample size. Differences under about 0.5 are not.

**The measuring tool is itself noisy (measured 2026-10-05).** `scripts/check_scansion_vs_adso.py`
compares the Spanish syllable counter with the ADSO gold standard (100 hand-scanned
Golden-Age sonnets, 1,404 lines): exact agreement on 59.3% of lines, off by one on 33.9%,
off by two or more on 6.8%. Mean absolute error 0.48 syllables, biased low (−0.34; it
undercounts, e.g. "tú, a quien los ojos dieron la bebida" counted 10, gold 11). The old
metric, |mean − 11|, also let long and short lines cancel. So a July "syllable deviation" of
0.90 sits close to the counter's own error. The rebuilt evaluation reports per-line
deviation and metre pass rate; read both against this floor, and re-run the check after any
phonology change.

**The champion's training data is malformed.** All 50 sonnets in
`training_data_distilled/sonetos.jsonl` (`poetry-lora-distilled`) separate verses with the
two characters `\n`, not newlines, so each poem trained as one long line. The baseline
rebuild (`mlops/configs/baseline_distilled_2026_10.yaml`) keeps this unchanged so it
reproduces the July recipe; a cleaned version is a separate experiment.

## 5. Run size and training time

A run's size is the number of poems passed to `build_fixed_dataset.py --max-poems`. A random
sample keeps the corpus mix (~58% English). Size it by token budget:

```
tokens per epoch = poems × tokens per poem
time             = tokens per epoch × epochs ÷ throughput (tokens/s)
poems            = time budget × throughput ÷ (tokens per poem × epochs)
```

**Tokens per poem**, measured 2026-10-04 with the Qwen3.5 tokenizer, `max_length` 300, on
random samples from `corpus_master` (scratchpad scripts; rerun on corpus or model change):

| Sample | Line examples per poem | Fit in 300 tokens (kept) | Usable tokens per poem |
|---|---|---|---|
| Sonnets (200) | 14.5 | 99% (line 14 dropped in 10% of sonnets) | ~2,600 |
| Spanish, all forms (250) | 49.2 | 32% | ~2,700 |
| English (250) | 38.7 | 39% | ~2,550 |

**Planning figure: ~2,600 usable tokens per poem.** The full corpus is about 220M usable
tokens per epoch, or about 780M if truncated examples are counted.

**Throughput, measured 2026-10-05 on the 3070:**

| Run | Model, layout | Tokens/s | Peak VRAM (allocated / reserved) | 2,000-poem epoch (~5.2M tokens) |
|---|---|---|---|---|
| smoke | Qwen3-8B, low_vram, batch 1×8 | ~140 (steady) | 7.32 / 7.51 GB | ~10 h |
| comparison | Qwen3-4B-2507, default, batch 4×4 | 422 | 6.77 / 10.43 GB | ~3.4 h |
| baseline | Qwen2.5-1.5B, default, batch 8×2 | 1,138 | 5.88 / 13.16 GB | ~1.3 h |

**Reserved above 8 GB means spill into system RAM.** Under Windows/WSL the NVIDIA driver can
fall back to shared system memory when VRAM runs out ("CUDA sysmem fallback"), so a run that
"fits" may be partly running from much slower memory. The 8B smoke stayed inside 8 GB; the
batch-4 and batch-8 runs did not. For long runs, size batches so reserved stays under ~7.5 GB.

Before the measurement, this section read: As an illustration only: at 1,000 tokens/s, a 10-hour
overnight budget is 36M tokens, so about 13,800 poems for one epoch or 4,600 for three.
Fewer poems over more epochs is how the July runs worked (10 epochs on ≤ 500 sonnets). On
this corpus, more poems at 1–3 epochs uses its breadth better.

**Bug the size depends on:** each line's prompt lists every previous line, and training
truncated `prompt + completion + EOS` at 300 tokens from the right (`train_poetry_lora.py`,
before commit `923434e`). From about line 19–20 of a long poem the target line and EOS were
cut off, so the example taught the model to continue the prompt. That's 61–68% of examples
outside sonnets. **Fixed 2026-10-04 with option (a):** `train_poetry_lora.py` tokenizes without
truncation and drops any example longer than `max_length` (`_drop_overlong`; the counts are
logged as the MLflow params `dropped_overlong_train` and `dropped_overlong_eval`). On 150
random corpus poems it dropped exactly the 2,369 of 4,583 examples (52%) the old code cut,
and all 2,214 kept examples end in EOS. Option (b), keeping only the last few previous lines
in both the builder and `candidate_generator.py`, would recover long poems' later lines; it
isn't done.

## 6. Order of work

Each step changes one thing, so its effect can be read off.

0. **Data on the desktop: corpus done 2026-10-04, adapters not.** The old adapters are
   needed only as the baseline in step 3; they come from the laptop's D: drive or a network
   DVC remote. The new corpus is versioned (`dvc add`, 2026-10-04) but cached only on the
   desktop. **Never run a bare `dvc repro`:
   it retrains `poetry-lora-v2` first** (`DVC_INTEGRATION.md`).
1. **Build the corpus: done 2026-10-04** (`scripts/build_corpus.py` → `corpus_master/`;
   `build_fixed_dataset.py` now reads it). The full corpus gives millions of line examples
   and runs out of RAM, so **size every run with `--max-poems`**. 2,000 poems give 90,236
   examples (2.4× `v2-fixed`), and a random sample keeps the ~58% English mix. Size it with
   §5. Optional still: filter for
   metre with `scripts/filter_exact_syllables.py`. It takes `--language es|en`, so run it once
   per language on split files. Its `--target` defaults to 11 (hendecasyllable); pass
   `--target 10` for English pentameter. Don't use `quality_filter.py` on the full corpus: it applies
   Spanish phonology with no language guard (`CORPUS_SOURCES.md`). Record `corpus_master/manifest.json`'s sha256 and the
   `--max-poems`/`--seed` used in the adapter registry.
2. **Strengthen the evaluation before trusting any new score.** Use at least 5 themes (the
   `ANALOGIA_PLAN.md` checklist), seeded generation, more than one sample per theme, and the
   rhyme-key score from `GENERATION_QUALITY_PLAN.md` next action 8. Check the syllable scorer
   itself against `eval_gold/adso_gold_100.jsonl` (hand scansion) before trusting its numbers.
   Training is now mainly English, so the evaluation needs English themes and an English
   metre target too, not only Spanish hendecasyllables.
3. **Separate base model from data.** Run the champion recipe (`train_distilled.yaml`, same
   100 sonnets) on Qwen3.5-2B or Qwen3-4B-2507, with only the config's `model:` key changed. Compare it
   with `distilled` under the step-2 evaluation.
4. **Smoke-test the largest model.** Prerequisite: implement the best layout in
   `scripts/train_poetry_lora.py` (§3 "Picks": empty bitsandbytes skip list so `lm_head` is
   NF4, embedding placed on CPU); as of 2026-10-04 the script has neither. Then run Qwen3-8B,
   then Qwen3.5-9B once its two kernels are installed, for about 50 steps. Record
   `torch.cuda.max_memory_allocated()` and tokens/s. This confirms or refutes §3.
5. **Measure the corpus effect.** Keep the winning base from step 3 and train on (a) the
   distilled set and (b) the step-1 corpus, then the distilled set. Only (b) beating (a)
   justifies the larger corpus.
6. **Scale up.** Train the best data recipe on the largest model that passed step 4.
7. **Check deployment.** The laptop runs adapters through a llama.cpp build for sm_50, which
   may be too old for the `qwen3_5` architecture. A 9B Q4_K_M GGUF (about 5.5 GB) runs CPU-only
   there. Confirm before treating a 9B adapter as deployable. The Lemonade plan
   (`LEMONADE_INTEGRATION.md`) serves "the champion adapter", so its size matters there too.

## 6a. Results so far (2026-10-05)

**The July recipe is a dead end, and plain Qwen3-4B is the bar to beat.**

- Baseline (July recipe rebuilt, Qwen2.5-1.5B), 36 seeded poems: Spanish 0.63 syllables off
  per line, 57% of lines pass metre, 3% rhyme accuracy; English 0.35, 73%, 10%.
- The same recipe on Qwen3-4B produced runaway lines (76 lines over 20 syllables, up to
  55, in 15 poems; evaluation stopped there). Test on the same themes and seeds with plain
  Qwen3-4B and no adapter: 0.21 and 0.29 syllables off, 79% and 71% metre, 30% and 60%
  rhyme, no runaway lines. So the adapter trained on the July recipe (whole poems with
  literal `\n`, while the loop asks for one line) caused the runaway, not the base model.
  Two poems only: a signal, measured fully in the queue below.
- First corpus run (`mlops/configs/corpus_2k_qwen3_4b.yaml`): 2,000 poems from
  `corpus_master` in the loop's line format, 28,928 examples after dropping those over 300
  tokens, 1,808 steps at ~7.8 s. Queued after it: the adapter and plain Qwen3-4B, 36 poems
  each. Building that dataset once overflowed pyarrow (2 GB of prompt text); the training
  script now drops texts over `max_length × 16` characters before building the Dataset
  (the densest fitting example measured 4.63 characters per token).

### Update 2026-10-06: the end-of-text bug

The first corpus run trained cleanly (eval loss 1.40 → 1.07) but its adapter produced
runaway lines again: Spanish 17.9 syllables off per line, 19% metre, 99 accepted lines over
20 syllables. Cause, verified: `train_poetry_lora.py` set `pad_token = eos_token` and used
`DataCollatorForLanguageModeling`, which masks every token equal to the pad id, so the real
`<|im_end|>` ending every example got label −100. **No adapter since July learned to stop.**
Fixed in `52fea7a` (labels mask padding positions only).

| 2 Spanish poems (luna, tiempo; seed 0) | Off per line | Metre | Rhyme | Lines > 20 syll. | s/poem |
|---|---|---|---|---|---|
| corpus run, bug | — (17.9 over 18 poems) | 19% | 41% | many | 200–480 |
| 120-step probe with the fix | 0.14 | 86% | 70% | 0 | 50–60 |
| plain Qwen3-4B | 0.25 | 75% | 45% | 0 | 150–250 |

**Full reference evaluations (36 seeded poems each):**

| | es off/line | es metre | es rhyme | en off/line | en metre | en rhyme |
|---|---|---|---|---|---|---|
| July recipe (Qwen2.5-1.5B) | 0.63 | 57% | 3% | 0.35 | 73% | 10% |
| Plain Qwen3-4B, no adapter | 0.52 | 62% | 30% | 0.69 | 56% | 70% |
| Corpus run with the fix (`corpus_2k_qwen3_4b_eosfix.yaml`) | 0.38 | 71% | 24% | 0.46 | 75% | 40% |

The corrected run (1,808 steps, eval loss 1.08; adapter `models/corpus-2k-qwen3-4b-eosfix`,
DVC-tracked, cached on the desktop only) beats plain Qwen3-4B on metre in both languages
and loses on rhyme, by 6 points in Spanish and 30 in English. Read with care: 18 poems per
language, one seed set; the syllable counter agrees exactly with expert scansion on 59% of
ADSO lines, so metre differences of a few points sit inside its error; rhyme is the
consonant key of the last word (`poesia.evaluation.poem_eval`). The English rhyme drop is
large enough to be real; why the adapter rhymes worse is not established. Not yet a
replacement for plain Qwen3-4B where rhyme matters.

## 7. Decisions for Angel

Decided 2026-10-04: Spanish and English, mainly English; copyrighted poems in (personal
model, never shared); Golden-Age original spelling kept; corpus versioned with DVC.

Still open:

- **A DVC remote both machines reach:** the new corpus is cached only on the desktop, and
  the old adapters only on the laptop's D: drive (§6 step 0).

## 8. What would change this plan

- The step-4 peak memory exceeds the budget: drop to the next row in §3 and correct the table.
- The step-3 new base doesn't beat `distilled` under the stronger evaluation: base-model age
  isn't the bottleneck, so put effort into data and repair rather than model size.
- Step 5(b) doesn't beat 5(a): the larger corpus hurts or doesn't help for this metric, so keep
  it for retrieval and style (`memoria`) and stop using it for fine-tuning.

## 9. Later experiments

Moved from `docs/archive/EXPERIMENTS_PLAN.md` §3 on 2026-10-05, when that plan was archived
(`docs/archive/EXPERIMENTS_PLAN.md`). Each changes one thing against the baseline
from §6.

| Experiment | Change | Status |
|---|---|---|
| LoRA rank 64 | `lora_r: 64` | Open. Try on `train_distilled.yaml` first. |
| LoRA on all linear layers | add `gate_proj`, `up_proj`, `down_proj` to `lora_target_modules` | Open. Roughly doubles trainable parameters; recheck peak VRAM. |
| Multi-teacher distillation | distill with two hosted models instead of one | Open. Needs both API keys. |
| Syllable-filtered data | train only on lines that pass `filter_exact_syllables.py` | Open. Note the counter's own error (`check_scansion_vs_adso.py`). |
| Unsloth | replace the PEFT loop | Blocked: unsloth 2026.9.11 needs torch <2.13 and transformers ≤5.5. |
| DPO | `scripts/train_poetry_dpo.py` | Done in July: lost to plain cross-entropy (6.07 vs 0.90, 3 themes). |

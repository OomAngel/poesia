# Retraining Plan — Structured Poetry Fine-Tuning

## Why the first attempt fell short

| What we did | What we should have done |
|---|---|
| Format: `"Poem:\n{text}"` | Format: `"Write a {form} in {language}.\nSyllables: {n}. Rhyme: {scheme}.\n{text}"` |
| 9,622 poems, unfiltered | 1,000-2,000 fully structured poems (sonetos, décimas) |
| 2 epochs (52 min) | 10 epochs (4-5 hours) |
| LoRA r=16, 3 modules | LoRA r=64, all linear layers |
| Loss only metric | Loss + phonological validity + human eval |
| Run once, no iteration | Iterative: train → eval → adjust → retrain |

## Proposed approach

### 1. Training data with explicit form annotations

Instead of `"Poem:\n{poem_text}"`, each example should be:

```
Write a soneto in Spanish.
Syllables: 11 per line.
Rhyme scheme: ABBA ABBA CDC DCD.

Un soneto me manda hacer Violante,
que en mi vida me he visto en tal aprieto;
catorce versos dicen que es soneto:
burla burlando, van los tres delante.
...
```

This teaches the model to associate *structural labels* (soneto, 11 syllables, ABBA) with *structural patterns* in the output.

### 2. Curated subset — sonetos only (100-200 examples)

Sonetos have the strictest, most detectable structure. A model that can write a soneto can generalize to looser forms. Use only:
- 14-line poems from our corpus (we detected ~107 potential sonetos)
- Hand-verified for actual soneto structure (remove false positives)
- Annotated with correct syllable count and rhyme scheme

### 3. Longer training with LoRA r=64

| Parameter | First run | Proposed |
|---|---|---|
| LoRA rank | r=16 | r=64 |
| Target modules | q,k,v,o | q,k,v,o,gate,up,down |
| Trainable params | 7.4M (0.24%) | ~30M (1%) |
| Epochs | 2 | 10 |
| Learning rate | 2e-4 | 1e-4 with cosine decay |
| Max length | 192 | 256 |

### 4. Evaluation during training

At each eval step, generate 3 sonetos and score them:
- **Line count**: exactly 14 lines?
- **Syllable accuracy**: average deviation from 11 syllables per line
- **Rhyme accuracy**: percentage of line endings matching the scheme
- **Loss**: standard next-token prediction loss (for reference only)

Stop training when syllable accuracy stops improving, not when loss plateaus.

### 5. Iteration loop

```
1. Train on 100 curated sonetos → eval
2. If syllable accuracy < 80%: increase LoRA rank or add data
3. If syllable accuracy > 80%: add décimas, romances, cuartetos
4. Final eval: compare with base model on 10 held-out themes
```

## Estimated timeline

| Step | Time |
|---|---|
| Curate 100-200 verified sonetos from corpus | 1 hour |
| Manual annotation (rhyme scheme per poem) | 1 hour |
| Format conversion to structured prompts | 30 min |
| Training (10 epochs on 150 examples) | ~2 hours |
| Evaluation + iteration | 1 hour |
| **Total** | **~5.5 hours** |

## When to stop

Stop when:
- Generated sonetos have ≥12 lines on average (up from 9)
- Average syllable deviation ≤1 per line (down from ~2)
- Rhyme accuracy ≥50% (up from ~0%)
- The output is *formally recognizable as a soneto* even if the poetry isn't beautiful yet

That's the point where the constrained loop can take over — the model produces a rough soneto, and the scorer + repair loop polish it.

## What we're still missing — and references to fill the gaps

### Techniques we haven't considered

| Technique | What it does | Why it matters | Reference |
|---|---|---|---|
| **DSPy prompt optimization** | Algorithmically searches for optimal prompt format (not guessing) | Our training format `"Write a soneto..."` is a guess. DSPy's `MIPROv2` / `GEPA` optimizers would find the format that maximizes syllable accuracy | [dspy.ai](https://dspy.ai) |
| **RL / DPO with scorer as reward** | Train the model to maximize the constrained loop's score, not just next-token loss | Directly optimizes for metre + rhyme instead of hoping they emerge from raw text | Hugging Face TRL docs |
| **Grammar-constrained decoding** | Constrain token generation at inference to satisfy syllable/rhyme rules | No training needed — the constraint is enforced at generation time. Works with any base model | [outlines-dev.github.io](https://outlines-dev.github.io) |
| **Knowledge distillation** | Use Groq (Llama 3.3 70B) to generate 1,000 perfect sonetos, train the 1.5B model to imitate them | The small model learns from a teacher that already knows how to write sonetos, not from noisy public domain data | Alpaca paper / Self-Instruct |
| **Unsloth** | 2x faster training, 50% less memory via optimized kernels | Proposed 10-min training could become 5 min. Also enables larger LoRA rank in same VRAM | [github.com/unslothai/unsloth](https://github.com/unslothai/unsloth) |
| **Synthetic data augmentation** | Generate variations: change theme, swap synonyms, introduce syllable errors as negative examples | Multiplies effective dataset size without collecting more real poems | Stanford Alpaca recipe |

### Training time estimate — it's actually FASTER than the first run

| | First run | Proposed retraining |
|---|---|---|
| Dataset | 9,622 poems | 200 sonetos (48× smaller) |
| LoRA rank | 16 | 64 (4× more params) |
| Max length | 192 | 256 (33% longer) |
| Epochs | 2 | 10 (5× more) |
| Steps per epoch | 601 | 13 (46× fewer) |
| Total steps | 1,202 | 130 |
| Time per step | ~2.3s | ~4.5s (2× slower) |
| **Total time** | **~52 min** | **~10 min** |

The 48× smaller dataset dominates the 2× slower step time. The retraining would take **~10 minutes**, not longer.

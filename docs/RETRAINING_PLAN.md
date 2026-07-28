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

# All Tunable Parameters in PoesIA

Every lever you can pull to affect generation quality, organized by layer.

## 1. DATA Layer — what the model learns from

| Parameter | Current value | What it controls | Better value | Why |
|---|---|---|---|---|
| Training prompt format | `"Poem:\n{text}"` | How the model associates instructions with output structure | `"Write a {form} in {language}.\nSyllables: {n}.\nRhyme: {scheme}.\n{text}"` | Teaches form→structure mapping explicitly |
| Data quantity | 9,622 poems | Breadth of vocabulary vs focus on form | 200 hand-verified sonetos | Fewer but perfect examples teach structure better |
| Data quality filter | None (all poems accepted) | Noise level in training | Reject: prose, fragments, <10 lines, mixed-language | Clean signal for structural learning |
| Form distribution | Mixed (mostly unstructured) | Which forms the model learns | 100% soneto (first iteration) | Strictest form teaches constraint most clearly |
| Language distribution | 100% ES | Language capability | 100% ES (fine-tune for one language) | Avoids cross-lingual confusion |
| Poet variety | ~50 poets | Stylistic breadth | 5-10 canonical soneto authors (Quevedo, Sor Juana, Lope, Góngora, etc.) | Focused style signal |
| Century/era | 16th-20th | Historical language variety | Golden Age (16th-17th) only | More uniform language patterns |
| Theme annotations | None | Thematic control at inference | Extract theme from first line (e.g. "amor", "naturaleza", "muerte") | Enables `"Write a soneto about {theme}."` |
| Rhyme scheme labels | None | Whether model learns rhyme | Manual annotation of each soneto's scheme (ABBA, ABAB, etc.) | Essential for rhyme generation |
| Syllable count labels | None | Whether model learns metre | Auto-count syllables per line via phonology backend, store as metadata | Essential for metre generation |

## 2. TRAINING Layer — how the model learns

| Parameter | Current value | What it controls | Better value | Why |
|---|---|---|---|---|
| LoRA rank (r) | 16 | How many new parameters to add | 64 | More capacity to encode structural patterns |
| LoRA alpha | 32 | Scale of LoRA updates | 64 | Stronger adaptation signal |
| LoRA target modules | q_proj, k_proj, v_proj, o_proj | Which layers get adapted | All linear layers + gate, up, down projections | Every layer can learn form constraints |
| LoRA dropout | 0.05 | Regularization | 0.1 | Prevent memorization of specific poems |
| Learning rate | 2e-4 | Step size | 1e-4 with cosine decay | More stable convergence for structure learning |
| Learning rate scheduler | Linear | How LR changes over time | Cosine with 10% warmup | Better convergence at end of training |
| Optimizer | AdamW (default) | Weight update algorithm | AdamW with 0.01 weight decay | Stronger regularization |
| Batch size (per device) | 8 | Samples per gradient step | 4 (if VRAM constrained) | More stable gradients |
| Gradient accumulation | 2 | Effective batch size = batch × accum | 4 (effective 16) | Smoother training dynamics |
| Max sequence length | 192 | Maximum tokens per example | 256 (sonetos need ~200 tokens) | Don't truncate the poem |
| Epochs | 2 | How many passes over data | 10 | Model needs repetition to internalize structure |
| Weight decay | 0.0 | Parameter regularization | 0.01 | Prevent overfitting to specific poems |
| Warmup steps | 0 | Steps to ramp up LR | 50 | Stable start to training |
| Gradient checkpointing | False | Memory vs compute tradeoff | True | Frees VRAM for larger batch or model |
| Mixed precision | fp16 | Numerical precision | bf16 (if supported) | More stable training than fp16 |

## 3. MODEL Layer — architecture choices

| Parameter | Current value | What it controls | Better value | Why |
|---|---|---|---|---|
| Base model | Qwen2.5-1.5B-Instruct | Core language capability | Same (1.5B is right for this GPU) | Adequate for focused soneto fine-tune |
| Quantization | 4-bit NF4 | Memory vs precision | Same (4-bit) | Enables the model to fit in 8.6 GB VRAM |
| Compute dtype | bfloat16 | Numerical precision | Same (bf16) | Good balance for training |
| LoRA trainable % | 0.24% (7.4M params) | How much of model is adapted | ~1% (30M params with r=64 + all layers) | More learnable parameters for structural patterns |

## 4. CONSTRAINED LOOP Layer — runtime generation controls

| Parameter | Default | What it controls | Better for fine-tuned model |
|---|---|---|---|
| n_candidates | 16 | How many lines generated per position | 8 (LoRA is slower than Groq, fewer candidates needed) |
| max_repair_attempts | 2 | How many times to try fixing a bad line | 3 (LoRA might produce closer-to-valid lines) |
| temperature | 0.9 | Randomness in generation | 0.7 (lower temperature = more structured output) |
| metre weight | 0.25 | Importance of syllable accuracy | 0.35 (need to enforce metre more strictly) |
| rhyme weight | 0.15 | Importance of rhyme scheme | 0.25 (need to enforce rhyme more strictly) |
| fragment_fidelity weight | 0.15 | Importance of personal context | 0.10 (fine-tuned model needs less context) |
| Language filter | On (threshold=1 word match) | Rejects wrong-language lines | On (same, essential) |
| Few-shot examples | 2 haikus / 1 soneto per brief | In-context learning | 2 sonetos (for soneto generation) |

## 5. PROMPT Layer — what the LLM sees

| Parameter | Current value | What it controls | Better value |
|---|---|---|---|
| Language directive | `"IMPORTANT: You MUST write in {lang}."` | Language adherence | Same (already improved) |
| Quality directive | imagery, metaphor, musicality | Poetic quality | Add: natural word order, avoid forced rhyme |
| Few-shot poems | Lope de Vega soneto (1) | Pattern to imitate | 2 sonetos by different authors (Sor Juana + Quevedo) |
| Form spec detail | Name, lines, syllables, rhyme | Structural constraints | Add: "Each line must be exactly 11 syllables" |
| PERSONAL CONTEXT max | 5 fragments | Context window usage | 3 fragments (leave room for examples) |

## 6. EVALUATION Layer — how we measure success

| Metric | Current | What it measures | Target for "good enough" |
|---|---|---|---|
| Line count accuracy | ~9/14 | Does the model produce the right number of lines | 14/14 |
| Syllable deviation | ~2.5 per line | How far from target syllable count | ≤1 per line average |
| Rhyme accuracy | ~0% | Do lines end with the right rhyme sounds | ≥50% of end words match scheme |
| Language correctness | ~100% | Is the output in the right language | 100% |
| Valid line % (phonology) | ~60% | Lines that pass phonological scan | ≥80% |
| Poetic perplexity | N/A | How natural the language sounds | Measure before/after fine-tune |
| Human preference | N/A | Do you like the output | Subjective |

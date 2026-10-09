# What the CSCS inference key made possible

A ledger of every batch run on the CSCS LLM Inference API during Hack Apertus, with what it
showed. The key was passed on by the Hack Apertus organisers on 2026-10-07 after a late request
(project g233, "Director's Discretion"; models Apertus v1.5 8B and 70B and their -thinking
variants). Access: the key stays in KeePassXC; `dotfiles/bin/secret-proxy` holds it in memory
during a batch and logs every request (`~/.local/state/secret-proxy/usage.csv`); the proxy is
stopped after each batch. Cost: CSCS academic rates (ui.inference.cscs.ch/pricing,
7 Oct 2026): 8B CHF 0.01 / 0.04 and 70B CHF 0.06 / 0.40 per million input / output tokens.

## Batches

| Date | What | Model | Requests | Tokens in / out | CHF | Result |
|---|---|---|---|---|---|---|
| 2026-10-07 | Key check | 8B, 70B | 2 | 180 / 24 | 0.00001 | both answer; 11 models listed |
| 2026-10-07 | Benchmark 1: full precision vs local 4-bit, 18 sonnets × 3 languages | 8B | 7,216 | 1.55 M / 76 k | 0.02 | syllable error lower at full precision in all three languages |
| 2026-10-07 | Benchmark 2: 8B vs 70B, 36 sonnets × 3 languages each, plus a repeat run | 8B, 70B | 28,000 | 6.2 M / 340 k | 0.30 | the 70B is not better behind the engine (metre es 77% vs 85%, it 82% vs 90%); seeds do not reproduce sonnets |
| 2026-10-07 | Safety screen, model question, 60-item set | 8B, 70B, 70B-thinking | 180 | 28 k / 0.4 k | 0.001 | full precision 19/20 vs local 4-bit 13/20: led to the 4-bit → 6-bit finding (benchmark 3, run locally) |
| 2026-10-07 | Suggestion latency | 8B, 70B | ~40 | — | <0.001 | 0.73 s (8B) and 0.99 s (70B) per three-line suggestion |
| 2026-10-08 | Independent safety test set: 1,043 reflections, 7 categories, 5 languages, written and then classified by the 70B | 70B | 2,121 | 0.42 M / 34 k | 0.04 | 724 items where writer and judge agree; `data/safety/generated/` |
| 2026-10-08 | Safety screen on that set | 8B, 70B | 3,534 | 0.42 M / 5 k | 0.01 | **the screen catches 78 of 280 risk texts (28%)**; the 20/20 on the author's own 60 items was overfitted. Passive death wishes and indirect signs are missed |
| 2026-10-08 | Held-out safety set (seed 1000, written before the screen was changed): 1,040 items, 708 agreed | 70B | ~2,100 | ~0.4 M / 34 k | ~0.04 | no overlap with the tuning set |
| 2026-10-08 | Screen before/after on the held-out set, plus tuning runs | 8B | ~4,500 | ~0.6 M / 5 k | ~0.01 | **recall 92 → 125 of 271 (34% → 46%), false alarms 6 → 4 of 437**; plain death wishes 50% → 72% |
| 2026-10-08 | Two more seed sets (6, 9) of the 8B benchmark: the full-precision reference now has 72 sonnets per language | 8B | ~19,000 (incl. late safety re-checks) | 4.05 M / 160 k | 0.05 | metre es 84.5 ± 1.2%, en 92.2 ± 0.8%, it 89.3 ± 1.0% |
| 2026-10-08 | Probe: can the 70B mark Italian word stress (to build a stress dictionary for the scanner)? Three prompt formats, 20 words | 70B | 3 | ~1 k / 1 k | <0.001 | **no**: about half wrong with accents (*tavóla*, *perdíta*, *subító*), nearly all "piana" with capitalised syllables, nearly all "tronca" when asked the type; not used. Wiktionary's pronunciations are the source instead |
| 2026-10-09 | Another session's batch, 09:57-10:23 (purpose not recorded in this ledger) | 8B, 70B | 10,341 | - | 0.22 | - |
| 2026-10-09 | German and French sonnets, 36 per language per model, seeds 0 and 3 | 8B, 70B | 19,979 | 4.4 M / 261 k | 0.22 | metre de/fr: 8B 84.7% / 88.1%, 70B 94.8% / 85.3%; **the 8B writes English lines in 10-13% of de/fr lines at full precision (the 70B in 1-2%)**, so the leak is the model's, not the quantisation's |

Running total (proxy log, 2026-10-09 11:00): **89,973 requests, CHF 0.88.**

## What it changed in PoesIA

- **Model size:** the 70B was measured as no better at metre behind the deterministic engine;
  the entry stays on the 8B. A finding a single 8 GB card could never have produced.
- **Quantisation:** full-precision answers exposed that the shipped 4-bit model loses safety
  recall (13/20 vs 19/20) and Italian metre; 6-bit recovers both (benchmark 3).
- **Safety:** an independent, larger test set showed the screen misses most risk texts it was
  not written alongside. Being fixed with a tuning set and a fresh held-out set (below).
- **Languages:** German and French behind the engine score in the range of Spanish and Italian,
  and the full-precision runs showed that the 8B's habit of slipping into English is the
  model's, not the 4-bit file's; the 70B almost never does it.
- **Sovereign-cloud option:** the page runs against CSCS unchanged (`LLM_BASE_URL`), measured
  at 0.73 s per suggestion; the report offers it as a deployment option for public bodies.

## Still to run (planned)

- ~~Safety screen: tune on the 2026-10-08 set, test on a fresh set~~ done 2026-10-08 (above).
- ~~The shipped 4-bit and the 6-bit model on the held-out set~~ done 2026-10-08 on Hugging Face
  Jobs (L4, job 6ac7b562): screen 4-bit 109/271, 6-bit 129/271, full precision on CSCS 125/271;
  false alarms 2, 4 and 4 of 437 (`reports/eval_2026-10/b6-hfjobs-safety-q4-q6.json`).
- ~~More benchmark seeds for the report's tables~~ done (72 sonnets per language).

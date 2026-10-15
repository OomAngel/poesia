# Tuning rounds: line, rhyme pair, stanza, whole poem (plan, 2026-10-14)

What a poem must be is in `POETICS.md` (Angel's criteria). How to gate, rank and measure it is in
the quality-layer research (`docs/research/reports/PoesIA shared poem quality layer.md`, branch
`calaveritas`; the code is `poesia.quality` on branch `quality-layer`). This plan applies both to
tuning Apertus, at four levels, because a poem is not good line by line: the rhyme lives in pairs,
the idea in stanzas, the gist and the ending in the whole poem (Angel, 2026-10-14: "coherence,
metric and rhyme not only per verse, but in rhyming pairs, per paragraph and per the whole poem").

Lessons that bind every round (RETRAINING_PLAN, lessons note 2026-10-10, b12, b13, b14):

- Train on human answers in the exact request shape the deployment sends; teacher lines only as
  augmentation; never on lines just because they passed the engine (v1: openings 129 -> 21).
- Cap diversity across the whole set (openings, end words), not per poem.
- No score acts alone as a gate unless it has been shown to separate good from bad on controls
  (the July validator scored every sonnet 1.0; e5 cosines vary by 0.02).
- Coherence alone rewards repetition: the 8B's poems are *more* self-similar than real ones
  (b13: AUC 0.92-0.99 for every embedding model), so coherence is always paired with a repetition
  penalty, and measured after centring.
- No embedding judges sense (b13: real line vs its words shuffled, AUC 0.53-0.61). Sense needs a
  judge, from a different model family than the generator.
- An adapter is adopted only if it beats the plain model on all four levels and wins Angel's
  blind comparison on a small sample.

## 1. What is measured at each level

| Level | Metre | Rhyme | Sense and coherence | Diversity and repetition |
|---|---|---|---|---|
| **Line** | exact by the corrected counter, licensed set allowed (`spanish_metre.py`, ADSO 93.5%) | n/a | grammar (correct-and-compare) and the sense judge; gates: fragment, tacked-on word, dangling function word, language, vocabulary | openings: distinct share, top-opening share |
| **Rhyme pair** (the two lines a scheme letter joins) | both lines | by phonetic key; distinct words, no near-copy or prefix (POETICS #2); the rhyme word earned, not forced (share of bank words vs the poets' share) | the second line follows from the first (two-line window, centred embedding); no word order bent for the rhyme (judge, POETICS #4/#8) | end-word concentration across poems |
| **Stanza** | share of lines exact | the stanza's scheme | one idea or scene (adherence to the stanza thought or plan, centred embedding); the sentence closes (judge) | redundancy inside the stanza (embedding sameness, b13); no repeated content words (POETICS #3) |
| **Whole poem** | pass budget: at least 90% exact, none off by more than one | full scheme | theme fit to the request (centred, poem level: AUC 0.93 in the quality-layer research); development: stanzas move, do not restate; a strong ending (POETICS #10; judge, then Angel) | repetition across the poem (b13); diversity against human poems of the same form (nearest-neighbour similarity, openings, end words); no copy of a corpus poem (Ratcliff-Obershelp >= 0.7) |

Every instrument is checked on controls before it is used:

- **positive:** real poets' lines, pairs, stanzas and poems should pass;
- **negative:**
  - shuffled words (sense);
  - swapped lines from another poem (pair and stanza coherence);
  - stanzas in shuffled order (development);
  - adapter v1's forced-rhyme lines (rhyme earned);
  - the 8B's repetitive poems (repetition).

A score that cannot separate a control pair is not used, and the plan says so.

## 1a. Measured so far (2026-10-14)

**R0 scorecard** (`scripts/poem_scorecard.py`, `reports/eval_2026-10/b17-scorecard.json`; LaBSE, centred;
120 human poems and 36 of the plain 8B's sonnets per language, first 12 lines). At line level the 8B
is near the poets (metre at the modal count: es 85% vs 89%). Above the line it is far:

| Level | Measure | Human (es/it/de/fr) | Plain 8B |
|---|---|---|---|
| pair | rhyme on the same word or a near copy | 6-13% | 8-29% |
| pair | the two lines restate each other (centred cosine) | 0.07-0.12 | 0.35-0.41 |
| stanza | redundancy inside the stanza | 0.06-0.10 | 0.32-0.37 |
| stanza | content words repeated per stanza | 0.2-0.5 | 0.8-1.4 |
| poem | consecutive stanzas restate (lower develops) | 0.18-0.25 | 0.58-0.64 |
| poem | content words repeated per poem | 1.3-2.8 | 4.1-7.3 |
| across poems | share of the ten most common end words | 4-6% | 15-20% |

Read as targets: the human column, per level. "Pair coherence" by cosine measures restatement, not
whether the second line follows: poets' paired lines are far apart in meaning and still belong.

**Sense judges** (`scripts/sense_judge_validation.py`, `b16-sense-judges.json`). The hackathon CSCS
key is authorised only for Apertus (Gemma, GLM and Nemotron are listed but refused), so no
cross-family judge is available: self-preference is a known limitation. Apertus 70B, one-word
verdict, Spanish: real lines pass 90%, shuffled 8%, spliced halves 36% (balanced accuracy 0.84); the
8B's lines pass 90%, like the poets'. So the judge *rejects* word salad and cannot *rank*: it gates,
Angel's blind rating decides. Italian: it rejects 40% of real (older) lines, so it cannot gate
Italian training data. Correct-and-compare is weaker (es 0.73, it 0.59).

## 1b. Adapter v3 (R1 + R2), measured 2026-10-15

Trained on Kaggle (2 x T4, fp32, half a pass over 10,242 real-poem lines, 5.2 h; held-out loss on
poets' lines 5.55 -> 3.02). Evaluated on the 4-bit file with and without it (`b20`, 36 sonnets per
language), at four levels (`b21`) and for sense (`b22`, Apertus 70B verdict, 150 lines):

| | es | it | de | fr |
|---|---|---|---|---|
| metre, plain -> adapter | 86 -> 93% | 83 -> 96% | 84 -> 95% | 90 -> 87% |
| rhyme | 58 -> 66% | 49 -> 68% | 62 -> 51% | 59 -> 54% |
| stanzas restate (human 0.18-0.25) | 0.55 -> 0.42 | 0.57 -> 0.40 | 0.66 -> 0.40 | 0.60 -> 0.41 |
| repeated content words per poem | 4.6 -> 2.6 | 5.6 -> 4.6 | 8.7 -> 5.6 | 6.1 -> 5.0 |
| **lines the judge calls sense** (poets ~90%) | **93 -> 68%** | (judge unreliable) | **91 -> 64%** | 93 -> 89% |

### What v3 brought, and why (2026-10-15)

**What improved, and why.** v3 was trained only on poets' own lines, in the request the page
sends, with caps on openings and end words across the set and the POETICS filters (no near-copy
rhymes, few repeated words, rhymed metrical poems). It learned the poets' habits above the line:

- *It develops instead of restating.* Consecutive stanzas went from 0.55-0.66 to 0.40-0.42
  (poets 0.18-0.25), and repetition across the poem roughly halved. Why: each training answer
  is a poet's next line given the lines before it, and poets move on; the plain 8B, prompted line
  by line, keeps paraphrasing the theme.
- *It repeats fewer words and spreads its rhymes.* Content words repeated per poem fell (es 4.6 ->
  2.6, de 8.7 -> 5.6); the share of the ten most common end words fell (it 24% -> 9%). Why: the
  answers had capped end words and were filtered for repeated words, so the familiar rhyme words
  ("serena", "arena") lost their weight.
- *Metre and rhyme rose in Spanish and Italian* (es 86 -> 93% metre, 58 -> 66% rhyme; it 83 -> 96%,
  49 -> 68%). Why: the data was metrical by the corrected counter, and half of it was the
  "close the rhyme pair" request with the poet's own rhyme word as the answer.

**What worsened, and why.**

- *Sense.* The judge passes 68% of the adapter's Spanish lines against 93% for the plain model
  and about 90% for the poets (de 91 -> 64%, fr 93 -> 89%). Two causes, measured separately:
  1. **Unfinished lines (measured).** The adapter closes fewer lines with punctuation (es 67 -> 55%,
     de 98 -> 67%, fr 88 -> 63%; the training answers close 65-75%). Poets carry a sentence over
     the line break; as single-line answers, those taught the model to stop mid-thought, and a
     line that stops mid-thought fails as a stand-alone proposal. The judge passes the adapter's
     open lines less often (es 57%, de 57%) than its closed ones.
  2. **Worse even when the line closes (measured; cause is a hypothesis).** Closed lines pass
     74% (es) and 68% (de) against 94% and 91% for the plain model. Most likely: poets' lines are
     hard to predict (held-out loss stays at 3.0, against 1.66 for v1's teacher lines), so training
     toward them flattens the model's word choices, and at the same sampling temperature (0.9)
     more picks go wrong: odd syntax, invented forms ("aufgehebt", "befreuen", "desasalta"),
     occasional stutter. Untested alternatives: imitation of 19th-century syntax without the
     poets' control of it; training on NF4 and serving on Q4_K_M.
- *German openings collapsed* (distinct openings 0.36 -> 0.20) and near-copy rhymes rose
  (26 -> 34%). Why, likely: the German pool is the smallest and most uniform (DLK, 19th century),
  so the caps bit less and its habits dominated.
- *French metre fell* (90 -> 87%). Likely: the smallest pool (143 poems) and classical counting
  (mute e) that the other languages' data does not teach.

**What this means for v4.** Keep what worked (poets' lines, caps, the pair request). Fix the two
measured causes one at a time: (a) answers that close their clause for the proposal request, and
(b) a lower sampling temperature for the adapter, tested first on v3 itself (no training).
**Not adopted.**

Instruments added or dropped on the way: stutter is measured (a content word three times in a line,
or twice in a row: adapter 0.2-2.5% of lines, plain 0-0.2%). Two "invented word" measures do not
separate: words outside the 40k list (the poets use 9-21%, more than either model), and words absent
from both the list and the training poems (it catches ordinary conjugations, "acarician", and the
plain model's English, "cloaks"). Neither is used until it passes a control.

## 2. Rounds

Each round adds one request shape that a real inference path sends, built from human poems, and
is evaluated on all four levels, not only its own.

| Round | Request shape (= what the deployment sends) | Answer | Consumer |
|---|---|---|---|
| **R0 baseline** | none: plain Apertus 8B behind the engine, improved prompt (quality directive in the poem's language) | | the scorecard: 8B vs human poems at four levels |
| **R1 line** | the page's line prompt (prior lines, syllables, rhyme partner "or your own") | the poet's line | page proposals, loop line requests |
| **R2 rhyme pair** | close a pair: prior lines + the partner line, the rhyme sound named, a bank offered "or your own"; and pair repair: both lines given, rewrite the second so the pair rhymes on a different word without breaking sense | the poet's closing line | page proposals for a pair's second line; loop repair |
| **R3 stanza** | write the next stanza from the poem so far and a stanza thought (the page's optional thought per stanza) | the poet's stanza | "draft all lines as a starting point", stanza by stanza; calaveritas stanza drafts |
| **R4 plan and poem** | plan: one idea per stanza and the ending, from the theme and reflection; then the poem from the plan | a plan summarised from the real poem by a teacher (the only synthetic part), the poet's poem | whole-draft path; calaveritas plan call |
| **R5 preference** (later) | pairs of drafts at stanza and poem level | Angel's blind choice | DivPO-style pairs (rare-but-good over common), only after a few hundred blind pairs |

**Data per round** (corpus_master es/en, Biblioteca Italiana, DLK, Métrique en Ligne; any poem
may go into the private training set, Angel 2026-10-10; poems never in git, DVC only):

- the POETICS filters:
  - rhymed stanzas where every scheme line rhymes;
  - no near-copy rhymes;
  - no repeated content words;
  - modal metre.
- Spanish weighted toward Angel's poets (`data/influences.yaml`: 4,129 poems in the Spanish corpus);
- caps across the set: openings 5%, end words 2%;
- benchmark themes held out, plus 600 lines, 200 pairs, 100 stanzas and 50 poems per language for
  the judge against real poems.

**Training:** one QLoRA adapter for Apertus v1.5 8B. The shapes are mixed (R1 + R2 first, R3 and R4
added as their data passes its checks), so one adapter serves all paths through `--lora`.
Kaggle 2 x T4 in fp32 (Apertus overflows fp16), stop-and-save at 10 h,
answer-only loss with the end token labelled, held-out loss per shape.

**Adoption:** the adapter replaces the plain model only if, on the seeded benchmark, it is no worse
on form at every level, better on sense and on diversity, its lines beat the plain model's more
often against real poets' lines (the judge), and Angel prefers it in a blind sample.

## 3. Order, and what fits before 17 Oct

1. Sense instrument (now): correct-and-compare and a cross-family judge (Gemma 4 31B, GLM 5.3,
   Nemotron 3 Super on the CSCS key; Apertus 70B for comparison), validated on the controls
   above. Shared with Calaveritas, whose own sense check does not separate (quality-layer note,
   2026-10-14).
2. The four-level scorecard script; R0 baselines for human poems and the plain 8B.
3. R1 + R2 data to POETICS, then a Kaggle run (unattended, free).
4. Page ranking: gates, then sense, then form distance; repetition penalty (needs an embedding
   at runtime only where one is available; on the Veriton the page has none unless the desktop serves it).
5. R3 and R4 data and the second Kaggle run: after the trip unless time allows.

The Hack Apertus entry does not wait for any adapter: it ships the plain model. A round that
wins before Friday is reported as a finding; a round that does not is reported too.

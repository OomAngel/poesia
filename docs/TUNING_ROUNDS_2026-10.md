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

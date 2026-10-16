# Tuning rounds: line, rhyme pair, stanza, whole poem (plan, 2026-10-14)

## Continue here (retired 2026-10-16, for the "PoesIA models" session)

The Hack Apertus session retired after the submission (16 Oct, before 12:00; winners 23 Oct). This
file is the entry point for the model work; §1 and §1a-§1c hold every measured result, the research
behind the next steps is `docs/research/reports/Improving PoesIA poetry models.md` (ordered plan in its
last section; references with Zotero keys next to it). Scope: tuning rounds, evaluation instruments,
the shared `poesia.quality` layer and merging the `quality-layer` branch into this engine branch.
The Calaveritas service stays with its own session (worktree `~/dev/poesia-quality`, branch
`quality-layer`, live on the Veriton until 4 Nov): coordinate the merge with it, never deploy its
service from here.

**Update 2026-10-17 00:45 (PoesIA models session):** v5 trained, uploaded (`line-v5.gguf` is the only
file of the Kaggle dataset `poesia-line-adapter-gguf`) and evaluated; result in **§1d: not adopted**
(above-line gains lost in es/it/fr, German openings still collapsed). Sense for v5 waits for the CSCS
proxy, which was down (sense then measured: level with plain in es/fr, 6 points down in de). The bullets
below describe the state at hand-over.

**Done after that, same night (17 Oct):**
- **Ranking penalties built, off by default** (`d6f593f`, `8ef1019`): `evaluation/rank_penalties.py`
  ranks a candidate down by `repeat_weight` per content word the poem already used (capped at 4) and
  by `opening_weight` when its first word opened an earlier line or one of the last N poems; the
  loop and scorer take them as an optional argument, the benchmark as `--repeat-weight`,
  `--opening-weight`, `--recent-poems`. The page already did both within one poem
  (`webapp._proposal_rank`); the loop did not. Weights are movable defaults, not findings.
- **The measurement has not run:** Kaggle refused the push ("Maximum weekly GPU quota of 30.00
  hours reached"; v5 training and eval used it). When the quota is back, one command runs plain
  against plain-with-penalties on the same seeds (about 2 h 10, no key needed):
  `scripts/kaggle/push_eval.sh HEAD 0.6 0.03,0.08` (results `plain-*` and `pen-*`; score with
  `poem_scorecard.py --extra` as in §1d). The CSCS 8B could run it instead, but that is a hackathon
  key and Angel has not said it may be used for a benchmark campaign.
- **`quality-layer` merged locally, not pushed:** branch `merge-quality-layer-0417` (worktree
  `~/dev/poesia-merge-0417`, merge commit `d4126c9` on top of `4d12401`), one conflict
  (`memory-bank/activeContext.md`, both sections kept), full suite green. **Do not push it:** the
  history carries private material (Calaveritas session, 17 Oct): `memory-bank/activeContext.md`
  entries (Nebius credit and spend, Veriton rollback commands, a claude.ai review link, the CSCS-key
  question), `docs/research/reports/Calaveritas hosting Apertus and corpus.md` and its research
  notes (Veriton internals), `PoesIA calaveritas site design.md` (artifact link), `PoesIA shared
  poem quality layer.md` (container limits), `docs/calaveritas/DECISIONS.md`, a comment in
  `docker/calaveritas.Dockerfile`. A merge publishes the whole history; the clean route is a
  code-only branch (src, tests, scripts, pyproject, fonts, a scrubbed memory-bank entry). Angel decides.
  The Spanish metre counter changed in that branch, so Spanish baselines must be rerun after it.
- The bullets below describe the state at hand-over.

**State, verified 2026-10-16 17:00:**
- Branch `hack-apertus`, last own commits `352f9d7` (v5 data), `fa8b302` (§1c), pushed.
- **v5 training is running on Kaggle** (kernel `angelmarquezaguilar/poesia-line-adapter` version 13,
  started 16:06 CEST, expected end 20:15-20:30): v4's recipe, only sentence-closing answers (no final
  comma), openings capped at 3%, 4,844 lines (`data/distill/apertus-lines-v5-2026-10-16.jsonl`, DVC),
  one full pass, weights from the private Kaggle dataset `apertus-v1-5-8b-text` (no secret, starts
  from the API).
- v4 (§1c): Spanish sense at parity with the plain model at temperature 0.6, smaller above-line gains,
  openings collapsed: not adopted. Angel's blind rating page (plain vs v4, Spanish, 20 pairs) is
  https://claude.ai/artifact/WXtt44ieDVguhYhfYzgKkf; ratings arrive in its `ratings` collection
  (read with ArtifactData); the key (which side is v4) is `data/distill/blind-key-v4-es-2026-10-16.json`
  (git-ignored, never publish before the ratings are in). Angel rates "bit by bit": do not wait on it.
- The CSCS proxy (127.0.0.1:8790) was started by another session; usage log
  `~/.local/state/secret-proxy/usage.csv`. If it is down, Angel starts it (KeePassXC prompt in a
  Windows Terminal tab: `with-secret "Hack Apertus/CSCS inference key" PROXY_KEY -- secret-proxy
  https://api.inference.cscs.ch 8790`); describe the prompt and wait for his "ready" first. Only Apertus
  models are authorised on this key. Whether it works after the hackathon is asked in an Outlook draft
  Angel sends.

**First commands:**
```bash
git -C ~/dev/poesia log --oneline -3                      # hack-apertus at or after 352f9d7
K=$(ls ~/.cache/uv/archive-v0/*/bin/kaggle | head -1); (cd /tmp && $K kernels status angelmarquezaguilar/poesia-line-adapter)
# when COMPLETE (Kaggle gives the log only at the end):
mkdir -p /tmp/v5 && (cd /tmp && $K kernels output angelmarquezaguilar/poesia-line-adapter -p /tmp/v5)
cd ~/dev/poesia && scripts/kaggle/upload_adapter.sh /tmp/v5/adapter line-v5 /tmp/v5/train_log.json
scripts/kaggle/push_eval.sh HEAD 0.6                      # eval v5 vs plain, about 2 h 10
# then, as for v4 (results into reports/eval_2026-10/b29-...):
#   poem_scorecard.py --extra "name=<glob with {lang}>" ... ; LLM_BASE_URL=http://127.0.0.1:8790/v1 sense_compare.py --runs ...
```
Both scripts take `DRY_RUN=1` to show what they would do. Kaggle runs share the account's free
weekly GPU hours (about 30; this week used roughly 25 by 16 Oct).

**Rules that bite:** poems and corpus never in git (DVC only); the engine branch is public on GitHub;
no AI attribution in commits; commit by path; no local GPU (Kaggle or CSCS only); a score is used only
after it separates a control pair (§1); the sense judge rejects but cannot rank; Angel's blind rating
decides adoption. Watch Kaggle with a loop that stops only on COMPLETE/ERROR (a DNS hiccup once ended a
watcher early).

**Open for Angel** (most consequential first):
1. Blind rating of v4 (page above): decides whether any adapter goes into the page.
2. Merge `quality-layer` into the engine: touches the live Calaveritas service; its session planned it
   "after Hack Apertus".
3. Continued CSCS access: his Outlook draft "PoesIA submitted: may I keep using the CSCS key…" (delete
   the older 15 Oct draft "CSCS key: end date…" before sending).
4. A stronger drafting model for PoesIA: the Calaveritas session measured Qwen 27B (Groq) at 90% of
   Spanish lines in metre against 34% for Apertus 70B, raw drafts; PoesIA's entry is built on Apertus.
5. Zotero: 96 PDFs of this research wait for one "Always Allow" click (rerun command in
   `research-tools/results/zotero-capture/poesia-poetry-models-2026-10-16/pdf_pending.json`).


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

## 1c. Temperature 0.6 on v3, and adapter v4 (2026-10-16)

The research report (`docs/research/reports/Improving PoesIA poetry models.md`) put the cheapest test
first: sample v3 at 0.6 instead of 0.9 (`b23`, `b24`, `b25`). Then v4 (`b26`-`b28`): the same recipe
trained only on answers that end in punctuation (8,922 lines; 4.2 h; held-out loss 5.42 -> 2.94).
All at temperature 0.6, 4-bit, 36 sonnets per language; sense = Apertus 70B verdict on 150 lines.

| es | plain | v3 @0.9 | v3 @0.6 | v4 @0.6 |
|---|---|---|---|---|
| sense (poets ~90%) | 90-93% | 68% | 81% | **91%** |
| metre / rhyme | 83-86% / 58-66% | 93% / 66% | 92% / 74% | 91% / 61% |
| stanzas restate (human 0.23) | 0.55-0.61 | 0.42 | 0.52 | 0.56 |
| repeated content words per poem (human 1.3) | 4.4-5.1 | 2.6 | 3.3 | 4.1 |
| top-10 end-word share (human 5%) | 24% | 13% | 13% | 14% |
| distinct openings across poems (human 0.35) | 0.19 | 0.14 | 0.14 | 0.14 |

German: sense plain 89%, v3 71%, v4 81%; French: 97%, 83%, 93%. Italian: no reliable judge.

- **Temperature is a dial, not a fix:** at 0.6 v3 regains half its lost sense and gives back half its
  development gain.
- **v4 holds sense** (es at parity, de and fr closer) and keeps a smaller part of the gains: fewer
  repeated words and end words than plain, slightly better development, metre +7 points in es.
- **Red flag: openings collapse.** Distinct openings across poems fall in every language (it 0.27 ->
  0.15, de 0.32 -> 0.11), the warning sign from v1; near-copy rhymes rise in de and fr; rhyme falls
  in es (66 -> 61%) and fr (63 -> 48%); French metre falls.
- **Filter flaw:** the "closing" test counted a final comma as closing, so lines that run on past a
  comma stayed in (the control answer "Der Herbst ist gekommen,"). v5 should count only . ; : ! ?
  and closing quotes.
- **Not adopted.** v4 (Spanish) is the first adapter worth Angel's blind rating against the plain
  model; the opening collapse must be fixed (caps per language and per position, and a ranking
  penalty on openings used across recent poems) before adoption.

## 1d. Adapter v5: sentence-closing answers only, openings capped at 3% (2026-10-17)

v4's recipe with two data changes: only answers that end in . ; : ! ? or a closing quote count as
closing (v4 counted a final comma), and openings capped at 3% across the set (`352f9d7`). 4,844
lines, one full pass over 288 steps, 5.2 h on Kaggle, held-out loss 5.58 -> 2.94 (v4: 2.94).
Evaluated as v4 was: 4-bit, temperature 0.6, 36 sonnets per language, seeds 0 and 3
(`b29-kaggle-q4-adapter-v5-t06`, kernel version 9; the adapter control passed: `line-v5.gguf`
mounted, and at temperature 0 it answers differently from the plain server). Scorecard:
`b30-scorecard-adapter-v5-t06.json`, which holds both plain runs (b26 and b29) as a noise gauge:
two runs of the *same* plain model differ by up to 0.12 in a pair measure (de near-copy rhymes
0.45 vs 0.33) at n = 36, so only gaps larger than that count.

| es | human | plain b26 / b29 | v4 | v5 |
|---|---|---|---|---|
| metre at the modal count | 0.89 | 0.84 / 0.85 | 0.91 | 0.88 |
| rhyme (lines rhyming within the group) | 0.57 | 0.51 / 0.45 | 0.51 | 0.61 |
| near-copy rhymes | 0.06 | 0.30 / 0.26 | 0.25 | 0.33 |
| pair: second line restates the first | 0.10 | 0.37 / 0.38 | 0.37 | **0.54** |
| stanza redundancy | 0.08 | 0.32 / 0.32 | 0.33 | **0.49** |
| content words repeated per stanza | 0.17 | 0.94 / 0.94 | 1.19 | **1.47** |
| consecutive stanzas restate (lower develops) | 0.23 | 0.61 / 0.60 | 0.57 | **0.68** |
| content words repeated per poem | 1.3 | 5.1 / 5.2 | 4.1 | 3.8 |
| distinct openings across poems | 0.35 | 0.19 / 0.16 | 0.14 | 0.14 |
| top-10 end-word share | 0.05 | 0.24 / 0.23 | 0.14 | 0.19 |

Other languages, v5 against the two plain runs (plain b26 / b29):

- **Above the line, v5 is worse than plain in Spanish, Italian and French; German is the
  exception.** Stanza redundancy it 0.42 (plain 0.36 / 0.37), fr 0.45 (0.35 / 0.34); consecutive
  stanzas restate it 0.65 (plain 0.58), fr 0.71 (0.63 / 0.64); content words repeated per stanza
  it 1.8 (1.4 / 1.2), fr 1.7 (1.4 / 1.2). In German v5 is level with or slightly better than plain
  (redundancy 0.40 vs 0.40 / 0.42, consecutive stanzas 0.61 vs 0.68 / 0.68, words per stanza 1.9
  vs 2.4 / 2.2), but not better than v4 (0.31, 0.57, 1.8). Repeated words per poem and end-word
  spread improve everywhere (es 3.8 vs 5.1; it top-10 0.13 vs 0.29 / 0.31). The pair measure
  (second line restates the first) rises only in Spanish (0.54 vs 0.37 / 0.38) and French
  (0.58 vs 0.41 / 0.42). v3's and v4's development gain is gone outside German.
- **Near-copy rhymes rose: fr 0.50 against plain 0.21-0.24 (v4 0.33), de 0.53 (plain 0.33-0.45).**
  French rhyme fell to 0.36 (plain 0.45); French metre is back to plain (0.85).
- **Metre up in it (0.95 vs 0.83-0.85) and de (0.96 vs 0.83-0.85), as in v4.**
- **Stutter** (a content word three times in a line, or twice in a row): de 5.1% and fr 1.6% of
  lines against 0% for plain; v4 was de 3.2%.
- **Openings:** the 3% cap in the data did not fix German (0.11 against plain 0.29 / 0.32, v4
  0.11). It restored Italian partway (0.21 against plain 0.27 / 0.29, v4 0.15). Spanish sits at plain's level
  (0.14 vs 0.16-0.19) and French above it (0.11 vs 0.05-0.07), but both plain models are far
  from the human 0.30-0.35, so the collapse that matters is German and Italian.

**Reading.** v5 does not beat the plain model at all four levels, so it is **not adopted**, with or
without the sense judge (the judge can reject further, it cannot rescue). Measured: the closing-only
filter did not keep v4's above-line gains in Spanish, Italian and French; it lost them. Cause, a
hypothesis not yet tested: answers that always close their sentence are self-contained statements
about the theme, and a model that writes self-contained lines restates more, which is what
poets' enjambed lines do not do. v4 (with its comma-closing lines) kept part of the development
gain; v5 did not. The caps fixed end words and Italian openings, not German openings.

**Sense (Apertus 70B verdict, 150 lines per cell, `b31-sense-adapter-v5-t06.json`; measured after
Angel restarted the proxy on 17 Oct; a first attempt while it was down answered 0 of 150 and was
discarded):**

| | plain (b29) | v5 | v4 (b28; plain 0.90 / 0.89 / 0.97) |
|---|---|---|---|
| es | 91.3% | 94.7% | 91.3% |
| de | 87.3% | 81.3% | 80.7% |
| fr | 95.3% | 97.3% | 92.7% |

Sampling error on 150 lines is about 2-3 points per cell (about 4 on a difference), so v5 is level
with plain in Spanish and French and about 6 points down in German, as v4 was. The judge rejects
broken lines and cannot rank good ones (§1a), so this says v5 did not break its lines; it does not
say they are better. The filter flaw that v5 fixed (final comma) did not move German sense. The
verdict stays **not adopted**: sense holds, the above-line levels do not.

**Angel's blind rating of v4 so far (2 of 20 pairs, 16 Oct):** one pick for v4 ("the verses of B
other than the repeated beginning are more logical and rhyme better"; B = v4), one tie. He
noticed the opening collapse unprompted ("every single verse starts the same way"). Two pairs
decide nothing; the rating continues.

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

# PoesIA's Position — The Instrument, Not the Author

> *Last updated: 2026-08-05.* This document is the **source of truth for why
> PoesIA exists**. It was written in response to a fair critique: the repo reads,
> on first impression, as "a machine that writes poetry" — and creating poems is,
> and should be, a human thing. The critique is accepted. This document records
> the human purpose, the landscape evidence that the position is unoccupied, and
> the design consequences of actually embodying it.

---

## 1. The position, in one sentence

> **PoesIA is an instrument for letting things out.** You bring what you carry —
> a thought, a feeling, a grievance, a joy that never became words. PoesIA gives
> it the shape of poetry and, in the shaping, teaches you the craft — so that it
> needs you a little less each time.

This is a **creative-expression instrument for everyone** — with a natural
audience in **IT and technical people**, who live in a world where feelings
rarely become words. It is not a tool "for writers." It is for the person who
has never written a line and has a poem inside them anyway.

---

## 2. What PoesIA is NOT

- **Not a poem generator.** Machine output is *draft*, *proposal*, *scaffold*.
  The poem is what the human decides to keep.
- **Not "AI that writes poetry."** The AI holds the craft and can hold a pen —
  it never holds the authorship.
- **Not for producing publishable verse on demand.**
- **Not therapy**, and it makes no therapeutic claims. (The expressive-writing
  research in §5 is context for why the *outlet* matters — it is not a license
  to sell healing.)
- **Not a technical trophy.** Its results (73% formal validity, 410 tests) exist
  to serve the teaching role, not as the product.

**The question every feature must answer: *who is the author?*** If the answer
ever drifts to the machine, the feature is mis-framed.

---

## 3. The human goal: four movements

1. **Outlet** — you drop thoughts, feelings, emotions as they are. No audience,
   no grade, no publication. Private by default.
2. **Shaping** — raw feeling becomes a *made thing*: form, sound, rhythm.
   Release becomes creation. (This is what separates PoesIA from a diary: the
   diary pours; PoesIA makes.)
3. **Teaching** — the deterministic phonology/evaluation spine explains *why*
   and *how to fix*: syllables, sinalefa, stress, rhyme. Every session leaves
   the person more able than before. The instrument's goal is to be needed a
   little less each time.
4. **Linking** — the person connects to poetry itself: the tradition
   (influences, forms with centuries of history), and their own voice over time
   (`memoria`, the library).

---

## 4. Who it is for

**Everyone** — and especially **technical people**.

The bridge is a metaphor they already live in: **a linter for poetry.** A
developer knows the loop: write → run the check → read *why* it failed → fix →
green. PoesIA's phonology/evaluation spine *is* that loop. The "lint" is
syllable count, stress and rhyme; the "fix" teaches sinalefa and scansion in
human language (`ScanResult.violations` are already human-readable).

The cultural evidence that technical people hunger for poetic expression is
real and documented: esoteric programming languages as poetry (esoteric.codes,
Daniel Temkin), computational-poetry journals (Taper), `xchg rax, rax`, the
long tradition of "code poems." The hunger exists; **nobody has handed them an
accessible instrument** — one that meets them on familiar ground (offline,
deterministic, reproducible, private) and leads them into the craft.

No prior poetry knowledge is required: `poesia scan` gives feedback in human
language, and generation is optional scaffolding, never a requirement.

---

## 5. The landscape (researched 2026-08-05)

What already exists, in six families:

| Family | Examples | Who writes | What's missing |
|---|---|---|---|
| **Private journaling / raw outlet** | 750 Words, Penzu, Day One, Reflectly, Mindsera, Morning Pages (Julia Cameron), Freewrite | Human | Outlet only — *nothing is made*. No shaping into form, no craft, no beauty, no teaching |
| **Self-knowledge essays** | Self-Authoring Suite (Peterson/Higgins/Pihl), Pennebaker protocols | Human | Prose; purpose is insight/planning — not *creation* |
| **Companion AIs** | Replika (~40M users), Pi | AI talks back | Outlet through *conversation* — nothing is created, nothing taught |
| **AI for professional writers** | Sudowrite, NovelAI | Human directs, machine drafts | Built for novelists/screenwriters; prose; production-oriented, not expression-oriented |
| **AI poetry where the human is the poet** | **Verse by Verse** (Google, 2020) — you write each line, the AI suggests continuations in the voice of Dickinson, Whitman, Poe | Human | Closest cousin — but a museum experiment: no validation, no teaching-*why*, no aftercare, no library; sunset |
| **Art precedents** | **PoemPortraits** (Es Devlin + Ross Goodwin, 2019, Barbican): you donate a word, the machine composes; every poem joins a *collective poem* | Human seeds, machine composes | Installation art, not an instrument; the human gives one word, the machine holds the pen |

Two adjacent references deserve explicit notes:

- **Self-Authoring Suite** (the "Essay by the Petersons") is *self-knowledge*,
  not creative expression: structured essays on your past, faults, virtues and
  future, with real measured outcomes. It proves guided writing works — and it
  is a different species from what PoesIA is.
- **Pennebaker's expressive writing paradigm** is the *science*: writing about
  your deepest feelings for 15–20 minutes across 3–4 days has documented
  psychological and physiological effects. PoesIA's outlet movement stands on
  this soil — honestly, without claiming to be therapy.

Also worth knowing: **"Poem Portraits"** (Spafford & Coombes, 2014) is the name
of a *human* practice — a poet interviews a person for ~30 minutes and writes
*them* a poem to keep, so they feel "interpreted." It is the pure human north
star of what PoesIA automates the scaffolding for.

---

## 6. Why the position is empty

Five requirements define the position:

1. **The human is the author, always.**
2. **Raw feeling becomes a made thing** (poetry), not journal prose.
3. **It teaches craft as it goes** — explains *why* and *how to fix*, in human language.
4. **It is private, personal and accumulative** — your voice over time.
5. **It speaks the technical person's language** — offline, deterministic, reproducible.

| Family | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Journaling (750 Words, Penzu, …) | ✅ | ❌ prose | ❌ | ✅ | ✅ |
| Self-authoring (Peterson) | ✅ | ❌ prose | ❌ | ✅ | ❌ |
| Companions (Replika, Pi) | ❌ machine talks | ❌ talk | ❌ | ❌ | ✅ |
| Writer tools (Sudowrite, NovelAI) | ~ | ❌ prose | ❌ | ✅ | ❌ |
| Verse by Verse | ✅ | ✅ | ❌ no why/no aftercare | ❌ | ❌ |
| PoemPortraits | ~ one word | ✅ | ❌ | ❌ | ❌ |

**No existing tool satisfies all five.** The space is open — not because nobody
thought of it, but because the combination is unusual: an instrument that turns
raw feeling into a *made thing*, teaches the making, and is private — instead of
either *generating* (machine as author) or *pouring* (nothing made).

---

## 7. Design consequences — what "embodying" means

1. **Language discipline.** CLI, docs and output never call machine output "a
   poem" alone — it is a *draft*, *proposal*, *scaffold*. The poem is what the
   human keeps.
2. **Human-writes-first flows are the flagship.** `poesia scan` (you write, it
   teaches) and `--interactive` (you choose/type each line; your own lines are
   scanned and scored) lead the Quick Start. Generation is one mode among
   several, framed as scaffolding.
3. **The teaching voice.** When validation fails, say *why* and *how to fix* in
   human language — not just "invalid". `ScanResult.violations` already carry
   the material; surface it everywhere, prettily.
4. **Reflection is a first-class step.** Before/after, ask what the person
   meant and felt; store it beside the poem (memoria provenance). The outlet is
   not a transaction; the poem's story is part of the poem.
5. **Privacy is sacred.** The outlet is private by default; the existing
   guardrails for hosted providers are load-bearing, not optional.
6. **Honesty.** No invented claims. The numbers stay real, the author's own
   creative content stays his (`NOTICE`), and the tool never implies the machine
   authored anything.

---

## 8. Guardrail / definition of done

For every feature, PR, doc change or CLI string: ask

> **"Who is the author?"** — if the answer is ever *the machine*, the work is
> mis-framed and must be reframed, not shipped.

and

> **"Which movement does this serve?"** — outlet, shaping, teaching, or linking.
> If the answer is *none*, the work is off-purpose.

---

## 9. Sources & verification status (2026-08-05)

Fetched and read directly during research:

- `selfauthoring.com` — Self-Authoring Suite positioning and modules
- Wikipedia: *Writing therapy* (Pennebaker's expressive-writing paradigm),
  *Replika*, *The Artist's Way*
- `mindsera.com`, `reflectly.app`, `penzu.com`, `getfreewrite.com`,
  `sudowrite.com`, `esoteric.codes`
- `poemportraits.co.uk` via Wayback snapshot (Spafford & Coombes — the human
  "Poem Portraits" practice)

Widely documented but **not re-verified verbatim** in this session (primary
pages no longer live or JS-rendered):

- **Verse by Verse** mechanics (Google Arts & Culture + Google Research, 2020;
  line-by-line suggestions in classic-poet styles; positioned the human as the
  poet; experiment since sunset)
- **PoemPortraits** (Es Devlin + Ross Goodwin) mechanics (Barbican *AI: More
  than Human*, 2019; word → machine poem; collective poem). `esdevlin.com`
  work page exists but renders via JS; the exact tagline was not re-confirmed.

Rule: if a future claim needs a verbatim quote from either, verify it before
printing it.



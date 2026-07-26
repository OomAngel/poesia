# Naming rationale

## The umbrella: PoesIA

*Poesía* is simply the Spanish word for "poetry." Read the last three
letters as **IA** (*Inteligencia Artificial* — Spanish/Romance abbreviation
for "AI") and the pun is already there, unforced. Nothing invented.

This landed after a long naming search (documented for posterity — see the
"how we got here" section below) that tried and rejected several other
directions:
- **poiesis** (Greek "making") — fine but not bilingual EN/ES-flavored enough
- root+suffix mashups (`coplai`, `rimagraph`, `silvagraph`, ...) — felt
  mechanical, not genuinely fused
- "hidden pun in a real word" tricks in English (`SoNNet`) — rejected because
  "Sonnet" collides with Anthropic's actual Claude Sonnet model line
- movie-pastiche jokes (`Rhymenator`, `Trovatron`) — fun but not durable branding

**PoesIA** won because it is the *exact* real word, works identically in
speech and text, and the family pattern (see below) reproduces cleanly
across every other real Spanish "-ía" word relevant to the project.

## The -IA family

Every sub-brand is a genuine Spanish noun ending in "-ía," chosen because its
literal meaning matches the module's actual responsibility:

| Sub-brand | Spanish word | Literal meaning | Module responsibility |
|---|---|---|---|
| **PoesIA** | poesía | poetry | core generation + phonology validation |
| **EufonIA** | eufonía | euphony | sound analysis: rhyme, assonance, consonance |
| **GalerIA** | galería | gallery | illustration: auca-style image + verse sheets |
| **MemorIA** | memoria | memory | collections now; Graph RAG retrieval later |
| **ArmonIA** | armonía | harmony | music: prosody → rhythm, score, recitation |

### EufonIA vs. ArmonIA — why both, why not redundant

- **Eufonía (euphony)**: pleasantness of *sound itself* — the acoustic/
  phonetic layer. Concerned with whether words, side by side, sound good:
  avoiding harsh consonant clusters, controlling assonance/consonance
  density, judging rhyme quality. This is a property of the *text*.
- **Armonía (harmony)**: concordance/balance *among parts* — and in music
  specifically, the vertical stacking of notes into chords, or more broadly
  the整体 fit of simultaneous musical elements. This is a property of *music
  derived from* the text.

EufonIA judges how the poem sounds when read; ArmonIA is what happens when
you decide to set that poem to music. One is analysis, the other is
generation into a new medium.

## How we got here (naming search log)

For continuity across sessions, the naming conversation went through several
rounds before converging:

1. Started with **poiesis** (Greek root of "poetry") — good concept, wrong
   linguistic register for a bilingual EN/ES project.
2. Explored Spanish/Latin poetic-form words as roots (`copla`, `vate`,
   `trova`, `verso`, `rima`, `glosa`, `silva`, `canto`...) crossed
   mechanically with tech suffixes (`-forge`, `-graph`, `-ai`) — correctly
   rejected as "too flat, obvious, dull."
3. Tried genuine portmanteaus and words with pre-existing double meanings
   (`contrapunto`, `sinéresis`, `urdimbre`) — too serious/academic, not fun.
4. Tried funny/memorable ML in-jokes (`Rhymenator`, `VicuñaVerso`, `SoNNet`)
   — fun, but `SoNNet` collides with an actual Claude model name, and the
   register overall skewed too jokey for a project meant to last.
5. User introduced the **illustration** idea (poem + image, auca/aleluya
   tradition) mid-conversation — this changed project scope in a healthy,
   permanent way (see GalerIA).
6. User independently arrived at **"poesía"** containing **"ía"** — the
   winning insight. Extended immediately to the -IA family above.
7. Music (**ArmonIA**) was added as a fifth pillar once illustration made
   clear the project's ambition extended beyond text.

## PyPI availability (checked at repo creation)

`poesia` was unregistered on PyPI as of this check (HTTP 404 on
`https://pypi.org/pypi/poesia/json`). Irrelevant until/unless this repo is
ever published — it remains a local, personal repository for now.

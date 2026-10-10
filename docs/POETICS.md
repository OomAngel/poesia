# Poetics: what PoesIA's author asks of a poem

Every quality decision in PoesIA is checked against this file: what the engine flags, what a
proposal must be, what goes into training data and how a model is judged. The criteria are
Angel's, stated while he worked on his own poems line by line (sessions of June 2024,
September 2024 and August 2025; the sessions themselves are private and are not quoted here
beyond the criteria). His poets are in `data/influences.yaml`; the movements in
`LITERARY_TAXONOMY.md`; the author's place in `POSITIONING.md` (the person is the author).

This is a first record, not the whole of it (Angel, 2026-10-10: "there must be more"). Add to it
when more is found; keep each criterion tied to how it is checked.

## The criteria

| # | Criterion | In his words | How PoesIA checks it |
|---|---|---|---|
| 1 | Rhyme and metre are kept, in every line of a rhymed stanza | "el poema debe respetar la rima y la métrica"; "solo un par de versos riman" (a fault) | engine: syllable count, stress, rhyme key per line |
| 2 | Rhymes fall on clearly different words, not near-copies | "no me gusta que rimen en palabras tan similares" | same word refused today; a shared-stem check is still missing |
| 3 | No repeated words in a poem | "inmenso 3 veces… lo mismo golpes, noble, invierno"; "repite alma" | missing: content-word repetition count |
| 4 | Every line makes sense, and says what is meant | "¿cómo es que la luz persiste? no me hace sentido"; lines that "no encajan" | grammar score (70B correct-and-compare), fluency check `_line_is_stiff`; finally his reading |
| 5 | Lyric words, not prosaic or technical ones | "mencionar *derecho* lo hace menos lírico" | missing; his rating |
| 6 | The register of Mexican poetry, not Spain's | "evitar españolismos… esto es poesía mexicana" | missing; corpus weighting toward his poets |
| 7 | His tradition: Mexican modernismo and romanticism, Miguel Hernández, Darío; "más torrencial" | "al estilo del modernismo romántico, de Luis G. Urbina" | `influences.yaml`; corpus weighting |
| 8 | Image and analogy over statement, but keeping his intention | "más abstracto, menos directo, con más analogías"; "no transmite la misma intención" | quality directive (`brief_builder.py`); his rating |
| 9 | Lines long enough to hold a whole idea | "versos un poquito más largos… hasta 16"; quatrains | form choice (open: alejandrino on the page) |
| 10 | A strong ending | "poderoso pero no es un buen final" | his rating |
| 11 | When a version fails, a new one, not small edits | "algo nuevo, no solo cambios pequeños" | proposal variety: distinct openings, not one recipe |

## Further statements (found 2026-10-10)

- **Who does what.** "LLM for imagination, deterministic algorithms for the craft (syllables,
  rhyme, stress), human for taste" (Angel, August 2026). `ARCHITECTURE.md`: the human brings
  "taste, necessity, surprise, and whether the poem deserved to exist"; the LLM "semantic
  imagination, metaphor, ambiguity, emotional movement".
- **Tone is not a list.** Era or movement, a poet to write like ("Urbina-like") and his own
  free words ("like cold coffee at dawn"); "no controlled vocabulary, that's antithetical to
  poetry" (design decisions of 2026-07-27, `git show e9a4369^:docs/DESIGN_QUESTIONS.md`).
- **His verdicts on generated verse** (calaveritas review, 2026-10-09): "repetitive,
  unoriginal" (criteria 3, 11); "why always the phone? No gist!" (the details given were
  pasted in word for word, with no idea of the whole poem: a poem needs a gist, and details
  become images, not labels); "not correct use of Spanish, *sombrero muy inclina*?" (criterion 4).
- **Judge against real poems first.** "Why human testers? Don't we have tens of thousands of
  examples per language to evaluate?" (2026-10-07). Machine evaluation compares with the
  corpus; his rating is the last check on a small sample, not the main instrument.
- **Not found yet:** a document Angel wrote on "the actual principles of a poem" (2026-10-10).
  Not on the desktop (searched: all poesia history, ~/dev, the Claude transcripts since
  2026-09-24, the full ChatGPT export, Windows documents, OneNote); the laptop's July–August
  sessions are the likely place.

## What follows for the machine

- A proposal is judged first on 4 (sense) and 1 (form), then on 2, 3, 5 and 6. Form without
  sense is a failure (the line adapter of 2026-10-09 rhymed at 93% with forced words).
- Training data comes from poems that already meet these criteria, weighted toward the poets
  of criterion 7, and filtered on 1–3 by machine. 4–10 cannot be filled in by a metric alone:
  the main judge is comparison with real poems on the same request (tens of thousands per
  language), and a model that might replace the current one gets Angel's blind rating on a
  small sample last.
- Scores that cannot separate good from bad lines are not criteria. The 28 July validator's
  quality score was 1.0 for every sonnet it kept, and its embedding scores varied by ±0.02, so
  they selected nothing (checked 2026-10-10).

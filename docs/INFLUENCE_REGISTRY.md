# Influence Registry

The registry lives in **`data/influences.yaml`**, loaded by `src/poesia/memoria/influence_loader.py`:
24 poets (Spanish / Latin American, English / American, Dutch) with era, movement, tone,
forms and exemplars.

- List them: `poesia memoria list-influences`
- Add one: `poesia memoria add-influence "<name>" --tone "a, b" --language es|en|nl`
  (writes into the YAML, in the language's section, leaving existing entries untouched)
- Richer profiles: `InfluenceRecord` has `resonance_notes` and `anti_patterns` fields, but no
  profile fills them yet.

Until 2026-10-05 this file held a readable copy of the same 24 profiles. Every value in it
was checked against the YAML before it was replaced by this pointer; the copy is in git
history.

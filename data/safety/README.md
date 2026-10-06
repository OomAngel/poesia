---
language: [es, en, de, fr, it]
license: cc-by-4.0
pretty_name: PoesIA safety reflections
size_categories: [n<1K]
task_categories: [text-classification]
---

# PoesIA safety reflections

60 short reflections, the kind a person might write before shaping a poem, used to test
PoesIA's safety screen (`src/poesia/safety/`). 12 per language (Spanish, English, German,
French, Italian): 4 ordinary, 4 sad but safe, 4 with a risk signal.

| Field | Meaning |
|---|---|
| `id` | `<language>-<category>-<n>` |
| `language` | `es`, `en`, `de`, `fr`, `it` |
| `category` | `ordinary`, `sad_safe`, `risk` |
| `risk` | `true` for the risk category |
| `text` | the reflection |

**Provenance.** Synthetic: written for this test set (drafted with an AI assistant, to be
reviewed by the author before publication). No real person's text. The same parallel content
appears in each language, translated by meaning, not word for word.

**Design.** The sad-but-safe items carry the words a naive filter trips on (died, death,
funeral, *murió*, *Tod*, *mort*, *morto*) and must not be flagged: the page is for people who
write about grief. The risk items are non-graphic and name no method: four kinds per
language (wish not to wake / burden, thinking of ending one's life, self-harm tonight, wish
to hurt another person).

**Limits.** 20 risk items is small; one person wrote both the screen's phrase list and this
set, so phrase-list scores on it are optimistic (`reports/eval_2026-10/safety-screen.json`
records the untuned and tuned numbers). It says nothing about real distress language, slang,
irony, or Swiss German dialect. It is a regression test, not a validation.

**Use.** `python scripts/evaluate_safety_screen.py [--ollama-model NAME]`.

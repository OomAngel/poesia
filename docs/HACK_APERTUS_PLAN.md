# Hack Apertus — PoesIA on Apertus v1.5 (working plan)

_Written 2026-10-06. Branch: `hack-apertus`. Submit target: Tue 13 Oct 2026; the hackathon
closes Fri 16 Oct 2026 12:00 CEST._

This is the **working runbook**: what to build, in what order, with the commands and a
"done when" check for each step. The author's planning notes (jury, pitch reasoning,
schedule constraints, research sources) live outside this public repo, in the private career-assets repo (Hack Apertus plan). Read that once; work from this file.

---

## 1. What we are entering

Hack Apertus (online stage, 1–16 Oct 2026), **Track 2B "Own Project"**, built on Apertus,
Switzerland's open LLM. Track 2B is judged on: purposeful use of AI, technical rigour,
value/cost/scalability, sovereign deployability, implementation feasibility.

Deliverables (from the organiser's Getting Started guide, read 2026-10-05):
- [ ] Built with Apertus (v1.5 8B).
- [ ] Public repo following the organiser's **template repo** (URL in the guide).
- [ ] Runs in Docker with **`make run`**, end to end.
- [ ] Deployable **on-premise or air-gapped** (ours: local Ollama, network off).
- [ ] **PDF report, at most 6 pages.**
- [ ] **Demo video, at most 2 minutes.**
- [ ] A public Hugging Face dataset with a card **if** a dataset is part of the entry (the
      safety test set, section 6).
- [ ] Submitted on hackapertus.ch/online-hack/submissions (the guide, read 2026-10-05) **and**
      the Devpost portal (devpost.com/submit-to/30350-hack-apertus, linked on Devpost 2026-10-06)
      until the organisers confirm which counts (hello@hackapertus.ch / Discord).

## 2. The product (POSITIONING.md, applied)

PoesIA stays what POSITIONING.md says: **an instrument for letting things out**; the person
is the author; four movements (outlet, shaping, teaching, linking). For the hack it gains
what Apertus v1.5 adds: Swiss languages, image and audio input, and on-prem deployment.

One flow, end to end, in a **local web page** (PoesIA has no web UI today, only the CLI and
`poesia.api`):

1. **Anchor (optional):** a photo the person brings (an autumn tree). Stored beside the poem
   as *their* reference. If the multimodal model fits (section 4), Apertus may offer a few
   concrete image-words; it never describes the picture as the poem.
2. **Reflection:** what they felt and thought, typed (spoken is stretch). Saved beside the
   poem (memoria), as today.
3. **Safety screen** (section 6) before any shaping.
4. **Shaping:** the existing constrained loop on Apertus: line by line, the person writes or
   picks; every line is scanned.
5. **Teaching:** syllables, stress, rhyme, explained in the person's language.
6. **Read-back:** an offline synthetic voice (Piper) reads the poem.
7. **Linking:** two or three public-domain poems from the person's tradition on the same
   feeling, retrieved locally.

**Cut line for 13 Oct (must-have):** web page; steps 2–7 for es/en; safety screen; all on
Apertus in Docker. **Stretch, in order:** Italian teaching, photo image-words, spoken
reflection, the fine-tuned adapter, German/French teaching beyond syllable counts.

Guardrail (POSITIONING §8) applies to every screen and string: *who is the author?*

## 2a. Writing UX: the person's own line comes first

From the co-writing research of 2026-10-06 (ownership drops with AI help unless suggestions
are small, requested and editable; readers penalise AI-worded personal writing; AI text
homogenises voice). Design for the web page:

- **Typing your own line is the default action.** Every line slot is a free-text field;
  proposals come only on request, appear greyed until edited or accepted, and default to
  several short options (words, phrases) rather than one finished line. Whole AI-written
  lines are off by default for personal poems.
- **Per-line origin in the data model:** `human` / `proposal-accepted` / `proposal-edited`
  (+ edit distance, history). Shown quietly, never as permanent colouring. Export can then
  state a true sentence ("all 14 lines worded by the author; metre checked by PoesIA"), and
  the report gets a privacy-safe metric: the human-worded share of each poem.
- **The engine lints, it doesn't rewrite:** per-syllable/stress diagnostics with an
  explanation in the poem's language; repairs as one-word changes, ranked by fit and
  variety (not model likelihood), preferring words already in the poem; each candidate
  shows why it fits. A per-line "allow this irregularity" switch; engine off for free verse.
- **Lock, reorder, recheck:** lock finished lines; drag to reorder with metre and rhyme
  letters recomputed live; per-line and per-poem undo and version history.
- **Gentle defaults:** short sessions, a visible stop, no pressure to write about trauma,
  linked poems offered as a choice (never pushed), the photo prompt asks "what did you feel?".

Must-have for 13 Oct: own-line-first input, greyed proposals, per-line origin, lint
explanations. Stretch: locks, drag-to-reorder, version history.

## 3. Languages and craft teaching

| Language | Engine | This week |
|---|---|---|
| es, en, nl | `src/poesia/phonology/` (existing; es checked against ADSO) | as is |
| it | new `italian.py` from `spanish.py`: sinalefe, dieresi/sineresi, verso piano/tronco/sdrucciolo (count to last stress + 1), endecasillabo stress on 10 | stretch #1; check by hand on 30 lines (Petrarch, Leopardi); Sylli (PyPI) as a syllabification cross-check |
| de | eSpeak NG phonemes with stress → syllable count, stress pattern, rhyme from the stressed vowel; name the metre when regular | syllables + rhyme; test on Haider's gold lines (`tnhaider/metrical-tagging-in-the-wild`) |
| fr | e muet counted only before a consonant and never at line end; diérèse/synérèse; alexandrin 6+6; rime masculine/féminine and quality | `french.py` counter; rules referenced from Carnet du Poète (`sbridel/carnet-du-poete`, GPL-3.0: reimplement the rules, don't copy its code) |
| rm | TeX `hyph-rm` hyphenation patterns → syllable counts | free verse only |

`multilingual.py` is the existing phonemizer/eSpeak NG stub to build on.

## 4. Models

- **Text runtime:** `andreasmartin/apertus-v1.5-8b-text` (the official v1.5 8B with image/audio
  towers removed) → GGUF Q4_K_M (~5 GB) → Ollama as `apertus-v1.5-8b-text:q4km`. Script:
  `scripts/setup_apertus.sh`. The pinned llama.cpp (`4df29be`) registers `ApertusForCausalLM`
  and has Apertus's chat template; the script's Ollama steps were tested against a mock server
  only. Fallback: his `apertus-v1.5-8b-text-Q8_0-GGUF` requantized with
  `llama-quantize --allow-requantize ... Q4_K_M`.
- **Images/audio:** Apertus v1.5 takes image, audio and text **input** and generates **text
  only**. Needs the official gated weights (`swiss-ai/Apertus-v1.5-8B`) and Swiss AI's
  transformers fork; no llama.cpp path. 4-bit on the 3070 is **untested and tight**.
  Fallback: photo is the person's private anchor only; speech via `faster-whisper`.
- **Read-back:** Piper (offline TTS; de/fr/it/es/en voices; no Romansh). Labelled synthetic
  voice, no cloning, can be turned off. Cloud TTS only as explicit opt-in.
- **Retrieval for linking:** `andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir` (check licence
  and quality on 20 reflections); fallback: the existing embedding profile
  (`docs/EMBEDDING_PROFILE.md`).

## 4a. Participant resources (from the organiser's resources page, read 2026-10-06)

Registering on Devpost gives: **CSCS inference for all teams** (Apertus served by the Swiss
National Supercomputing Centre); **Phoeniqs compute support for non-academic teams, on
application** (Phoeniqs runs 192 NVIDIA H100s in Basel); **$10 Hugging Face credits** per
hacker; **Edit with Ava** for demo videos; bookable **mentors** 1–16 Oct. (CSCS compute is
for Swiss academic teams only.) Redemption steps are in the Getting Started guide.

**Closed before we registered (Resources & Tools page, read 2026-10-06 evening):** CSCS keys
"have been distributed. We are no longer accepting new requests" (6 Oct, 18:40 CEST);
Phoeniqs applications closed 4 Oct, 20:30 CEST. So no CSCS 70B and no H100 time: the bullets
below and the Phoeniqs branch of §5 do not apply. Still open: HF credits
(hackapertus.ch/online-hack/hugging-face, same email as the Devpost account), Edit with Ava
(editwithava.com/promo, code AVA5), mentors. Remote GPU instead: Kaggle (free weekly GPU
quota) with Andreas Martin's Apertus v1.5 8B SFT notebook
(kaggle.com/code/andreasmartinch/sft-apertus-v1-5-8b-hack-apertus-template); 70B only through
the $10 HF credits, if at all. Multimodal tests run locally (4-bit) or are dropped.

What was planned (superseded by the closure above):
- **Bigger models for development, not for the deliverable.** The entry must run
  on-prem/offline with `make run`, so the demo stays on Apertus 8B locally. Use CSCS for what
  the 3070 can't do: Apertus **70B** and the full **multimodal v1.5** (image/audio tests,
  image-words, spoken reflection), and fast evaluation runs.
- **70B as teacher (no approval needed):** use CSCS 70B to (a) label the 60-line safety set
  and many more synthetic reflections for the screen, (b) produce candidate lines in it/de/fr
  that pass PoesIA's own metre check, as extra training data for the 8B adapter. Never put
  real people's text through it. Record the model and date for every generated item.
- **Two deployment tiers for the report:** 8B on a single consumer GPU (school, library,
  home); 70B on a canton or hospital server, on-prem. Measure both if CSCS allows timing.

## 5. Training (stretch, unattended)

**If Phoeniqs approves H100 time:** run the QLoRA on Apertus 8B there in minutes to hours
instead of overnight, and use the speed for what matters: 2–3 runs comparing data mixes
(with and without the 70B-generated lines), larger `max_length` (keep long poems), and more
poems per language. A 70B QLoRA fits one 80 GB H100, but only as the server tier above;
it cannot be the `make run` demo. Apply on registration day: approval time is unknown.

**If not (default):**

From `RETRAINING_PLAN_2026-10.md` §3/§5: Qwen3-8B trained on the 3070 at 7.32 GB peak with
`memory_layout: low_vram`, batch 1×8, `max_length` 300, ~140 tokens/s → ~2,600 tokens/poem →
**~1,500 poems in one overnight run**.

- Base: the text model (`hf-text`), same layout; **40-step smoke run first** (peak memory).
- Data: the loop's line format via `build_fixed_dataset.py`, mixed ~30% es, 25% en, 15% each
  it/de/fr (new corpora, section 7).
- End-of-text fix `52fea7a` must be in the trainer (it is on `main`).
- Use the adapter **only if** it beats plain Apertus on the seeded evaluation.
- Convert with `scripts/convert_adapters_to_gguf.py`; log the run in MLflow.

## 6. Safety layer (must-have) and the verifier argument

**Verifier argument for the report:** the model proposes, the deterministic engine checks,
the person decides. Measure metre pass rate of Apertus lines unaided vs after the
check-and-repair loop (the seeded evaluation already reports metre per model).

**Safety screen** before shaping:
- keyword list per language + one Apertus classification call ("does this text express
  intent or risk of self-harm or harm to others?");
- on a positive: pause the poem, say plainly that what they wrote matters, show Swiss support
  numbers **143** (Die Dargebotene Hand / La Main Tendue / Telefono Amico) and **147** (Pro
  Juventute). **Verify both on the services' own sites before shipping.** The person may
  continue afterwards; nothing is stored unless they keep the poem;
- no therapy claims anywhere (POSITIONING §2).

**Test set (`data/safety/safety_reflections.jsonl`; synthetic, kept in git: no real
person's text):** 60 reflections across es/en/de/fr/it: 20 ordinary, 20 sad-but-safe (grief,
loneliness, autumn), 20 with risk signals. No real people's text. Report recall on the risk set and false alarms on the
sad-but-safe set. Publish as a small HF dataset with a card.

Privacy: reflections can be health data under the Swiss revised FADP; on-prem by default,
nothing logged, local storage only on "keep".

## 7. Corpora (into `data/external/`, DVC-tracked, never git or Docker)

| Source | Language | Command | Licence | Use |
|---|---|---|---|---|
| PULPO (`linhd-postdata/pulpo`) | de 1.58M, it 662k, fr 224k verses (+ es, en) | `hf download linhd-postdata/pulpo --repo-type dataset --local-dir data/external/pulpo` | not stated | training lines only |
| DLK (`tnhaider/DLK`) | de, 65,755 poems, metre-annotated JSON | `git clone --depth 1 https://github.com/tnhaider/DLK data/external/DLK` | CC BY 4.0 (paper) | linking, training, metre test |
| PO-EMO (`tnhaider/poetry-emotion`) | de 158 + en 64 poems, emotions per line | `git clone --depth 1 https://github.com/tnhaider/poetry-emotion data/external/poetry-emotion` | check | does linking match a feeling? |
| Metrical gold (`tnhaider/metrical-tagging-in-the-wild`) | de/en annotated lines | `git clone --depth 1 https://github.com/tnhaider/metrical-tagging-in-the-wild data/external/metrical-tagging` | check | German metre test |
| Métrique en Ligne (Averell 9) | fr, 5,081 poems | `pip install averell && averell download 9 10 --corpora-folder data/external/averell` | unknown | training, evaluation |
| Biblioteca Italiana (Averell 10) | it, 25,341 poems | (same command) | unknown | training, evaluation |
| Wikisource de/fr/it | public domain | fetch pattern of `scripts/fetch_gutenberg_poems.py` / Wikisource API | PD | **the only texts shown to users** in linking |

Record each source, licence and date in `docs/CORPUS_SOURCES.md`. Anything with an unknown
licence is training/evaluation only, never shown to users or published.

## 8. Day-by-day runbook

Each day: tick the boxes, then update `memory-bank/activeContext.md`.

### Tue 6 Oct (evening) — downloads

- [ ] Accept the terms on https://huggingface.co/swiss-ai/Apertus-v1.5-8B (signed in).
- [ ] `hf auth login` (WSL, poesia env).
- [ ] `git fetch && git checkout hack-apertus`
- [ ] `bash scripts/setup_apertus.sh --official` (overnight; ~45 GB free needed).
- [ ] Corpora: every command in section 7.
- [ ] Tools: `sudo apt install espeak-ng texlive-lang-other`; `pip install piper-tts sylli
      faster-whisper averell`; Piper voices de/fr/it/es/en; `hf download
      andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir --local-dir models/swiss-embed`;
      `git clone --depth 1 https://github.com/sbridel/carnet-du-poete external/carnet-du-poete`.
- [x] Template repo: https://github.com/HackApertus/project-template (named on the Track 1A/1B/2B
      pages, read 2026-10-06; has `track_2b/`). FHGR 2A starter: `fhgr/HackApertusTemplate26`.

**Done when:** `bash scripts/setup_apertus.sh --check` shows the GGUF and the Ollama model.

### Wed 7 Oct — runtime, baseline, page skeleton

- [ ] `OLLAMA_MODEL=apertus-v1.5-8b-text:q4km poesia write --llm ollama --theme luna`
- [x] Seeded baseline, es + en, 36 poems (same harness and seeds as the Qwen3-4B reference
      in RETRAINING_PLAN §6a; `reports/eval_2026-10/apertus-v1.5-8b-text.json`, run
      2026-10-07 through transformers, `low_vram`, 40–127 s per poem):

      All rows re-scored 2026-10-07 with the current scorer (English rhyme keys no longer
      separate secondary from primary stress: "evermore" rhymes with "shore").

      | 18 poems per language | es off/line | es metre | es rhyme | en off/line | en metre | en rhyme |
      |---|---|---|---|---|---|---|
      | July recipe (Qwen2.5-1.5B) | 0.63 | 57% | 3% | 0.35 | 73% | 11% |
      | Plain Qwen3-4B | 0.52 | 62% | 30% | 0.69 | 56% | 72% |
      | Qwen3-4B + corpus adapter (main, 55784bd) | 0.38 | 71% | 24% | 0.46 | 75% | 40% |
      | Apertus 8B text, transformers, raw prompt | 0.83 | 60% | 41% | 0.73 | 77% | 83% |
      | **Apertus 8B text, Ollama Q4_K_M + line system message** | 0.42 | **82%** | **44%** | **0.29** | **89%** | 83% |

      The raw-prompt run had rhyme-word fragments ("bayed blade"): 17 es / 19 en lines under
      four words, which also inflated its rhyme. Cause: with a rhyme word bank in the prompt,
      Apertus answers with the word alone (6/6 seeded tries, chat format); a system message for
      line prompts fixes that (0/6) and is now sent by the Ollama and OpenAI-compatible clients
      (921d6b6). Fragments left with it: 9 es / 5 en, so the loop now also drops candidates
      under three words for lines of 8+ syllables (fail-open, 9be86c3). ~35 s per poem via Ollama.

      Re-run with that filter (`apertus-v1.5-8b-text-ollama-nofrag.json`): es 0.28 / 85% / 33%,
      en 0.37 / 87% / 86%. Fragments barely moved (es 9 → 5, en 5 → 7): they come from batches
      where every candidate is a bare word, which the fail-open keeps. The metre and rhyme shifts
      between the two runs are within seed noise (per-poem rhyme ranges 0–100%; 18 poems), so
      neither run is "the" number; report both. Note: this loop's Spanish rhyme word bank comes
      from Datamuse (online); English from CMUdict (offline). The page sends no word bank, so
      the benchmark is not the page's exact condition.
- [ ] Web page skeleton: FastAPI (or similar) + one HTML page over `poesia.api` — photo
      upload, reflection box, line-by-line shaping with the existing scan feedback.
- [x] 4-bit multimodal load test with the official weights (2026-10-07, RTX 3070 8 GB, separate
      venv with Swiss AI's transformers fork `3797303`; script `~/data/hack-apertus/mm_load_test.py`).
      NF4 language model and lm_head on GPU, vision and audio tokenizers fp32 on GPU, the 2.2 GB
      input embedding (vocab 266,752) moved to RAM by hand (accelerate's CPU offload leaves a meta
      tensor that `generate()` reads; `PreTrainedModel.device` also has to report the GPU).
      Loads in 15 s at 5.29 GB. Text 3.6 s; image (COCO sample) 2.2 s, "cats, remote controls,
      pink couch" (right); audio (Piper clip, Spanish) 1.5 s, "Vi un árbol perdiendo sus hojas y
      pensé en mi parte" (said: *padre*). Peak 6.57 GB allocated, **7.5 GB reserved**: fits only
      with the card otherwise empty (Ollama unloaded, ~0.3 GB desktop). Photo image-words and
      spoken reflection on Apertus itself are possible; shipping them needs a second image with
      torch + the fork (several GB) and an 8 GB card to itself.
- [ ] Stretch: mixed dataset → 40-step smoke run → QLoRA overnight.

**Done when:** a poem is shaped in the browser on Apertus; baseline numbers recorded.

### Thu 8 Oct — safety and Docker

- [x] Safety screen (`src/poesia/safety/`, page endpoint `/api/safety`, pause panel with
      143 / 147 / 144-112, checked on 143.ch and 147.ch 2026-10-07) + test set
      `data/safety/safety_reflections.jsonl` (60, card in `data/safety/README.md`) + numbers
      (`reports/eval_2026-10/safety-screen.json`), risk recall / false alarms on 40 safe:

      | | untuned | after adding conjugated forms (tuned on this set: optimistic) |
      |---|---|---|
      | phrases | 11/20, 0/40 | 19/20, 0/40 |
      | Apertus 8B yes/no | 13/20, 0/40 | (not tuned) |
      | either (the policy) | 18/20, 0/40 | 20/20, 0/40 |

      Needs a held-out set written by someone else before any claim beyond "regression test".
- [ ] Docker in the template layout: an Ollama service + the PoesIA web service; model from a
      volume; `make run` serves the page; works with the network off. No corpus or poems in
      the image.
- [x] Stretch: `italian.py` (2026-10-07). Pure Python: nuclei with Italian diphthong rules,
      sinalefe, piano/tronco/sdrucciolo endings, sineresi, a short list of words whose stressed
      i/u stays apart at line end (*mìo*, *vìa*). Against the 10,001 expert-annotated
      endecasillabi in Biblioteca Italiana (Averell 10): **79.5% exact** (Dante 79.2%, Petrarca
      85.4%), mean |error| 0.23, stress on the 10th position 79.6%
      (`scripts/check_italian_scansion.py`). Rules were kept only when they helped both poets;
      dialefe helped Dante and hurt Petrarca, so it is out. The page offers the Italian sonetto.

**Done when:** `make run` on a clean checkout shows the page and writes a poem offline.

### Fri 9 Oct — linking, voice, audit, users

- [x] Linking (2026-10-07): `src/poesia/linking/`, `/api/link`, panel "Poems that feel like
      this"; index of 3,000 es + 3,000 en showable poems (Gutenberg, CC0 pd_poetry, DISCO CC BY;
      authors dead after 1955 excluded) embedded with bge-m3 on CPU
      (`scripts/build_linking_index.py`), shipped in the entry's `track_2b/data/linking`.
- [x] Piper read-back button, labelled as a synthetic voice (2026-10-07).
- [x] ux-audit (2026-10-07, against `poesia-web`): the five URL layers pass (positive control:
      the broken fixture is flagged); persistence: reflection, theme and line 1 survive a reload;
      keyboard: line 14's "Ideas" and the linking button reachable by Tab. Found and fixed:
      changing the form silently cleared the lines (now asks first).
- [ ] Adapter vs plain Apertus (if trained); pick one.
- [ ] 2–3 tester sessions (consent; no reflections kept; three fixed questions: did you
      finish, does it feel like yours, what got in the way).

**Done when:** the full flow works for es/en (+ it).

### Sat 10 Oct — evidence, on-prem proof, video

- [ ] Validate `docs/hack_apertus/refs.bib` (14 entries, drafted 2026-10-06) with
      research-tools; fetch the open-access papers; check each cited sentence against them.
- [ ] Health statistics: venture-lab `research/statistics/poesia-health-statistics.md`
      (drafted 2026-10-06). Replace the rows tagged [S] with Obsan's own tables; promote the
      figures the report uses into venture-lab's claims registry.
- [ ] Cost per poem: seconds and watts on the 3070 and on a CPU-only server.
- [ ] `make run` on the CPU-only server (on-prem proof).
- [ ] Record the 2-minute video: a real photo and a real reflection (the author's own).

### Sun 11 – Mon 12 Oct — report and polish

- [ ] Report, max 6 pages: the person and the flow; architecture; verifier and safety;
      sovereignty and cost; evaluation (metre, safety, users); limits; next stage.
- [ ] README section for the entry; dataset card for the safety set; every box in section 1.

### Tue 13 Oct — submit

- [ ] Submit on hackapertus.ch. Fixes only until Fri 16 Oct 12:00 CEST.

## 9. Open questions (organiser Discord)

1. Track 2B: may the entry extend a project started before 1 Oct, if the Apertus integration,
   Docker entry and evaluation are built during the hack?
2. Does a runtime using Apertus v1.5 8B's text backbone (multimodal towers removed, quantized
   to GGUF) count as "built with Apertus"?
3. (Read the guide first) Track 1B "Swiss Voices": does it fit this entry better than 2B?

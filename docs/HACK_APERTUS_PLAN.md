# Hack Apertus — PoesIA on Apertus v1.5 (working plan)

_Written 2026-10-06. Branch: `hack-apertus`. Submit target: Tue 13 Oct 2026; the hackathon
closes Fri 16 Oct 2026 12:00 CEST._

This is the **working runbook**: what to build, in what order, with the commands and a
"done when" check for each step. The author's planning notes (jury, pitch reasoning,
schedule constraints, research sources) live outside this public repo, in career-assets
`docs/ww-transition/competitions/hack-apertus.md`. Read that once; work from this file.

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
- [ ] Submitted on hackapertus.ch/online-hack/submissions (not Devpost).

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

## 5. Training: one QLoRA run (stretch, unattended)

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

**Test set (`eval_gold/safety_reflections.jsonl`):** 60 hand-written reflections across
es/en/de/fr/it: 20 ordinary, 20 sad-but-safe (grief, loneliness, autumn), 20 with risk
signals. No real people's text. Report recall on the risk set and false alarms on the
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
- [ ] Open the organiser's Getting Started guide; copy the template repo URL here: ______

**Done when:** `bash scripts/setup_apertus.sh --check` shows the GGUF and the Ollama model.

### Wed 7 Oct — runtime, baseline, page skeleton

- [ ] `OLLAMA_MODEL=apertus-v1.5-8b-text:q4km poesia write --llm ollama --theme luna`
- [ ] Seeded baseline, es + en, 36 poems (same harness and seeds as the Qwen3-4B reference
      in RETRAINING_PLAN §6a); add Apertus as a third row in that table.
- [ ] Web page skeleton: FastAPI (or similar) + one HTML page over `poesia.api` — photo
      upload, reflection box, line-by-line shaping with the existing scan feedback.
- [ ] 4-bit multimodal load test with the official weights (record peak VRAM).
- [ ] Stretch: mixed dataset → 40-step smoke run → QLoRA overnight.

**Done when:** a poem is shaped in the browser on Apertus; baseline numbers recorded.

### Thu 8 Oct — safety and Docker

- [ ] Safety screen + `eval_gold/safety_reflections.jsonl` (60 lines) + recall/false-alarm
      numbers.
- [ ] Docker in the template layout: an Ollama service + the PoesIA web service; model from a
      volume; `make run` serves the page; works with the network off. No corpus or poems in
      the image.
- [ ] Stretch: `italian.py`.

**Done when:** `make run` on a clean checkout shows the page and writes a poem offline.

### Fri 9 Oct — linking, voice, audit, users

- [ ] Linking: embed public-domain poems (Wikisource + DLK) and the reflection; return 2–3
      nearest in the person's language.
- [ ] Piper read-back button, labelled as a synthetic voice.
- [ ] ux-audit (separate repo) against the local page: accessibility, persistence (a typed
      reflection must survive a reload), input robustness, keyboard, findability.
- [ ] Adapter vs plain Apertus (if trained); pick one.
- [ ] 2–3 tester sessions (consent; no reflections kept; three fixed questions: did you
      finish, does it feel like yours, what got in the way).

**Done when:** the full flow works for es/en (+ it).

### Sat 10 Oct — evidence, on-prem proof, video

- [ ] `refs.bib` (~15 entries: expressive writing, arts and health, Swiss mental-health
      statistics, LLM and speech-generator harms, automatic scansion, the Apertus report
      arXiv 2509.14233) validated with research-tools.
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

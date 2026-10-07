# Hack Apertus — packaging and UX plan

_Written 2026-10-07, after the first full build (runbook `docs/HACK_APERTUS_PLAN.md` §8).
Replaces the tester/video/report steps as the next block of work; those follow it._

## Where we are (measured 2026-10-07)

- **Install today:** `git clone` + `make run` with Docker and the NVIDIA runtime. A clean
  machine downloads **~17 GB** before the page appears: the Ollama image 9.3 GB (its GPU
  libraries), Apertus GGUF 5 GB, bge-m3 1.2 GB, and a locally built page image 1.9 GB (a
  3-minute build with a C++ compiler). Windows has no `make`; progress shows only as console
  logs; nothing tells the user what is happening during the first ~10 minutes.
- **Page today** (screenshots at 1280 and 390 px): mixed languages (English chrome, Spanish
  labels once a Spanish form is chosen); the form menu shows code names ("soneto (es)");
  14 empty fields at once with no stanza grouping; stress shown as "S u S S"; lessons are
  long and technical ("Sinalefa detected"); an English line in a Spanish form gets a Spanish
  lesson; on a phone the sticky bar covers the lines and a line scrolls sideways; "Keep"
  downloads JSON, not something a person reads.
- What works and stays: own-line-first, suggestions on request, per-line origin, safety
  pause, read-back, linking, nothing stored server-side, `LLM_BASE_URL` for any endpoint.

## Packaging: goal and steps

**Goal:** from nothing to a working page with one command on Windows, macOS or Linux, with
or without an NVIDIA GPU, a visible progress screen, and the smallest download; plus a
carry-on bundle for an air-gapped machine.

| # | Step | Done when | Effort |
|---|---|---|---|
| P1 ✓ (done 2026-10-07) | **Slim the page image.** Check whether `prosodic` (English extra) is used at runtime; if not, drop it (it brings pandas, scipy, pyarrow, statsmodels, matplotlib, ~450 MB). Multi-stage build so the compiler never ships. | image < 0.8 GB; `--network none` scan/safety/read-back/link tests still pass | 1 h |
| P2 ✓ (measured 2026-10-07; decision below) | **Measure a lighter model server.** llama.cpp `llama-server` (OpenAI-compatible chat *and* embeddings, supports Apertus at the pinned commit, can fetch a GGUF from Hugging Face) against the 9.3 GB Ollama image: image size, first-token time, same seeded benchmark. Switch only if it is clearly smaller and scores the same. | a table of both; decision recorded | 3 h |
| P3 ✓ (done 2026-10-07) | **One command without make.** `docker compose up` alone works (CPU), `docker compose --profile gpu up` uses the GPU; `run.sh` / `run.ps1` pick the profile by checking for an NVIDIA runtime. `make run` stays for Linux. | the same three commands work on Windows (PowerShell), WSL and Linux | 1 h |
| P4 ✓ (done 2026-10-07) | **First-run screen in the page.** The page starts at once and shows "Preparing PoesIA: downloading the poetry model (2.1 of 5.0 GB)" from the model server's pull progress; scanning, the safety screen and read-back work immediately; suggestions switch on when the model is ready. | a fresh volume shows progress in the browser, not only in the console | 3 h |
| P5 ✓ (done 2026-10-07: `bundle.sh` 9.6 GB in 9.5 min, `load.sh` 6.5 min; restored with images and models deleted, run on a Docker network with no route out) | **Air-gapped bundle.** `make bundle` writes the images and the model volume to one folder (`docker save` + a volume tar) with a checksum; `make load` restores it on a machine with no network. | `make load && make run` on a machine with the cable out; one paragraph and a photo for the report | 2 h |
| P6 ✓ (done 2026-10-07: reads the GPU share from Ollama once the model is loaded; CPU-only measured 14 s per suggestion, 7.3 GB memory) | **Hardware check at start.** Free GPU memory and RAM read at startup; under ~6 GB free on the GPU the page says it runs on CPU (suggestions ~15 s) instead of silently splitting the model. Minimum requirements in the README. | the 11%/89% CPU/GPU split seen on 2026-10-07 is reported, not hidden | 1 h |
| P7 | **CI smoke test** of the entry: build, start CPU-only with a tiny GGUF, hit `/api/scan`, `/api/safety`, `/api/propose`. | green on every push | 2 h |
| P8 | **Prebuilt images** (GHCR) so judges pull instead of build; local build stays as the fallback. *Decided: at submission.* | `docker compose up` pulls; no compiler, no 3-min build | 1 h |
| P9 ✓ (built 2026-10-07: `poesia-web --with-ollama`, entry `run-native.sh`/`.ps1` via uvx at a pinned commit; no compiler or git needed, uv brings Python 3.13. Tested on Linux with the compiler disabled and on Windows (page, voices, linking, suggestions). **Caveat:** Ollama 0.40.0 on Windows 11 25H2 with Developer Mode cannot read models it pulls (tag symlinks under `manifests-v2`, "untrusted mount point"); the page now shows Ollama's message; Docker is the route there. Not yet reported upstream.) | **Native path, no Docker** (individuals): Ollama desktop app + `pipx install` + `poesia-web --setup` that pulls the models with progress. *Decided: before 13 Oct.* | works on a laptop with only Ollama installed | 4 h |

## UX: goal and steps

**Goal:** a person who has never written a poem finishes one in their own words in about
15 minutes, understands each check without knowing the terms, and the page speaks one
language throughout.

| # | Step | Done when | Effort |
|---|---|---|---|
| U1 ✓ (done 2026-10-07) | **One language per session.** First choice: "I want to write in Español / English / Italiano"; the whole page follows (a string table; de/fr later). | no mixed-language screen at 390/768/1280 px in es, en, it | 3 h |
| U2 ✓ (done 2026-10-07) | **Human form choice.** Cards: "Soneto — 14 versos de 11 sílabas, rima ABBA ABBA CDC DCD", haiku, and **free verse** (no metre checks; reading, safety and linking only), each with a two-line example. | the form names no code ("sonnet_shakespearean") | 1 h |
| U3 ✓ (done 2026-10-07) | **Guided flow:** 1 What moved you → 2 Write → 3 Listen and read → 4 Keep, with a step indicator. Lines appear stanza by stanza (4-4-3-3 with spacing); rhyme partners linked by a coloured mark instead of letters. | testers can say where they are and what comes next | 4 h |
| U4 ✓ (done 2026-10-07) | **Show the scansion, not codes.** The scanned line split into syllables with stressed ones in bold and merges joined ("la‿au·ro·ra"), a one-line status ("11 of 11 ✓", "one syllable too many"), and the explanation behind "Why?". | no "S u S" and no undefined term on screen | 3 h |
| U5 ✓ (done 2026-10-07) | **Language mismatch hint.** A line that looks English in a Spanish form gets "This line looks English; the soneto counts Spanish syllables" instead of a Spanish lesson. | the 2026-10-07 screenshot case shows the hint | 1 h |
| U6 | **Smaller suggestions first** (plan §2a): rhyme words and short phrases from offline dictionaries (CMUdict, Spanish/Italian suffix lists), whole lines only on a second click; each says why it fits. | default "Ideas" offers words, not finished lines | 3 h |
| U7 | **Keep as something to read:** text and print/PDF with title and the authorship line; JSON only as "open later". | a kept poem opens in any editor and prints on one page | 2 h |
| U8 ✓ (done 2026-10-07) | **Phone layout:** compact bottom bar that never covers a line; lines wrap (no sideways scroll). | ux-audit responsive layer + screenshots at 390 px clean | 1 h |
| U9 | **Safety copy per language** checked by a native speaker; focus stays in the pause panel. | three languages reviewed; keyboard test passes | 1 h |
| U10 ✓ (done 2026-10-07: step 4, after Write; Italian added the same day, 609 Gutenberg poems, after the offline test showed it empty) | **Linking as the ending:** after the poem, "Others felt this too", with the credit line. | shown only after Write | 1 h |
| U11 | **Usability check:** 3 people (es, en, it), before and after U1–U4: time to first own line, finished or not, "does it feel like yours", what got in the way. No reflection kept. | numbers for the report | 3 h |

Every UX step is checked with ux-audit (its 12 layers, positive controls first) and
screenshots at 390, 768 and 1280 px in each language.

## Order (to the 13 Oct submit)

1. P1, P3, U1, U2, U8 (small, remove the most visible problems).
2. U3, U4, U5, P4 (the guided page and the first-run screen).
3. P5, P6, U7, U10, P2 measurement, P9 (no-Docker install, decided before 13 Oct).
4. U11 testers, then the video (Edit with Ava) and the report PDF.
5. If time: U6, P7, U9. P8 (publish images) at submission.

About 35 hours of work for steps 1–3. Steps 4–5 need people and your decisions.

## Decisions (Angel, 2026-10-07)

1. **P8, images:** publish the page image on GitHub Container Registry at submission, and
   keep the local build as the fallback when the pull fails.
2. **P2, model server:** measure llama.cpp's server against Ollama (size, first-token time,
   the seeded benchmark) and switch only if it is clearly smaller and scores the same.
3. **P9, no-Docker install:** **before 13 Oct**, so the report can show that a person runs it
   with only the Ollama app installed (it moves into step 3 of the order below).
4. **U1, languages:** Spanish, English and Italian now; German and French after submitting.

## P2 result: llama.cpp server vs Ollama (2026-10-07)

Same Apertus GGUF, same RTX 3070, the page's own OpenAI-compatible client, the seeded
benchmark (18 sonnets per language). Figures and sources: `reports/eval_2026-10/p2-server-comparison.json`.

| | llama.cpp `server-cuda` b11459 | Ollama 0.34.4 |
|---|---|---|
| Download (compressed) | 2.59 GB GPU image, 0.31 GB CPU image | 3.75 GB, one image for both |
| First run, all downloads | ~9.1 GB GPU, ~6.9 GB CPU | ~10.3 GB |
| First token / 3-line suggestion | 0.037 s / 0.63 s | 0.073 s / 1.05 s |
| Seconds per sonnet (es, en) | 24.0, 21.6 | 28.0, 24.0 |
| es: off / metre / rhyme | 0.17 / 84% / 42% | 0.21 / 84% / 37% |
| en | 0.12 / 92% / 90% | 0.14 / 89% / 84% |
| it | 0.16 / 85% / 49% | 0.18 / 83% / 43% |

How to read it: llama.cpp is equal or ahead on every score in all three languages, but the
gaps are within run-to-run noise. The same seeds on Ollama gave different Italian sonnets in
two runs (4 of the first 7 differ), so only a gap that holds across repeated runs would count.

**Decision: keep Ollama for the 13 Oct submission; move the Docker path to llama.cpp after
16 Oct.** The criterion ("clearly smaller and scores the same") holds for CPU-only machines
(−33% first-run download) but not clearly with a GPU (−11%). Switching now costs about three
days: the page would have to download the GGUFs itself to keep the progress screen, run two
servers (chat and embeddings), replace the GPU-share check (`/api/ps`), and redo the bundle,
the native path and their tests, all while U11, the video and the report are still open.

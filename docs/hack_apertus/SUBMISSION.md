# Hack Apertus 2026 — Track 2B Submission Sheet

> **Single reference document for applying to Hack Apertus Track 2B (Own Project).**  
> Use this document to copy-paste directly into the submission forms.
>
> **Hard Deadline**: **Friday 16 October 2026, 12:00 CEST (noon)**.

---

## 1. Submission Portals

**Official Submission Form (the only one)**:  
👉 **https://hackapertus.ch/online-hack/submissions** (select Track 2B to open the form)

*Not Devpost.* The official template says "Submissions are not handled on Devpost but via this URL
only" (`HackApertus/project-template`, `track_2b/README.md`), and the submissions page says "One
submission per project" (both checked 2026-10-13).

---

## 2. Copy-Paste Application Form Fields

### Project Name
```text
PoesIA — Multilingual Poetry Writing Instrument on Apertus
```

### Track
```text
Track 2B: Own Project
```

### Tagline / One-Line Elevator Pitch
```text
A private, on-premise writing instrument where the person stays the author; Apertus v1.5 8B suggests lines on request and a deterministic rule engine explains poetic metre in 5 languages.
```

### Team Members
* **Angel Márquez Aguilar** (Solo)  
  * Email: `angel.marquezaguilar@outlook.com`  
  * GitHub: `@OomAngel` (`https://github.com/OomAngel`)  
  * Hugging Face: `@GrootCappuccino` (`https://huggingface.co/GrootCappuccino`)  
  * Location: Roermond, Netherlands / Switzerland (EU/EEA resident, eligible)

---

### Target Architecture (Mandatory Criterion)
Select/State: **All three supported and verified**:
* **a) On-premise**: Runs locally on a consumer workstation/laptop with 1 consumer GPU (8 GB VRAM) or CPU-only (8 GB RAM) via `make run` or `./run.sh`.
* **b) Air-gapped**: Shipped with self-contained bundle scripts (`./bundle.sh` and `./load.sh`) packing both images and models (9.6 GB); runs on an isolated Docker network with zero route out.
* **c) Sovereign Swiss Cloud**: Tested and verified against the CSCS LLM Inference API (`https://api.inference.cscs.ch/v1`) using `swiss-ai/Apertus-v1.5-8B`.

---

### Public Git Repository URL
```text
https://github.com/OomAngel/poesia-apertus
```
*(Path within repo: `track_2b/`)*

---

### Technical Report (PDF)
* **File**: `track_2b/PoesIA_Report.pdf` (or `track_2b/TeamName_Report.pdf`)
* **Length**: 6 pages plus one page of references (limit: 6 without references). Build: `pandoc technical_report.md -o PoesIA_Report.pdf --pdf-engine=xelatex -V geometry:margin=0.75in -V fontsize=10pt`, then copy to `TeamName_Report.pdf`.
* **Source**: Compiled from `track_2b/technical_report.md`.

---

### Demo Video URL (Max 2 minutes)
```text
[INSERT_YOUTUBE_OR_VIMEO_LINK_HERE]
```
*(See Checklist below for script and recording instructions)*

---

### Dataset URL (Optional)
```text
https://huggingface.co/datasets/GrootCappuccino/poesia-safety-screen
```
*(60 synthetic reflections, 12 per language: es, en, de, fr, it.)* **Private today** (the link
returns 401): judges cannot open it unless Angel makes it public with the template's card; otherwise
leave this field empty.

---

### Project Description / Motivation & Impact (Long Form)

```markdown
### What it does
PoesIA is an expressive writing instrument designed for private, on-premise deployment. Unlike conversational generative AI that replaces human authorship, PoesIA keeps the person as the primary writer across four reflective stages:
1. **Outlet & Reflection**: The writer reflects on an experience or feeling.
2. **Safety Screen**: An offline, rule-and-model safety net checks for distress signals and offers local support hotlines before writing begins, with no text stored or transmitted.
3. **Shaping & Craft Teaching**: The writer chooses a poetic form (Spanish *soneto*, English Shakespearean sonnet, Italian *sonetto*, German *Sonett*, French alexandrine sonnet, haiku, or free verse). Every line is scanned deterministically for syllable counts, synalepha, and rhyme by a pure-rule engine that explains craft rules in the writer's language. Apertus v1.5 8B proposes lines only when asked; a whole draft is offered only as a starting point on request, and its lines stay marked as drafts until the writer edits them.
4. **Recitation & Linking**: An offline synthetic voice (Piper) reads the poem aloud, and semantic retrieval connects the work to curated public-domain poetry (Dante, Dickinson, Rosalía de Castro, Rilke) touching similar emotional themes.

### How it uses Apertus
PoesIA uses `andreasmartin/apertus-v1.5-8b-text` in GGUF Q4_K_M quantisation served locally via Ollama, as well as native integration with the CSCS Swiss Inference Cloud. Apertus performs:
- Single-line proposals ranked deterministically by scansion rather than model probability;
- A whole-poem draft on request, as a starting point (lines marked as drafts until edited);
- Borderline distress evaluation in the safety pause.

On a seeded benchmark of 18 sonnets per language, Apertus guided by PoesIA achieves 83% (Spanish, rerun with the corrected syllable counter), 87–90% (English) and 87% (Italian) exact metrical accuracy, using about 1.7 Wh per automatic sonnet on an 8 GB consumer GPU.

### Sovereign & Private by Design
No data leaves the device. All models, phonology rules, TTS voices, and embedding indexes run 100% offline. Public libraries, schools, hospitals, and cantonal institutions can deploy PoesIA without third-party cloud data exposure.
```

---

### Instructions for Judges to Run the Solution

```bash
# Clone the repository
git clone https://github.com/OomAngel/poesia-apertus.git
cd poesia-apertus/track_2b

# Launch the prototype (starts Ollama and the PoesIA writing webapp)
make run

# Open in browser:
# http://localhost:8000
```
*(Air-gapped verification: `./bundle.sh` creates the offline bundle; `./load.sh poesia-bundle` loads it on a machine with no internet connection.)*

---

## 3. Review of Project Status: Done vs. Pending

### ✅ COMPLETED & VERIFIED (Ready for Submission)

1. **Apertus v1.5 Integration**:
   - Local Ollama runtime with `andreasmartin/apertus-v1.5-8b-text:q4km`.
   - CSCS Inference Cloud integration (`https://api.inference.cscs.ch/v1`).
   - Line and full-draft prompting with structured 14-verse templates and resilient verse fallback.
2. **Deterministic Scansion Engine**:
   - Multilingual syllabification, stress, synalepha, and consonant rhyme across 5 languages (es, en, it, de, fr).
3. **Full Writing Web Interface**:
   - 4-step wizard: Reflection $\rightarrow$ Form selection $\rightarrow$ Writing workspace $\rightarrow$ Listen & Export.
   - Per-line provenance tracking (`human` vs `proposal-accepted`).
   - Optional thoughts per stanza; a whole draft only on request, as a starting point, its lines marked as drafts until edited. "Next" on an empty poem does not write it for the person.
4. **Offline Recitation (Piper TTS)**:
   - 5 stock synthetic voices running in-process; tested and returning audio.
5. **Local Semantic Linking**:
   - BGE-M3 embeddings on CPU matching public domain poetry (in the entry, `make run`). On the Veriton deployment the embeddings come from the desktop GPU, so linking there works only while the desktop serves them.
6. **Safety Pause**:
   - Multilingual phrase screening + Apertus evaluation with local emergency resources.
7. **UX Audit Verification (`ux-audit`)**:
   - Automated end-to-end journey tests in `tests/test_webui_ux_journey.py` (engine repo) against the deployed page: an empty poem is not written for you (4 interactions, 2.9 s); stanza thoughts then a draft as a starting point (9 interactions, 20.9 s); 0 failures (2026-10-13, after the repin).
   - WCAG 2.2 AA mechanical compliance: **PASS** (0 violations).
   - Responsive design (390px, 768px, 1024px+): **PASS** (0 horizontal overflows, no iOS zoom triggers).
   - Keyboard-only navigation: **PASS**.
   - Interruption data persistence: **PASS**.
8. **Deployment & Packaging**:
   - `make run`, `run.sh`, `run.ps1`, `run-native.sh`, `bundle.sh`, and `load.sh`.
   - Hardened Docker container deployed and live on Veriton (`https://veriton.tail6b937e.ts.net:8443`).
9. **Technical Report**:
   - `track_2b/technical_report.md` updated with measured benchmark figures, CSCS usage, and UX audit findings.
   - Compiled to `track_2b/PoesIA_Report.pdf` (exactly 6 pages, meeting the competition rule).

---

### ⏳ PENDING ITEMS (To complete before Friday 16 Oct 12:00 CEST)

1. **Record the 2-Minute Demo Video**:
   * Requirements: Max. 2 minutes, showcase the working prototype.
   * Suggested flow (120 s):
     * *0:00 - 0:20*: Introduce PoesIA (human author, sovereign offline writing, 5 languages).
     * *0:20 - 0:40*: Step 1 (Theme & reflection) + Step 2 (Select Spanish Soneto).
     * *0:40 - 1:15*: Step 3: type your own line and watch it scanned (syllables, stress, rhyme, why it falls short); "Ideas" for rhyme words, then one Apertus line proposal; at most a glance at the whole draft as a starting point, greyed until edited.
     * *1:15 - 1:40*: Step 4 (Piper voice recitation aloud + Dickinson/Rosalía linked poems).
     * *1:40 - 2:00*: Show `make run` in terminal / air-gapped architecture / CSCS sovereign option.
   * Action: Upload to YouTube (Unlisted or Public) or Vimeo, and paste the URL into Section 2 above.
2. **Optional: Hugging Face Dataset Card**:
   * If submitting the safety evaluation dataset, ensure `https://huggingface.co/datasets/GrootCappuccino/poesia-safety-screen` uses the HackApertus template and is set to Public.
3. **Submit on Portals**:
   * Open `http://hackapertus.ch/online-hack/submissions`.
   * Paste the fields from Section 2 of this document.
   * Attach `PoesIA_Report.pdf`.
   * Only this form: not Devpost, and one submission per project.

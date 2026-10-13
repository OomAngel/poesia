# Hack Apertus 2026 — Track 2B Submission Sheet

> **Single reference document for applying to Hack Apertus Track 2B (Own Project).**  
> Use this document to copy-paste directly into the submission forms.
>
> **Hard Deadline**: **Friday 16 October 2026, 12:00 CEST (noon)**.

---

## 1. Submission Portals

1. **Official Submission Form (Primary)**:  
   👉 **http://hackapertus.ch/online-hack/submissions**
2. **Devpost Portal (Mirror / Backup)**:  
   👉 **https://devpost.com/submit-to/30350-hack-apertus** (or https://hackapertus.devpost.com/submit)

*Note: Per Hack Apertus organizers, submissions are officially evaluated via `hackapertus.ch/online-hack/submissions`. Devpost should be filled out as well to ensure visibility on both platforms.*

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
* **Length**: Exactly 6 pages (meets the $\le 6$ page limit).
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
*(60 synthetic reflections + held-out evaluations across es, en, de, fr, it)*

---

### Project Description / Motivation & Impact (For Devpost / Long Form)

```markdown
### What it does
PoesIA is an expressive writing instrument designed for private, on-premise deployment. Unlike conversational generative AI that replaces human authorship, PoesIA keeps the person as the primary writer across four reflective stages:
1. **Outlet & Reflection**: The writer reflects on an experience or feeling (optionally anchored by a personal photo or memory).
2. **Safety Screen**: An offline, rule-and-model safety net checks for distress signals and offers local support hotlines before writing begins, with no text stored or transmitted.
3. **Shaping & Craft Teaching**: The writer chooses a poetic form (Spanish *soneto*, English Shakespearean sonnet, Italian *sonetto*, German *Sonett*, French alexandrine sonnet, haiku, or free verse). Every line is scanned deterministically for syllable counts, synalepha, and rhyme by a pure-rule engine that explains craft rules in the writer's language. Apertus v1.5 8B provides suggestions and full drafts only when requested.
4. **Recitation & Linking**: An offline synthetic voice (Piper) reads the poem aloud, and semantic retrieval connects the work to curated public-domain poetry (Dante, Dickinson, Rosalía de Castro, Rilke) touching similar emotional themes.

### How it uses Apertus
PoesIA uses `andreasmartin/apertus-v1.5-8b-text` in GGUF Q4_K_M quantisation served locally via Ollama, as well as native integration with the CSCS Swiss Inference Cloud. Apertus performs:
- Single-line proposals ranked deterministically by scansion rather than model probability;
- Whole-poem drafting with structured verse numbering;
- Borderline distress evaluation in the safety pause.

On a seeded benchmark of 18 sonnets per language, Apertus guided by PoesIA achieves 83–85% (Spanish), 87–90% (English), and 87% (Italian) exact metrical accuracy, consuming under 1.7 Wh per automatic sonnet on an 8 GB consumer GPU.

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
   - Optional Step 3 workflow: users can skip manual typing or provide optional stanza thoughts.
4. **Offline Recitation (Piper TTS)**:
   - 5 stock synthetic voices running in-process; tested and returning audio.
5. **Local Semantic Linking**:
   - BGE-M3 embeddings on CPU matching public domain poetry.
6. **Safety Pause**:
   - Multilingual phrase screening + Apertus evaluation with local emergency resources.
7. **UX Audit Verification (`ux-audit`)**:
   - Automated end-to-end journey tests in `tests/test_webui_ux_journey.py` passing with **0 failures**.
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
     * *0:40 - 1:15*: Step 3 (Optional stanza thoughts or skip directly, 1-click Apertus draft, deterministic scansion syllables/rhyme feedback).
     * *1:15 - 1:40*: Step 4 (Piper voice recitation aloud + Dickinson/Rosalía linked poems).
     * *1:40 - 2:00*: Show `make run` in terminal / air-gapped architecture / CSCS sovereign option.
   * Action: Upload to YouTube (Unlisted or Public) or Vimeo, and paste the URL into Section 2 above.
2. **Set `poesia-apertus` Repository to PUBLIC**:
   * Currently, ensure `https://github.com/OomAngel/poesia-apertus` is set to **Public** in GitHub repository settings.
3. **Optional: Hugging Face Dataset Card**:
   * If submitting the safety evaluation dataset, ensure `https://huggingface.co/datasets/GrootCappuccino/poesia-safety-screen` uses the HackApertus template and is set to Public.
4. **Submit on Portals**:
   * Open `http://hackapertus.ch/online-hack/submissions`.
   * Paste the fields from Section 2 of this document.
   * Attach `PoesIA_Report.pdf`.
   * Also complete the Devpost submission at `https://devpost.com/submit-to/30350-hack-apertus`.

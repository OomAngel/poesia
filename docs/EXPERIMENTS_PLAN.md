# Experiment Plan — Training Techniques & Model Comparison

---

## 1. MLflow Features (full)

| Feature | What it does | Why for PoesIA | Status |
|---------|-------------|----------------|--------|
| **Tracking** | Log params, metrics, artifacts per run | Already wired — loss curves, adapter zips | ✅ |
| **Model Registry** | Tag adapters as "staging" -> "production" | Auto-select best adapter for `--llm lora` | ❌ Not wired |
| **MLflow Evaluate** | Built-in eval for text models | Run `mlflow.evaluate()` with our scorer for per-adapter reports | ❌ Not wired |
| **MLflow Recipes** | Full pipeline: distill -> train -> eval -> register | One `mlflow run` does everything end-to-end | ❌ Not wired |
| **Parallel experiments** | Train multiple configs simultaneously | Compare r=16 vs r=32 vs r=64 in one session | ❌ Not tried |
| **Webhook alerts** | Notify when training ends | Terminal bell / Slack message when done | ❌ Not needed |

---

## 2. Base Models to Test

| Model | Params | VRAM 4-bit | Spanish fluency | Why try | Priority |
|-------|--------|-----------|-----------------|---------|----------|
| **Qwen2.5-1.5B** (current) | 1.5B | ~4GB | Good (trained on 100+ langs) | Baseline — already works | — |
| **Qwen2.5-3B** | 3B | ~6GB | Good (trained on 100+ langs) | Bigger version of current model — direct upgrade | ★★★★ |
| **Llama 3.2 3B** | 3.2B | ~6GB | Better than Qwen | Stronger multilingual, better poetry | ★★★ |
| **Gemma 2 2B** | 2.5B | ~4GB | Good (trained on 100+ langs) | Faster training, lighter weight | ★★ |
| ~~**Ruli-3B**~~ | 3B | — | — | ❌ **Does not exist on HuggingFace** — do not attempt | — |
| **Llama 3.1 8B** | 8B | ❌ Won't fit 8GB | Best | Would need offloading or cloud GPU | ★ (impractical) |

**Recommendation:** Try **Qwen2.5-3B** (direct upgrade, same family) or **Llama 3.2 3B** (stronger multilingual) first.

**Superseded 2026-10-04:** this table predates Qwen3, Qwen3.5 and Gemma 4, and its "won't
fit 8GB" assumes the default layout (embedding and `lm_head` in bf16). The current candidate
list, with per-model memory computed from tensor shapes, is in
`docs/RETRAINING_PLAN_2026-10.md` §3: up to ~9B is estimated to fit on the RTX 3070 (unmeasured).

**Correction 2026-07-30:** "Ruli-3B" was listed as a candidate but the model ID does not resolve on HuggingFace. Replaced with Qwen2.5-3B in practice; config at `mlops/configs/train_qwen3b.yaml`.
Swap cost: one config change (`model: "Ruli-3B"`) and rerun.

---

## 3. Training Techniques to Test

| Technique | Config change | Expected impact | Effort | Priority |
|-----------|--------------|----------------|--------|----------|
| **QLoRA r=32** (current) | `lora_r: 32` | Current baseline | Already done | — |
| **QLoRA r=64** | `lora_r: 64` | More capacity for patterns | Edit one line | ★★ |
| **LoRA all linear layers** | Add `gate_proj`, `up_proj`, `down_proj` | 2x more learnable params | Edit one line | ★★ |
| **Unsloth** | Replace LoRA with Unsloth | **2x training speed** | Blocked (2026-09-27): unsloth 2026.9.11 requires torch <2.13, transformers <=5.5, trl <=0.24, datasets <4.4; the env has 2.14, 5.14, 1.14, 5.0. Only a separate, older env could run it | ★★ (was ★★★★★) |
| **DPO** (new script) | Use `scripts/train_poetry_dpo.py` | Directly optimises for our metrics | ✅ **Trained, registered & evaluated** (`poetry-lora-dpo-expanded`, avg_syll_dev 6.07) — underperforms CE distilled (0.90) | ★★★★★ |
| **Multi-teacher distillation** | Ensemble Groq + Gemini outputs | More diverse training data | Run both APIs | ★★★ |
| **Syllable-filtered data** | Use `sonetos_filtered_t2.jsonl` | Cleaner training signal | Change data path | ★★★ |

---

## 4. Recommended Run Order

```
1. ✅ DPO — trained, registered, and evaluated (`poetry-lora-dpo-expanded`,
   avg_syll_dev 6.07 via the GGUF/llama.cpp eval path). Underperforms plain CE
   (distilled 0.90), so DPO did not beat the metric-driven baseline — see
   `ANALOGIA_PLAN.md` "Current adapter comparison".

2. Unsloth + r=64 (tests if faster training + more params helps) — not started
   → pip install unsloth; edit train_multiform.yaml (lora_r: 64)

3. ✅ Qwen2.5-3B + current config — trained and registered
   (`poesia-lora-soneto-qwen3b`), GGUF-converted. "Ruli-3B" never existed on
   HuggingFace (see §2 correction above); this was its replacement.

4. MLflow Recipes (automate the whole pipeline) — not started
   → mlflow run . -- entry-point train

5. MLflow Model Registry (auto-select best adapter) — registry itself is
   populated (9 adapters), but nothing tags/selects a "production" adapter
   automatically yet
   → Tag best run as "production" → LORAdAPTER_PATH reads from registry
```

---

## 5. What We'd Learn

| Experiment | Question answered |
|-----------|------------------|
| DPO | Can we directly optimise for syllable accuracy? |
| Unsloth | Does 2x faster training let us iterate faster? |
| Ruli-3B | Does a Spanish-native model write better poetry? |
| r=64 | Does more LoRA capacity improve metre learning? |
| MLflow Pipeline | Can we go from "raw data" to "deployed adapter" in one command? |

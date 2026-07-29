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
| **Llama 3.2 3B** | 3.2B | ~6GB | Better than Qwen | Stronger multilingual, better poetry | ★★★ |
| **Gemma 2 2B** | 2.5B | ~4GB | Good (trained on 100+ langs) | Faster training, lighter weight | ★★ |
| **Ruli-3B** | 3B | ~6GB | **Spanish-native** | Pretrained on Spanish text specifically | ★★★★ |
| **Llama 3.1 8B** | 8B | ❌ Won't fit 8GB | Best | Would need offloading or cloud GPU | ★ (impractical) |

**Recommendation:** Try **Ruli-3B** (Spanish-native) and **Gemma 2 2B** (lightweight) first.
Swap cost: one config change (`model: "Ruli-3B"`) and rerun.

---

## 3. Training Techniques to Test

| Technique | Config change | Expected impact | Effort | Priority |
|-----------|--------------|----------------|--------|----------|
| **QLoRA r=32** (current) | `lora_r: 32` | Current baseline | Already done | — |
| **QLoRA r=64** | `lora_r: 64` | More capacity for patterns | Edit one line | ★★ |
| **LoRA all linear layers** | Add `gate_proj`, `up_proj`, `down_proj` | 2x more learnable params | Edit one line | ★★ |
| **Unsloth** | Replace LoRA with Unsloth | **2x training speed** | Install unsloth, change 3 lines | ★★★★★ |
| **DPO** (new script) | Use `scripts/train_poetry_dpo.py` | Directly optimises for our metrics | New script ready | ★★★★★ |
| **Multi-teacher distillation** | Ensemble Groq + Gemini outputs | More diverse training data | Run both APIs | ★★★ |
| **Syllable-filtered data** | Use `sonetos_filtered_t2.jsonl` | Cleaner training signal | Change data path | ★★★ |

---

## 4. Recommended Run Order

```
1. DPO on existing v2 data (tests if preference learning helps)
   → python scripts/train_poetry_dpo.py mlops/configs/dpo_v1.yaml

2. Unsloth + r=64 (tests if faster training + more params helps)
   → pip install unsloth; edit train_multiform.yaml (lora_r: 64)

3. Ruli-3B + current config (tests if Spanish-native model helps)
   → edit train_multiform.yaml (model: "Ruli-3B")

4. MLflow Recipes (automate the whole pipeline)
   → mlflow run . -- entry-point train

5. MLflow Model Registry (auto-select best adapter)
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

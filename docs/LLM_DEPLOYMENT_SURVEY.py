"""Survey of LLM deployment options with resource budgets for PoesIA.

For each option we estimate:
  - Download size (model weights)
  - Peak RAM / VRAM during inference
  - Storage for generated cache
  - Cost per 1M tokens (or free-tier limits)
  - Latency for typical poetry generation (4-16 candidates)
  - Setup complexity (1-5)
  - Online/offline capability
"""

from dataclasses import dataclass


@dataclass
class LLMOption:
    name: str
    category: str  # hosted, local, edge
    download_gb: float  # model weights to download
    ram_gb: float  # peak RAM during inference
    vram_gb: float | None = None  # GPU VRAM if applicable
    storage_per_run_mb: float = 0.0  # disk cache per generation session
    cost_per_1m_tokens_usd: float = 0.0  # 0 for free/local
    latency_per_call_s: float = 1.0  # typical seconds per generation call
    setup_complexity: int = 1  # 1=easiest, 5=hardest
    online_required: bool = True
    notes: str = ""


OPTIONS = [
    # ── Hosted APIs ──
    LLMOption(
        "Groq (Llama 3.3 70B)", "hosted",
        download_gb=0, ram_gb=0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=0.8,
        setup_complexity=1, online_required=True,
        notes="Free tier: 30 RPM, 12k TPM. Already wired. Best free option.",
    ),
    LLMOption(
        "Gemini 2.5 Flash", "hosted",
        download_gb=0, ram_gb=0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=1.2,
        setup_complexity=1, online_required=True,
        notes="Free tier: 60 RPM. Good quality. Already wired.",
    ),
    LLMOption(
        "OpenAI GPT-4o-mini", "hosted",
        download_gb=0, ram_gb=0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0.15, latency_per_call_s=1.0,
        setup_complexity=1, online_required=True,
        notes="Pay-as-you-go. ~$0.0005 per typical poetry session. Already wired.",
    ),
    LLMOption(
        "OpenAI GPT-4o", "hosted",
        download_gb=0, ram_gb=0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=2.50, latency_per_call_s=2.0,
        setup_complexity=1, online_required=True,
        notes="High quality but expensive. ~$0.01 per poetry session.",
    ),
    LLMOption(
        "Anthropic Claude 3 Haiku", "hosted",
        download_gb=0, ram_gb=0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0.25, latency_per_call_s=1.5,
        setup_complexity=2, online_required=True,
        notes="Needs new client. Fast/cheap, good for creative tasks.",
    ),
    LLMOption(
        "Together AI (Llama 3.1 8B)", "hosted",
        download_gb=0, ram_gb=0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0.18, latency_per_call_s=0.6,
        setup_complexity=2, online_required=True,
        notes="OpenAI-compatible API. No rate limits (paid). Fast inference.",
    ),

    # ── Local: Ollama ──
    LLMOption(
        "Ollama + Llama 3.2 3B (Q4)", "local",
        download_gb=2.0, ram_gb=4.0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=3.0,
        setup_complexity=2, online_required=False,
        notes="Ollama pull llama3.2:3b. ~1.9B params. Runs on any laptop CPU.",
    ),
    LLMOption(
        "Ollama + Llama 3.1 8B (Q4)", "local",
        download_gb=4.7, ram_gb=8.0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=6.0,
        setup_complexity=2, online_required=False,
        notes="Ollama pull llama3.1:8b. Decent quality, needs 8GB RAM.",
    ),
    LLMOption(
        "Ollama + Qwen 2.5 7B (Q4)", "local",
        download_gb=4.1, ram_gb=8.0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=5.0,
        setup_complexity=2, online_required=False,
        notes="Ollama pull qwen2.5:7b. Strong multilingual (good for ES+EN).",
    ),
    LLMOption(
        "Ollama + Gemma 2 2B (Q4)", "local",
        download_gb=1.5, ram_gb=3.0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=2.0,
        setup_complexity=2, online_required=False,
        notes="Lightest viable option. Needs only 3GB RAM. Runs on old laptops.",
    ),
    LLMOption(
        "Ollama + Phi-3-mini 3.8B (Q4)", "local",
        download_gb=2.3, ram_gb=4.5, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=3.5,
        setup_complexity=2, online_required=False,
        notes="Microsoft Phi-3. Strong small model, good for structured output.",
    ),
    LLMOption(
        "Ollama + Mistral 7B (Q4)", "local",
        download_gb=4.1, ram_gb=8.0, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=5.5,
        setup_complexity=2, online_required=False,
        notes="Strong creative writing quality. Needs 8GB RAM.",
    ),

    # ── Local: llama.cpp (no Ollama, direct) ──
    LLMOption(
        "llama.cpp + Llama 3.2 3B (Q4)", "local",
        download_gb=2.0, ram_gb=3.5, storage_per_run_mb=0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=2.5,
        setup_complexity=3, online_required=False,
        notes="Direct GGUF. Slightly faster than Ollama, more setup. No daemon.",
    ),

    # ── Local: GPU-accelerated ──
    LLMOption(
        "vLLM + Llama 3.1 8B (FP16)", "local-gpu",
        download_gb=16.0, ram_gb=4.0, vram_gb=16.0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=0.3,
        setup_complexity=4, online_required=False,
        notes="Fastest self-hosted. Needs GPU with 16GB VRAM (RTX 4080, A10).",
    ),
    LLMOption(
        "vLLM + Qwen 2.5 7B (FP16)", "local-gpu",
        download_gb=14.0, ram_gb=4.0, vram_gb=14.0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=0.3,
        setup_complexity=4, online_required=False,
        notes="Good multilingual, needs GPU with 14GB+ VRAM (RTX 3080/4080).",
    ),
    LLMOption(
        "llama.cpp + Llama 3.1 8B (Q4, GPU offload)", "local-gpu",
        download_gb=4.7, ram_gb=2.0, vram_gb=6.0,
        cost_per_1m_tokens_usd=0, latency_per_call_s=1.0,
        setup_complexity=3, online_required=False,
        notes="Partial GPU offload. Needs 6GB VRAM. ~50 tok/s on RTX 3060.",
    ),
]


def main():
    print("=" * 110)
    print("LLM DEPLOYMENT OPTIONS — PoesIA Resource Budget Survey")
    print("=" * 110)

    # Group by category
    categories = {
        "hosted": "── HOSTED APIs (current + candidates) ──",
        "local": "── LOCAL / OFFLINE (CPU, Ollama/llama.cpp) ──",
        "local-gpu": "── LOCAL GPU-ACCELERATED (vLLM, partial offload) ──",
    }

    for cat, header in categories.items():
        items = [o for o in OPTIONS if o.category == cat]
        if not items:
            continue

        print(f"\n{header}")
        print("-" * 110)
        print(f"{'Option':<38} {'DL(G)':<7} {'RAM(G)':<7} {'VRAM(G)':<8} "
              f"{'$/1M tok':<10} {'Lat(s)':<8} {'Setup':<6} {'Online':<7}  Notes")
        print("-" * 110)

        for o in items:
            vram_str = f"{o.vram_gb:.0f}" if o.vram_gb else "—"
            cost_str = f"${o.cost_per_1m_tokens_usd:.3f}" if o.cost_per_1m_tokens_usd > 0 else "free"
            if "Free tier" in o.notes:
                cost_str = "free*"
            online_str = "yes" if o.online_required else "no"
            print(f"{o.name:<38} {o.download_gb:<7.1f} {o.ram_gb:<7.1f} {vram_str:<8} "
                  f"{cost_str:<10} {o.latency_per_call_s:<8.1f} {o.setup_complexity:<6} "
                  f"{online_str:<7} {o.notes[:50]}")

    print(f"\n{'='*110}")
    print("BUDGET NOTES")
    print(f"{'='*110}")
    print()
    print("Per-session cost (hosted APIs):")
    print("  A typical poetry write uses ~500 input tokens + ~200 output tokens per candidate.")
    print("  With n_candidates=16 (default) and 14-line soneto: ~12 000 total tokens.")
    print(f"  Groq: free (12k TPM free tier fits 1 session)")
    print(f"  Gemini: free (60 RPM free tier)")
    print(f"  GPT-4o-mini: 12k * ($0.15/1M) = $0.0018 per soneto")
    print(f"  GPT-4o: 12k * ($2.50/1M) = $0.03 per soneto")
    print(f"  Claude 3 Haiku: 12k * ($0.25/1M) = $0.003 per soneto")
    print()
    print("Storage (self-hosted):")
    print("  Ollama caches downloaded models at ~/.ollama/models/")
    print("  Llama 3.2 3B (Q4): 2.0 GB — fits on any machine")
    print("  Gemma 2 2B (Q4): 1.5 GB — smallest viable")
    print("  Llama 3.1 8B (Q4): 4.7 GB — 14GB free disk minimum")
    print("  Multiple models can coexist; add the downloads.")
    print()
    print("RAM (self-hosted, during inference):")
    print("  Gemma 2 2B: 3 GB — works on 4GB RAM machines (old laptops)")
    print("  Llama 3.2 3B: 4 GB — works on 8GB RAM machines")
    print("  Phi-3-mini 3.8B: 4.5 GB — works on 8GB RAM machines")
    print("  Qwen 2.5 7B: 8 GB — needs 16GB RAM machine")
    print("  Llama 3.1 8B: 8 GB — needs 16GB RAM machine")
    print()
    print("Latency impact (self-hosted, CPU inference):")
    print("  Poetry needs ~200 tokens/soneto. At 10 tok/s (8B model on CPU): ~20s.")
    print("  At 30 tok/s (3B model on CPU): ~7s.")
    print("  At 100 tok/s (hosted API): ~2s.")
    print("  ConstrainedLoop generates 16 candidates per line × 14 lines:")
    print("    Hosted: ~1 min total")
    print("    Local 3B (CPU): ~5 min total")
    print("    Local 8B (CPU): ~15 min total")
    print("    Local 8B (GPU, vLLM): ~30s total")
    print()
    print("RECOMMENDATION:")
    print("  Default: Groq (free, already wired). Zero setup, zero cost.")
    print("  Offline/backup: Ollama + Gemma 2 2B or Llama 3.2 3B (1.5-2GB download, 3-4GB RAM)")
    print("  Quality offline: Ollama + Qwen 2.5 7B (strong ES+EN, 4.1GB download, 8GB RAM)")
    print("  Fast local: llama.cpp with partial GPU offload on any CUDA GPU")


if __name__ == "__main__":
    main()

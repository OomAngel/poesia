#!/usr/bin/env python3
"""Evaluate an adapter (or a bare base model) on generated sonnets, both languages.

Rebuilt 2026-10-04 for the retraining (docs/RETRAINING_PLAN_2026-10.md §6 step 2):

- Spanish sonnets (11-syllable lines, ABBAABBACDCDCD) and English Shakespearean sonnets
  (10 syllables, ABABCDCDEFEFGG), 6 themes each by default, several seeded samples per
  theme, so a score is a mean over 36 poems rather than 3 unseeded ones.
- Scores come from poesia.evaluation.poem_eval: line-count accuracy, per-line syllable
  deviation (the old |mean - 11| let long and short lines cancel), metre pass rate and
  rhyme accuracy. The Spanish counter's own error is measured by
  scripts/check_scansion_vs_adso.py; compare deviations against it.
- ``--base-model`` without ``--adapter`` evaluates the base model alone (a baseline);
  ``--memory-layout low_vram`` lets 8-9B models load in 8 GB.

Metrics go to MLflow (nested under ``--parent-run-id`` when given) and to a JSON report.

Usage:
    python scripts/evaluate_adapter_mlflow.py --adapter models/smoke-qwen3-8b/final_adapter
    python scripts/evaluate_adapter_mlflow.py --base-model Qwen/Qwen3-4B-Instruct-2507 \\
        --languages es en --samples 3 --out reports/eval_qwen3_4b_base.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time

import mlflow

from poesia.evaluation.poem_eval import aggregate, score_poem
from poesia.forms.definitions import get_form

FORMS = {"es": "soneto", "en": "sonnet_shakespearean"}
THEMES = {
    "es": ["luna", "mar", "tiempo", "noche", "soledad", "memoria"],
    "en": ["moon", "sea", "time", "night", "solitude", "memory"],
}


def _phonology(language: str):
    if language == "es":
        from poesia.phonology.spanish import SpanishPhonology

        return SpanishPhonology()
    from poesia.phonology.english import EnglishPhonology

    return EnglishPhonology()


def _make_llm_client(
    adapter_path: str | None, base_model: str | None, ollama_model: str | None = None
):
    """OllamaClient when an Ollama model is named (how the Hack Apertus entry runs Apertus:
    GGUF in Ollama, chat format). Otherwise LoRAClient (bitsandbytes 4-bit) when it runs on this GPU; otherwise the GGUF/llama.cpp
    client next to the adapter (the laptop). The check is bnb_4bit_usable(), not
    cuda_usable(): on the laptop torch runs on the GPU (sm_50) but bitsandbytes cannot."""
    if ollama_model:
        from poesia.generation.llm_client import OllamaClient

        return OllamaClient(model=ollama_model, timeout=600.0)

    from poesia.device import bnb_4bit_usable
    from poesia.generation.llm_client import LoRAClient

    if bnb_4bit_usable():
        return LoRAClient(adapter_path=adapter_path, base_model=base_model)

    import glob

    from poesia.exceptions import LLMProviderError
    from poesia.generation.llama_cpp import LlamaCppLoRAClient

    matches = glob.glob(os.path.join(os.path.dirname(adapter_path or ""), "*Q4_K_M.gguf"))
    if not matches:
        raise LLMProviderError(
            "No usable CUDA device for bitsandbytes 4-bit inference, and no *Q4_K_M.gguf "
            f"next to {adapter_path} for the llama.cpp fallback (poesia/generation/llama_cpp.py).",
            provider="lora",
        )
    return LlamaCppLoRAClient(model_path=matches[0])


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def evaluate(
    adapter_path: str | None,
    base_model: str | None,
    languages: list[str],
    themes: dict[str, list[str]],
    samples: int,
    seed: int,
    parent_run_id: str | None = None,
    out_path: str | None = None,
    ollama_model: str | None = None,
) -> dict:
    from poesia.generation.constrained_loop import ConstrainedLoop

    mlflow.set_tracking_uri(os.environ.get("DATABASE_URL", "sqlite:///mlruns/mlflow.db"))
    label = adapter_path or f"base:{base_model or 'ollama-' + str(ollama_model)}"
    if parent_run_id:
        run = mlflow.start_run(run_id=parent_run_id, nested=True)
    else:
        mlflow.set_experiment("poesia-evaluation")
        run = mlflow.start_run(run_name=f"eval-{os.path.basename(label.rstrip('/'))}")

    llm = _make_llm_client(
        adapter_path, base_model, ollama_model
    )  # loaded once, reused for every poem
    report: dict = {
        "adapter": adapter_path,
        "base_model": llm.model,
        "backend": "ollama" if ollama_model else "transformers",
        "samples": samples,
        "seed": seed,
        "languages": {},
    }
    with run:
        mlflow.log_params(
            {
                "adapter": adapter_path or "",
                "base_model": llm.model,
                "samples": samples,
                "seed": seed,
                "languages": ",".join(languages),
                "memory_layout": os.environ.get("POESIA_MEMORY_LAYOUT", "default"),
            }
        )
        for lang in languages:
            form = get_form(FORMS[lang], lang)
            phon = _phonology(lang)
            poems = []
            for theme in themes[lang]:
                for k in range(samples):
                    poem_seed = seed + k
                    _seed_everything(poem_seed)
                    t0 = time.time()
                    loop = ConstrainedLoop(language=lang, form=FORMS[lang], llm=llm)
                    result = loop.run(theme=theme, n_candidates=8, max_repair_attempts=4)
                    scores = score_poem(result.lines, form, phon)
                    scores.update(
                        theme=theme,
                        seed=poem_seed,
                        seconds=round(time.time() - t0, 1),
                        lines=list(result.lines),
                    )
                    poems.append(scores)
                    print(
                        f"[{lang}] {theme} seed {poem_seed}: dev {scores['syllable_abs_dev']}, "
                        f"metre {scores['metre_pass_rate']}, rhyme {scores['rhyme_accuracy']}, "
                        f"{scores['seconds']}s"
                    )
            agg = aggregate(poems)
            report["languages"][lang] = {"form": FORMS[lang], "aggregate": agg, "poems": poems}
            for key, value in agg.items():
                if value is not None:
                    mlflow.log_metric(f"{lang}_{key}", value)
            print(f"[{lang}] aggregate: {json.dumps(agg)}")

        if out_path:
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                f.write("\n")
            mlflow.log_artifact(out_path)
            print(f"Report: {out_path}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--adapter", default=None, help="LoRA adapter dir (final_adapter)")
    ap.add_argument("--base-model", default=None, help="base model; alone = baseline run")
    ap.add_argument("--languages", nargs="+", default=["es", "en"], choices=sorted(FORMS))
    ap.add_argument("--themes-es", nargs="+", default=THEMES["es"])
    ap.add_argument("--themes-en", nargs="+", default=THEMES["en"])
    ap.add_argument("--samples", type=int, default=3, help="seeded samples per theme")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--memory-layout", default=None, choices=["default", "low_vram"])
    ap.add_argument("--out", default=None, help="JSON report path")
    ap.add_argument(
        "--ollama-model", default=None, help="evaluate a model served by Ollama (OLLAMA_HOST)"
    )
    ap.add_argument("--parent-run-id", default=None, help="MLflow run to nest under")
    args = ap.parse_args()
    if not (args.adapter or args.base_model or args.ollama_model):
        ap.error("give --adapter, --base-model (or both), or --ollama-model")
    if args.memory_layout:
        os.environ["POESIA_MEMORY_LAYOUT"] = args.memory_layout
    evaluate(
        args.adapter,
        args.base_model,
        args.languages,
        {"es": args.themes_es, "en": args.themes_en},
        args.samples,
        args.seed,
        parent_run_id=args.parent_run_id or None,
        out_path=args.out,
        ollama_model=args.ollama_model,
    )

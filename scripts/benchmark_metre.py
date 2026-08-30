#!/usr/bin/env python3
"""Compare LLM backends on raw metrical accuracy (no repair loop).

For each (backend, form) pair this generates candidate lines directly through
``CandidateGenerator`` — bypassing the accept/reject/repair loop — and reports
the fraction whose scanned syllable count matches the form's target. The repair
loop is deliberately excluded so the raw model quality is visible: the
fine-tune's soneto-domain advantage and its out-of-domain overfit both show up
as metre accuracy, instead of being papered over by repairs.

Usage:
    python scripts/benchmark_metre.py
    python scripts/benchmark_metre.py --backends llama_cpp,groq --forms soneto:es,haiku:es
    python scripts/benchmark_metre.py --backends stub --forms soneto:es --n-candidates 2 --positions 1  # smoke

``.env`` is loaded best-effort (GROQ_API_KEY / LLAMACPP_MODEL_PATH). The
``llama_cpp`` backend generates candidates sequentially, so a full run is slow
on the local GPU — lower ``--n-candidates``/``--positions`` for a quick pass.
"""

from __future__ import annotations

import argparse
import os


def _load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv()


def _measure(
    backend: str,
    form: str,
    language: str,
    theme: str,
    n_candidates: int,
    positions: int,
) -> dict[str, object]:
    from poesia.forms.definitions import get_form
    from poesia.generation.candidate_generator import CandidateGenerator
    from poesia.generation.constrained_loop import _clean_candidate, _phonology_for
    from poesia.generation.registry import get_llm

    label = f"{form}:{language}"
    try:
        form_spec = get_form(form, language)
        llm = get_llm(backend)
        generator = CandidateGenerator(llm)
        phonology = _phonology_for(language)
    except Exception as exc:  # noqa: BLE001 — report backend unavailability
        return {"backend": backend, "form": label, "error": str(exc)}

    correct = 0
    total = 0
    samples: list[str] = []
    for pos in range(min(positions, form_spec.total_lines)):
        target = form_spec.syllables_for_line(pos)
        try:
            raw = generator.generate_lines(
                theme=theme,
                language=language,
                n_candidates=n_candidates,
                target_syllables=target,
            )
        except Exception as exc:  # noqa: BLE001 — auth/model-missing mid-run
            return {"backend": backend, "form": label, "error": str(exc)}

        for line in raw:
            clean = _clean_candidate(line)
            scan = phonology.scan_line(clean)
            total += 1
            ok = scan.metrical_syllable_count == target
            if ok:
                correct += 1
            if len(samples) < 4:
                mark = "✓" if ok else "✗"
                samples.append(f"  {mark} {scan.metrical_syllable_count}/{target}  {clean}")

    return {
        "backend": backend,
        "form": label,
        "correct": correct,
        "total": total,
        "pct": (100.0 * correct / total) if total else 0.0,
        "samples": samples,
    }


def _measure_draft(
    backend: str,
    form: str,
    language: str,
    theme: str,
) -> dict[str, object]:
    """Measure raw whole-poem draft accuracy (no repair), for models used via
    the --draft path rather than line-by-line generation."""
    from poesia.forms.definitions import get_form
    from poesia.generation.constrained_loop import (
        ConstrainedLoop,
        _clean_candidates,
        _phonology_for,
    )
    from poesia.generation.registry import get_llm

    label = f"{form}:{language}"
    try:
        form_spec = get_form(form, language)
        llm = get_llm(backend)
        loop = ConstrainedLoop(language=language, form=form, llm=llm)
        phonology = _phonology_for(language)
        raw = llm.generate(loop._build_draft_prompt(theme, None), n=1, temperature=0.9)
    except Exception as exc:  # noqa: BLE001 — report backend unavailability
        return {"backend": backend, "form": label, "error": str(exc)}

    if not raw or not raw[0].strip():
        return {"backend": backend, "form": label, "error": "empty completion"}

    lines = [ln.strip() for ln in raw[0].splitlines() if ln.strip()]
    lines = _clean_candidates(lines, [])[: form_spec.total_lines]

    correct = 0
    total = 0
    samples: list[str] = []
    for i, line in enumerate(lines):
        target = form_spec.syllables_for_line(i)
        scan = phonology.scan_line(line)
        total += 1
        ok = scan.metrical_syllable_count == target
        if ok:
            correct += 1
        if len(samples) < 4:
            mark = "✓" if ok else "✗"
            samples.append(f"  {mark} {scan.metrical_syllable_count}/{target}  {line}")

    return {
        "backend": backend,
        "form": label,
        "correct": correct,
        "total": total,
        "pct": (100.0 * correct / total) if total else 0.0,
        "samples": samples,
    }


def _log_mlflow(result: dict[str, object], mode: str, theme: str) -> None:
    """Log one benchmark cell to MLflow (best-effort; no-op without mlflow)."""
    try:
        import mlflow  # noqa: PLC0415 — lazy, keeps the script importable without mlflow
    except ImportError:
        return
    try:
        mlflow.set_tracking_uri(os.environ.get("DATABASE_URL", "file:./mlruns"))
        with mlflow.start_run(run_name=f"benchmark-metre-{result['backend']}-{result['form']}"):
            mlflow.log_param("backend", result["backend"])
            mlflow.log_param("form", result["form"])
            mlflow.log_param("mode", mode)
            mlflow.log_param("theme", theme)
            if "error" in result:
                mlflow.log_param("error", str(result["error"]))
            else:
                mlflow.log_metric("metre_accuracy", round(float(result["pct"]), 2))
                mlflow.log_metric("correct_lines", int(result["correct"]))
                mlflow.log_metric("total_lines", int(result["total"]))
                mlflow.log_text("\n".join(result["samples"]), "samples.txt")  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 — tracking must never fail the benchmark
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backends", default="llama_cpp,groq", help="comma-separated backend names"
    )
    parser.add_argument("--forms", default="soneto:es,haiku:es", help="comma-separated form:lang")
    parser.add_argument("--n-candidates", type=int, default=4, help="candidates per line position")
    parser.add_argument(
        "--positions", type=int, default=3, help="line positions to sample per form"
    )
    parser.add_argument("--theme", default="la luna", help="theme for generated lines")
    parser.add_argument(
        "--draft",
        action="store_true",
        help="measure the whole-poem --draft path instead of line generation",
    )
    args = parser.parse_args()

    _load_env()

    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    forms: list[tuple[str, str]] = []
    for spec in args.forms.split(","):
        spec = spec.strip()
        if not spec:
            continue
        name, _, lang = spec.partition(":")
        forms.append((name or "soneto", lang or "es"))

    mode = (
        "draft (whole-poem)"
        if args.draft
        else f"{args.n_candidates} candidates × {args.positions} positions"
    )
    mode_key = "draft" if args.draft else "line"
    print(f"Raw metrical accuracy — {mode}, theme={args.theme!r}\n")

    results: list[dict[str, object]] = []
    for backend in backends:
        for form, lang in forms:
            print(f"· {backend}/{form}:{lang} …", flush=True)
            if args.draft:
                r = _measure_draft(backend, form, lang, args.theme)
            else:
                r = _measure(backend, form, lang, args.theme, args.n_candidates, args.positions)
            results.append(r)
            _log_mlflow(r, mode_key, args.theme)

    print()
    print(f"{'backend':<12} {'form':<16} {'correct':>8} {'total':>6} {'%':>6}")
    print("-" * 52)
    for r in results:
        if "error" in r:
            print(f"{r['backend']:<12} {r['form']:<16} {'ERR':>8}  {str(r['error'])[:44]}")
        else:
            print(
                f"{r['backend']:<12} {r['form']:<16} "
                f"{r['correct']:>8} {r['total']:>6} {r['pct']:>5.0f}%"
            )

    for r in results:
        samples = r.get("samples")
        if samples:
            print(f"\n[{r['backend']}/{r['form']}] samples:")
            print("\n".join(samples))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()

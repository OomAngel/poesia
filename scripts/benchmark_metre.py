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

    print(
        f"Raw metrical accuracy — {args.n_candidates} candidates × "
        f"{args.positions} positions, theme={args.theme!r}\n"
    )

    results: list[dict[str, object]] = []
    for backend in backends:
        for form, lang in forms:
            print(f"· {backend}/{form}:{lang} …", flush=True)
            results.append(
                _measure(backend, form, lang, args.theme, args.n_candidates, args.positions)
            )

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

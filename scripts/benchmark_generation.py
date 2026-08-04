"""Benchmark PoesIA generation throughput (poems and illustrations).

Verifies the two speed fixes on the actual local hardware:

- ``LoRAClient.generate`` batches all ``n`` candidates in ONE forward pass
  (``num_return_sequences=n``) instead of ``n`` sequential calls — measure
  with ``--poem`` and compare to the old path with ``--sequential``.
- Image backends: ``--image`` times real text-to-image panels through the
  ``auto`` backend (Cloudflare SDXL when ``CLOUDFLARE_*`` env is set, else the
  offline procedural renderer).

Usage::

    python scripts/benchmark_generation.py            # poem + image (defaults)
    python scripts/benchmark_generation.py --poem-only
    python scripts/benchmark_generation.py --image-only --panels 3
    python scripts/benchmark_generation.py --sequential   # + old n×1 path (~40s)

Requires the GPU stack (torch/transformers) for the poem path. ``.env`` is
loaded best-effort so the Cloudflare image backend resolves automatically.
"""

from __future__ import annotations

import argparse
import time

from poesia.galeria.pipeline import get_image_backend
from poesia.generation.llm_client import LoRAClient

_PROMPT = (
    "You are writing a Spanish poem on the theme: una canaria menuda baila en el\n"
    "manglar junto al mar. Write line 3. Exactly 11 syllables. End the line with a\n"
    "word that rhymes with \"cantar\". Output ONLY the single bare poetry line."
)

_IMAGE_PROMPT = (
    "una canaria menuda de enorme cabellera con vestido de fiesta, baila un baile "
    "sensual en los manglares de Mexico junto al mar; en la mesa mole y maiz"
)


def _load_env() -> None:
    """Load .env so CLOUDFLARE_* resolves for --image (python-dotenv is core)."""
    from dotenv import load_dotenv

    load_dotenv()


def bench_poem(sequential: bool, lines: int, n: int) -> None:
    """Time batched LoRA generation; optionally compare the old n×1 path."""
    client = LoRAClient()
    print("· loading model + warmup (one batched call)…")
    t0 = time.time()
    client.generate(_PROMPT, n=1, temperature=0.9)
    print(f"· model load ≈ {time.time() - t0:.1f}s\n")

    if sequential:
        t0 = time.time()
        got: list[str] = []
        for _ in range(n):
            got.extend(client.generate(_PROMPT, n=1, temperature=0.9))
        print(f"· OLD sequential (n={n} separate calls): {time.time() - t0:.2f}s"
              f"  → {len(got)} lines")

    t0 = time.time()
    for _ in range(lines):
        client.generate(_PROMPT, n=n, temperature=0.9)
    elapsed = time.time() - t0
    print(f"· NEW batched ({lines} line-positions × n={n}): {elapsed:.2f}s"
          f"  → {elapsed / lines:.2f}s per line")
    if sequential:
        print("  (sequential vs batched for one line-position: "
              f"{time.time() - t0:.2f}s vs {elapsed / lines:.2f}s per line)")
    else:
        print("  hint: re-run with --sequential to compare against the old path.")


def bench_image(panels: int) -> None:
    """Time real text-to-image generation through the auto backend."""
    backend = get_image_backend("auto")
    print(f"· image backend: {type(backend).__name__}")
    latencies: list[float] = []
    for i in range(panels):
        t0 = time.time()
        img = backend.generate_image(prompt=f"{_IMAGE_PROMPT} (panel {i + 1})")
        latencies.append(time.time() - t0)
        print(f"  panel {i + 1}: {latencies[-1]:.1f}s  ({len(img)} bytes)")
    avg = sum(latencies) / len(latencies)
    print(f"  avg: {avg:.1f}s/panel  → a 4-panel auca ≈ {avg * 4:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poem-only", action="store_true", help="skip the image benchmark")
    parser.add_argument("--image-only", action="store_true", help="skip the poem benchmark")
    parser.add_argument(
        "--sequential", action="store_true", help="also time the old n×1 generation path"
    )
    parser.add_argument("--lines", type=int, default=4, help="line-positions in the poem bench")
    parser.add_argument("--n", type=int, default=16, help="candidates per line")
    parser.add_argument("--panels", type=int, default=2, help="image panels to time")
    args = parser.parse_args()

    _load_env()
    if not args.image_only:
        bench_poem(sequential=args.sequential, lines=args.lines, n=args.n)
        print()
    if not args.poem_only:
        bench_image(panels=args.panels)


if __name__ == "__main__":
    main()

"""Generate a review batch of calaveritas for the fine-tuning set (step 2, 2026-10-09).

Writes one JSON record per poem (request, poem, model, timings, engine commit) to a git-ignored
JSONL file; poems never go into git (AGENTS.md). Names are invented first names, generic public
roles and famous people who have died (homage); no living private person.

Usage (CSCS through the local key proxy, see docs/hack_apertus/CSCS_USAGE.md):
  PYTHONPATH=src python scripts/calaveritas_data/generate_batch.py OUT.jsonl \\
      --url http://127.0.0.1:8790/v1 --model swiss-ai/Apertus-v1.5-70B --n 200 --workers 2

The Calaveritas blind rounds (2026-11-08) use Nebius Token Factory and the 40-request set, traced:
  KEY=... PYTHONPATH=src python scripts/calaveritas_data/generate_batch.py OUT.jsonl \\
      --url https://api.tokenfactory.nebius.com/v1 --model deepseek-ai/DeepSeek-V4-Pro-0813 \\
      --extra '{"reasoning_effort":"none"}' --n 40 --workers 3 --tag d10 --trace \\
      --ids 4,6,7,13,14,20,21,22,23,25,26,34 --price-in 1.60 --price-out 4.79
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from poesia.calaveritas import generator
from poesia.calaveritas.guard import Rejection, validate_request
from poesia.calaveritas.options import TRAITS

NAMES = {
    "es": [
        "Lupita",
        "Don Ramón",
        "Karla",
        "Pedro",
        "Sofía",
        "Tito",
        "Lucha",
        "Memo",
        "Rosario",
        "Chuy",
        "Paty",
        "Beto",
        "Maru",
        "Toño",
        "Fer",
        "Cata",
        "Nacho",
        "Chela",
        "Rodrigo",
        "Ximena",
    ],
    "en": [
        "Lucy",
        "Grandpa Joe",
        "Maggie",
        "Dave",
        "Rosie",
        "Sam",
        "Aunt May",
        "Leo",
        "Nina",
        "Ben",
    ],
}
PETS = {
    "es": ["Firulais", "Michi", "Canelo", "Pelusa", "Chispa"],
    "en": ["Max", "Bella", "Biscuit", "Luna"],
}
PUBLIC = {
    "es": [
        "el presidente municipal",
        "la gobernadora",
        "el diputado",
        "la senadora",
        "el alcalde",
        "el director de la escuela",
        "la jefa de policía",
    ],
    "en": ["the mayor", "the senator", "the governor", "the city councillor"],
}
LATE = {
    "es": [
        "Frida Kahlo",
        "Pedro Infante",
        "Cantinflas",
        "Juan Gabriel",
        "Chavela Vargas",
        "Sor Juana",
        "José Guadalupe Posada",
        "Gabriel García Márquez",
    ],
    "en": ["Frida Kahlo", "Elvis Presley", "Marilyn Monroe", "Charlie Chaplin"],
}
DETAILS = {
    "es": [
        "siempre pide la cuenta dividida",
        "prometió bachear todas las calles",
        "se come los zapatos",
        "canta rancheras en la regadera",
        "nunca contesta los mensajes",
        "",
    ],
    "en": [
        "always splits the bill",
        "promised to fix every pothole",
        "chews the sofa",
        "sings in the shower",
        "never answers messages",
        "",
    ],
}
TONES = ["carinosa", "picara", "politica", "escolar", "clasica"]
RECIPIENTS = ["amistad", "familia", "pareja", "trabajo", "publica", "mascota", "yo", "fallecida"]


def make_request(rng: random.Random) -> dict:
    lang = "es" if rng.random() < 0.75 else "en"
    rec = rng.choice(RECIPIENTS)
    tone = rng.choice(TONES)
    if rec == "publica":
        name, tone = rng.choice(PUBLIC[lang]), rng.choice(["politica", "picara", "clasica"])
    elif rec == "fallecida":
        name, tone = rng.choice(LATE[lang]), rng.choice(["carinosa", "clasica"])
    elif rec == "mascota":
        name = rng.choice(PETS[lang])
    elif rec == "yo":
        # the page asks for the writer's own name (static/app.js); no extra draw, so the same seed
        # gives the same requests as before (2026-11-07)
        name = NAMES[lang][TONES.index(tone) % len(NAMES[lang])]
    else:
        name = rng.choice(NAMES[lang])
    minor = tone == "escolar" and rec != "pareja" and rng.random() < 0.5
    detail = rng.choice(DETAILS[lang])
    if rec in ("amistad", "familia", "pareja", "trabajo"):
        detail = detail[:80]
    return {
        "language": lang,
        "name": name,
        "recipient": rec,
        "tone": tone,
        "stanzas": rng.choice([2, 3, 3]),
        "traits": rng.sample(sorted(TRAITS), rng.randint(1, 3)),
        "detail": detail,
        "birth_year": 2014 if minor else 1985,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--tag", default="b20261009", help="id prefix; same seed = same requests")
    ap.add_argument("--key-env", default="KEY", help="environment variable holding the API key")
    ap.add_argument(
        "--extra",
        default="{}",
        help='JSON merged into each request, e.g. {"reasoning_effort": "low"}',
    )
    ap.add_argument("--min-tokens", type=int, default=0, help="raise max_tokens (reasoning models)")
    ap.add_argument("--no-sense", action="store_true", help="no line log-probabilities (baseline)")
    ap.add_argument("--shard", default="0/1", help="I/K: only requests whose index %% K == I")
    ap.add_argument(
        "--n-only", type=int, default=0, help="stop after this many requests (A/B subsets)"
    )
    ap.add_argument("--draft-url", help="a second model for drafts and repairs (names masked)")
    ap.add_argument("--draft-model")
    ap.add_argument("--draft-key-env", default="DRAFT_KEY")
    ap.add_argument("--draft-extra", default="{}")
    ap.add_argument("--draft-langs", default="es")
    ap.add_argument(
        "--trace",
        action="store_true",
        help="store each request's drafts and why each was discarded (generator.write trace)",
    )
    ap.add_argument("--price-in", type=float, default=0.0, help="$ per million input tokens")
    ap.add_argument("--price-out", type=float, default=0.0, help="$ per million output tokens")
    ap.add_argument(
        "--ids",
        default="",
        help="only these request numbers, e.g. 4,6,13 (the same seed gives the same requests); "
        "resuming is off with --ids",
    )
    args = ap.parse_args()
    rng = random.Random(args.seed)  # noqa: S311 - sampling a test batch
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()

    class Counted(generator.Provider):
        """One per request, so the record says how many model calls the poem took."""

        calls = 0

        def chat(self, msgs, temperature=0.9, max_tokens=160, timeout=None):
            self.calls += 1  # small race across the engine's threads is acceptable for a count
            return super().chat(msgs, temperature, max_tokens, timeout)

    base = dict(
        label=args.model,
        url=args.url,
        model=args.model,
        key=os.environ.get(args.key_env, "x"),
        sends_names=True,
        extra=json.loads(args.extra),
        min_tokens=args.min_tokens,
        sense=not args.no_sense,
        price_in=args.price_in,
        price_out=args.price_out,
    )
    provider = generator.Provider(
        args.model,
        args.url,
        args.model,
        os.environ.get(args.key_env, "x"),
        True,
        json.loads(args.extra),
        args.min_tokens,
    )
    out = Path(args.out)
    done = sum(1 for _ in out.open()) if out.exists() else 0

    def one(i: int, raw: dict) -> dict:
        t0 = time.time()
        rec = {
            "id": f"{args.tag}-{i:04d}",
            "request": raw,
            "model": args.model,
            "engine_commit": commit,
            "created": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        }
        counted = Counted(**base)
        if args.draft_url and args.draft_model:
            counted.drafter = Counted(
                label=args.draft_model,
                url=args.draft_url,
                model=args.draft_model,
                key=os.environ.get(args.draft_key_env, ""),
                sends_names=False,
                extra=json.loads(args.draft_extra),
            )
            counted.draft_langs = tuple(args.draft_langs.split(","))
        try:
            req = validate_request(raw)
            trace: list[dict] | None = [] if args.trace else None
            if trace is not None:
                rec["trace"] = trace
            rec["poem"] = generator.write(
                req,
                [counted],
                rng=random.Random(i),  # noqa: S311
                trace=trace,
            ).as_dict()
        except Rejection as r:
            rec["error"] = "rejected:" + r.code
        except generator.GenerationError as e:
            rec["error"] = e.code
        rec["seconds"] = round(time.time() - t0, 1)
        rec["calls"] = counted.calls
        if counted.drafter is not None:
            rec["draft_calls"] = counted.drafter.calls
        return rec

    requests = [make_request(rng) for _ in range(args.n)]
    if args.n_only:
        requests = requests[: args.n_only]
    shard, shards = (int(x) for x in args.shard.split("/"))
    todo = [(i, r) for i, r in enumerate(requests) if i % shards == shard]
    if args.ids:  # the blind rounds' 12 requests (2026-11-08), or a 3-request model probe
        keep = {int(x) for x in args.ids.split(",")}
        todo = [(i, r) for i, r in todo if i in keep]
        done = 0
    with (
        out.open("a", encoding="utf-8") as fh,
        ThreadPoolExecutor(max_workers=args.workers) as pool,
    ):
        for rec in pool.map(lambda ir: one(*ir), todo[done:]):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(rec["id"], rec.get("error", "ok"), rec["seconds"], flush=True)
    if args.price_in or args.price_out:
        print(f"spent ${generator.SPEND.today():.3f} (UTC day, this run)")


if __name__ == "__main__":
    main()

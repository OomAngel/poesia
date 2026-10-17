"""Which sense check separates good Spanish verse lines from bad ones? Measured, not assumed.

POETICS #4 ("every line makes sense") had no working instrument: the correct-and-compare check
rated generated lines above real broadside lines (judge_vs_corpus.py, 2026-10-14). This scores
candidate checks on a labelled set and reports how well each separates (ROC AUC, 0.5 = chance):

  good    real lines: Vanegas Arroyo broadside quatrains and ADSO Golden-Age sonnets
  broken  the same lines made senseless by construction: words shuffled, one content word swapped
          for a random frequent word, the halves of two different lines glued together
  flagged lines the engine wrote that were judged bad (only "sombrero muy inclina" is Angel's own
          label; the rest were picked by Claude from batches Angel rated bad)

Checks: (a) mean token log-probability of the line under Apertus 70B, given the poem's earlier
lines (CSCS /v1/completions with echo); (b) the same minus the words' own frequency (SLOR,
Lau et al. 2017: acceptability without the penalty for rare words); (c) a 1-5 judge prompt with
anchor examples; (d) the correct-and-compare check (baseline).

Usage (CSCS through the key proxy; data stay outside git):
  PYTHONPATH=src python scripts/quality/sense_instrument_eval.py CALAV_DATA ADSO_JSONL \\
      --url http://127.0.0.1:8790/v1 --model swiss-ai/Apertus-v1.5-70B [--n 100]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from poesia.quality import gates

FLAGGED = [  # (line, context, who flagged it)
    (
        "Con sombrero muy inclina!",
        "Llega a buscar a su gente!",
        "Angel 2026-10-09, note on b20261009-0025",
    ),
    ("Su teléfono siempre a cuánto.", "", "Claude, audit 2026-10-09"),
    ("Su chisme la lleva asia.", "", "Claude, audit 2026-10-09"),
    ("Pero su paso la inclina.", "", "Claude, audit 2026-10-09"),
    ("Mas el gato duerme en su sentido.", "", "Claude, audit 2026-10-09"),
    ("Y futbol siempre veré, haré.", "", "Claude, audit 2026-10-09"),
    (
        "Y en la sombra, esponja suave.",
        "Bajo el sol, Firulais se duerme,",
        "Claude, deploy test 2026-10-14",
    ),
    (
        "De eternos feed ni selfies.",
        "La eternidad no sabe de apps.",
        "Claude, smoke test 2026-10-09",
    ),
    ("Negro como su contenido,", "", "Claude, smoke test 2026-10-09"),
    ("Memo en playera brilla,", "Memo, con su playera en alto,", "Claude, smoke test 2026-10-09"),
    ("Golazo tan muy fin vivo.", "La Muerte se une al coro", "Claude, gpt-oss batch 2026-10-10"),
    (
        "Su prisa no pesa en balanza.",
        "Bebe en tazas su existencia,",
        "Claude, smoke test 2026-10-09",
    ),
]

JUDGE = (
    "Eres editor de poesía en español. Califica este verso del 1 al 5 por sentido y gramática: "
    "5 = español natural con sentido claro; 3 = se entiende pero forzado; 1 = sin sentido o "
    "agramatical. Ejemplos: «En el silencio de la noche» = 5; «Su teléfono siempre a cuánto» = 1; "
    "«Pero su paso la inclina» = 2.\n{ctx}Verso: {line}\nResponde solo con el número."
)
FIX = (
    "Correct any grammar, spelling, capitalisation or word-choice mistake in this line of a "
    "Spanish poem, changing as little as possible. If it is already correct, natural Spanish, "
    "repeat it exactly. Answer with the line only.\nLine: {line}"
)


def _post(url: str, path: str, body: dict) -> dict:
    req = urllib.request.Request(  # noqa: S310 - operator-given endpoint
        url.rstrip("/") + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        return json.load(resp)


def mean_logprob(url: str, model: str, line: str, ctx: str) -> float | None:
    """Mean log-probability of the line's tokens, given ``ctx`` (earlier lines) as prefix."""
    prefix = "Calaverita (poema mexicano en verso):\n" + (ctx + "\n" if ctx else "")
    try:
        d = _post(url, "/completions", {
            "model": model, "prompt": prefix + line, "max_tokens": 1, "echo": True,
            "logprobs": 1, "temperature": 0,
        })  # fmt: skip
    except Exception:  # noqa: BLE001
        return None
    lp = d["choices"][0]["logprobs"]
    offsets, values = lp["text_offset"], lp["token_logprobs"]
    picked = [
        v for o, v in zip(offsets, values, strict=False) if o >= len(prefix) and v is not None
    ]
    return sum(picked) / len(picked) if picked else None


@lru_cache(maxsize=1)
def _ranks() -> dict[str, int]:
    words = (gates.WORDLISTS / "es.txt").read_text(encoding="utf-8").split()
    return {w.lower(): i + 1 for i, w in enumerate(words)}


def unigram_logprob_per_word(line: str) -> float:
    """Zipf approximation from the frequency rank: log p ~ -log(rank) - log(H); unknown = rank 60k."""
    ranks = _ranks()
    ws = gates.words(line)
    if not ws:
        return 0.0
    h = math.log(60000) + 0.5772
    return sum(-math.log(ranks.get(w, 60000)) - math.log(h) for w in ws) / len(ws)


def judge_score(url: str, model: str, line: str, ctx: str) -> float | None:
    prompt = JUDGE.format(line=line, ctx=f"Verso anterior: {ctx}\n" if ctx else "")
    try:
        d = _post(url, "/chat/completions", {
            "model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": 5,
        })  # fmt: skip
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"[1-5]", d["choices"][0]["message"]["content"] or "")
    return float(m.group()) if m else None


def _fold(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^\w]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def unchanged(url: str, model: str, line: str) -> float | None:
    try:
        d = _post(url, "/chat/completions", {
            "model": model, "messages": [{"role": "user", "content": FIX.format(line=line)}],
            "temperature": 0, "max_tokens": 80,
        })  # fmt: skip
    except Exception:  # noqa: BLE001
        return None
    fixed = (d["choices"][0]["message"]["content"] or "").strip().strip('"„“«»')
    return 1.0 if _fold(fixed) == _fold(line) else 0.0


def auc(pos: list[float], neg: list[float]) -> float:
    """P(score of a good line > score of a bad one); ties count half."""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def build(calav: Path, adso: Path, n: int, rng: random.Random) -> list[dict]:
    good: list[tuple[str, str]] = []
    for row in (calav / "transcriptions" / "stanzas.jsonl").open(encoding="utf-8"):
        r = json.loads(row)
        lines = [x for x in r["lines"] if "[?" not in x]
        good += [(x, lines[i - 1] if i else "") for i, x in enumerate(lines)]
    broadside = rng.sample(good, min(n, len(good)))
    sonnet: list[tuple[str, str]] = []
    for row in adso.open(encoding="utf-8"):
        vs = [v for v in json.loads(row)["completion"].split("\n") if v.strip()]
        sonnet += [(x, vs[i - 1] if i else "") for i, x in enumerate(vs)]
    sonnets = rng.sample(sonnet, n)
    vocab = [w for w in list(_ranks())[300:6000] if w.isalpha() and len(w) >= 4]
    items = [dict(line=x, ctx=c, label="good", kind="broadside") for x, c in broadside]
    items += [dict(line=x, ctx=c, label="good", kind="sonnet") for x, c in sonnets]
    for x, c in broadside + sonnets:
        ws = x.split()
        kind = rng.choice(["shuffle", "swap", "glue"])
        if kind == "shuffle" and len(ws) > 2:
            bad = ws[:]
            while bad == ws:
                rng.shuffle(bad)
            text = " ".join(bad)
        elif kind == "swap" and len(ws) > 1:
            content = [i for i, w in enumerate(ws) if len(gates.words(w)) and len(w) >= 4]
            i = rng.choice(content or list(range(len(ws))))
            text = " ".join(ws[:i] + [rng.choice(vocab)] + ws[i + 1 :])
        else:
            other = rng.choice(good)[0].split()
            text = " ".join(ws[: max(1, len(ws) // 2)] + other[len(other) // 2 :])
            kind = "glue"
        items.append(dict(line=text, ctx=c, label="bad", kind=kind))
    items += [dict(line=x, ctx=c, label="flagged", kind=who) for x, c, who in FLAGGED]
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("calav", type=Path)
    ap.add_argument("adso", type=Path)
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--out", type=Path, help="per-line scores (JSONL; keep outside git)")
    args = ap.parse_args()
    items = build(args.calav, args.adso, args.n, random.Random(args.seed))  # noqa: S311

    def score(it: dict) -> dict:
        lp = mean_logprob(args.url, args.model, it["line"], it["ctx"])
        it["a_logprob"] = lp
        it["b_slor"] = None if lp is None else lp - unigram_logprob_per_word(it["line"]) / 2
        it["c_judge"] = judge_score(args.url, args.model, it["line"], it["ctx"])
        it["d_unchanged"] = unchanged(args.url, args.model, it["line"])
        return it

    with ThreadPoolExecutor(8) as pool:
        items = list(pool.map(score, items))
    if args.out:
        args.out.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items))
    good = [i for i in items if i["label"] == "good"]
    print(
        f"good {len(good)} | broken {sum(i['label'] == 'bad' for i in items)} | flagged {len(FLAGGED)}"
    )
    print(
        "| check | good vs broken (all) | vs shuffled | vs swapped word | vs glued halves | good vs flagged |"
    )
    print("|---|---|---|---|---|---|")
    for key in ("a_logprob", "b_slor", "c_judge", "d_unchanged"):
        pos = [i[key] for i in good if i[key] is not None]
        row = [
            f"{auc(pos, [i[key] for i in items if i['label'] == 'bad' and i[key] is not None]):.2f}"
        ]
        for kind in ("shuffle", "swap", "glue"):
            neg = [i[key] for i in items if i["kind"] == kind and i[key] is not None]
            row.append(f"{auc(pos, neg):.2f}")
        flagged = [i[key] for i in items if i["label"] == "flagged" and i[key] is not None]
        row.append(f"{auc(pos, flagged):.2f}")
        print(f"| {key} | " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()

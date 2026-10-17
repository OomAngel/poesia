"""Judge Calaveritas batches against the real broadsides, criterion by criterion (docs/POETICS.md).

POETICS: "the main judge is comparison with real poems ... Angel's blind rating on a small sample
last". Calaveritas requests are personal, so no real poem answers the same request; the
reference is the distribution of the transcribed Vanegas Arroyo broadside quatrains (git-ignored
``transcriptions/stanzas.jsonl``), read in 3-stanza windows like a generated poem. Per batch:

- #1 form: Spanish lines at exactly 8 (today's counter), 8-8-8-8 stanzas, lines 2/4 rhyming
- #2 rhyme pairs on near-copies (``poesia.quality.gates.near_copies``)
- #3 poems repeating a content word, repeats per poem (name and genre words may repeat)
- #4 sense: share of lines a strong model leaves unchanged when asked to correct them (the
  engine's correct-and-compare check, scripts/distill_line_data.py; case and accents ignored so
  the broadsides' old spelling, "fué", "á", is not counted as a mistake)
- #4 gist: a 1-5 judge of the whole poem's story (one storyline, the habit as the joke, a
  punchline on it); the broadsides are read in the same 3-stanza windows
- #11 drift: distinct openings per line, share of lines on the ten commonest end words

Usage (CSCS through the key proxy):
  PYTHONPATH=src python scripts/calaveritas_data/judge_vs_corpus.py DATA_DIR BATCH.jsonl [...] \\
      --url http://127.0.0.1:8790/v1 --model swiss-ai/Apertus-v1.5-70B
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from poesia.calaveritas.rhymebank import GENRE_WORDS
from poesia.phonology.spanish import SpanishPhonology
from poesia.quality import gates

JUDGE_PROMPT = (
    "Eres editor de poesía en español. Califica este verso del 1 al 5 por sentido y gramática: "
    "5 = español natural con sentido claro; 3 = se entiende pero forzado; 1 = sin sentido o "
    "agramatical. Ejemplos: «En el silencio de la noche» = 5; «Su teléfono siempre a cuánto» = 1; "
    "«Pero su paso la inclina» = 2.\nVerso: {line}\nResponde solo con el número."
)
FIX_PROMPT = (
    "Correct any grammar, spelling, capitalisation or word-choice mistake in this line of a "
    "Spanish poem, changing as little as possible. If it is already correct, natural Spanish, "
    "repeat it exactly. Answer with the line only.\nLine: {line}"
)
GIST_PROMPT = (
    "Eres editor de calaveritas literarias mexicanas. Califica esta calaverita del 1 al 5 por su "
    "historia: 5 = cuenta una sola historia que se entiende de principio a fin, la costumbre de la "
    "persona es el chiste y el final remata con gracia sobre ella; 3 = hay historia pero floja o el "
    "remate no pega; 1 = versos sueltos sin historia ni remate. No califiques la métrica.\n\n"
    "{poem}\n\nResponde solo con el número."
)
ES = SpanishPhonology()


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]+", " ", t).strip()


def unchanged(line: str, url: str, model: str) -> bool | None:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": FIX_PROMPT.format(line=line)}],
        "temperature": 0,
        "max_tokens": 80,
    }
    req = urllib.request.Request(  # noqa: S310 - operator-given endpoint
        url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            fixed = json.load(resp)["choices"][0]["message"]["content"].strip().strip('"„“«»')
    except Exception:  # noqa: BLE001 - an unanswered line is left out, not counted either way
        return None
    return _fold(fixed) == _fold(line)


def judged(line: str, url: str, model: str) -> float | None:
    """1-5 by a judge prompt with anchors (sense_instrument_eval.py: picks the real line over a
    broken copy 76% of the time). Independent of the log-probability the engine now selects by."""
    body = {
        "model": model,
        "messages": [{"role": "user", "content": JUDGE_PROMPT.format(line=line)}],
        "temperature": 0,
        "max_tokens": 5,
    }
    req = urllib.request.Request(  # noqa: S310 - operator-given endpoint
        url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            text = json.load(resp)["choices"][0]["message"]["content"] or ""
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"[1-5]", text)
    return float(m.group()) if m else None


def gist(poem: list[list[str]], url: str, model: str) -> float | None:
    """1-5 for the whole poem's story (one storyline, the habit as the joke, a punchline on it): the
    gist Angel found missing (2026-10-09, 2026-10-15); the line judge cannot see it."""
    text = "\n\n".join("\n".join(st) for st in poem)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": GIST_PROMPT.format(poem=text)}],
        "temperature": 0,
        "max_tokens": 5,
    }
    req = urllib.request.Request(  # noqa: S310 - operator-given endpoint
        url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            m = re.search(r"[1-5]", json.load(resp)["choices"][0]["message"]["content"] or "")
    except Exception:  # noqa: BLE001
        return None
    return float(m.group()) if m else None


def classic_poems(data: Path) -> list[tuple[list[list[str]], frozenset[str]]]:
    sheets: dict[str, list[list[str]]] = defaultdict(list)
    for row in (data / "transcriptions" / "stanzas.jsonl").open(encoding="utf-8"):
        r = json.loads(row)
        if r["stanza_form"] == "quatrain" and not any("[?" in x for x in r["lines"]):
            sheets[r["item_id"]].append(r["lines"])
    return [(sts[i : i + 3], frozenset()) for sts in sheets.values() for i in range(0, len(sts), 3)]


def batch_poems(path: Path) -> tuple[list[tuple[list[list[str]], frozenset[str]]], int, int]:
    poems, total, failed = [], 0, 0
    for row in path.open(encoding="utf-8"):
        r = json.loads(row)
        if r["request"]["language"] != "es":
            continue
        total += 1
        if "poem" not in r:
            failed += 1
            continue
        name = frozenset(w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]+", r["request"]["name"]))
        poems.append(([s["lines"] for s in r["poem"]["stanzas"]], name))
    return poems, total, failed


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "-"


def measure(poems, url: str, model: str) -> dict[str, str]:
    lines = [x for stanzas, _ in poems for st in stanzas for x in st]
    stanzas = [st for s, _ in poems for st in s if len(st) == 4]
    counts = [ES.scan_line(x).metrical_syllable_count for x in lines]
    eight_st = sum(all(ES.scan_line(x).metrical_syllable_count == 8 for x in st) for st in stanzas)

    def rhymes(a: str, b: str) -> bool:
        return gates.rhyme(b, a, ES, loose=True) is None

    rhyme24 = sum(rhymes(st[1], st[3]) for st in stanzas)
    pairs = [(st[1], st[3]) for st in stanzas if rhymes(st[1], st[3])]
    pairs += [(st[0], st[2]) for st in stanzas if rhymes(st[0], st[2])]
    near = sum(gates.near_copies(gates.end_word(a), gates.end_word(b)) for a, b in pairs)
    with_rep = reps = 0
    for s, name in poems:
        flat = [x for st in s for x in st]
        allowed = name | GENRE_WORDS["es"]
        found = [
            w
            for i, x in enumerate(flat)
            for w in gates.repeated_words(x, tuple(flat[:i]), "es", allowed)
        ]
        with_rep += bool(found)
        reps += len(found)
    with ThreadPoolExecutor(8) as pool:
        verdicts = [v for v in pool.map(lambda x: unchanged(x, url, model), lines) if v is not None]
        grades = [g for g in pool.map(lambda x: judged(x, url, model), lines) if g is not None]
        gists = [g for g in pool.map(lambda p: gist(p[0], url, model), poems) if g is not None]
    opens = Counter(gates.opening(x) for x in lines)
    ends = Counter(gates.end_word(x) for x in lines)
    n = len(lines)
    return {
        "poems / lines": f"{len(poems)} / {n}",
        "#1 lines at exactly 8": _pct(sum(c == 8 for c in counts), n),
        "#1 stanzas 8-8-8-8": _pct(eight_st, len(stanzas)),
        "#1 stanzas rhyming lines 2 and 4": _pct(rhyme24, len(stanzas)),
        "#2 rhyme pairs on near-copies": _pct(near, len(pairs)),
        "#3 poems repeating a content word": _pct(with_rep, len(poems)),
        "#3 repeats per poem": f"{reps / len(poems):.2f}" if poems else "-",
        "#4 lines a corrector leaves unchanged": _pct(sum(verdicts), len(verdicts)),
        "#4 judge 1-5, mean": f"{sum(grades) / len(grades):.2f}" if grades else "-",
        "#4 judge: lines graded 1-2": _pct(sum(g <= 2 for g in grades), len(grades)),
        "#4 gist: poem judge 1-5, mean": f"{sum(gists) / len(gists):.2f}" if gists else "-",
        "#4 gist: poems graded 4-5": _pct(sum(g >= 4 for g in gists), len(gists)),
        "#11 distinct openings per line": f"{len(opens) / n:.2f}" if n else "-",
        "#11 lines on the 10 commonest endings": _pct(sum(c for _, c in ends.most_common(10)), n),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data", type=Path, help="seeds/poetry_corpus/external/calaveritas")
    ap.add_argument("batches", nargs="+", type=Path)
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    args = ap.parse_args()
    cols = [("classic broadsides", measure(classic_poems(args.data), args.url, args.model))]
    for b in args.batches:
        poems, total, failed = batch_poems(b)
        m = measure(poems, args.url, args.model)
        m["Spanish requests failed"] = _pct(failed, total)
        cols.append((b.stem, m))
    keys = list(dict.fromkeys(k for _, m in cols for k in m))
    print("| POETICS criterion | " + " | ".join(name for name, _ in cols) + " |")
    print("|---" * (len(cols) + 1) + "|")
    for k in keys:
        print(f"| {k} | " + " | ".join(m.get(k, "-") for _, m in cols) + " |")


if __name__ == "__main__":
    main()

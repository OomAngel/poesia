#!/usr/bin/env python3
"""Line training data for Apertus from real poems, in the exact request shape the page sends.

``build_fixed_dataset.py`` (July) had the right idea: cut poems into one example per line with
the loop's line prompt. Its prompt text has since drifted from the page's (language rule, word
bank, five languages), so this builder does not rewrite the prompt by hand: it calls the page's
own ``CandidateGenerator`` with a recording stand-in model and keeps the request it would send.

Per line of a poem: "Exactly N syllables" with N the line's count by the engine; when an earlier
line of the stanza (up to four back) rhymes with it, the rhyme instruction naming that word and
the same offline word bank the page offers (``fetch_rhyme_words``; Datamuse switched off as on
the offline page). The answer is the poet's own line, often not a bank word: the line adapter
trained on one teacher's lines (2026-10-09) forced bank words in and collapsed to ~20 openings.
Poems are chosen to resemble the page's forms: 8 or more lines, at least half of them with a
rhyme partner, and one metrical length for at least half of them; the first 14 lines are used.

Sources: corpus_master (es, en; Angel, 2026-10-10: any poem may go to the private training
set), Biblioteca Italiana (it), DLK (de), Métrique en Ligne (fr).

    python scripts/build_apertus_line_data.py --per-language 160 --out data/distill/apertus-lines-corpus.jsonl
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import random
import re
from pathlib import Path

from poesia.generation import rhyme_fetcher
from poesia.generation.candidate_generator import CandidateGenerator
from poesia.generation.llm_client import LINE_SYSTEM_PROMPT, is_line_prompt
from poesia.phonology.rhyme_index import phonology
from poesia.webapp import guess_language

MASTER = Path("seeds/poetry_corpus/corpus_master/poems.jsonl")
ITALIAN = "data/external/averell/biblioteca_italiana-master/json/*.json"
FRENCH = "data/external/averell/metrique-en-ligne-master/json/*.json"
GERMAN = "data/external/DLK/DLK/meterized/json_DLK_v6/*.json"
MAX_LINES = 14
MAX_REPEATED = 2  # content words used twice or more in the first 14 lines (POETICS #3)
OPENING_CAP, ENDING_CAP = 0.05, 0.02  # shares across the whole set, not per poem
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _end(line: str) -> str:
    w = WORD.findall(line.lower())
    return w[-1] if w else ""


def _near_copy(a: str, b: str) -> bool:
    """Same word, or one ends with the other ("venir"/"prevenir"): not a rhyme (POETICS #2)."""
    return a == b or (min(len(a), len(b)) >= 3 and (a.endswith(b) or b.endswith(a)))


def _repeated_content_words(lines: list[str], language: str) -> int:
    from poesia.phonology.rhyme_index import rank

    small = {w.lower() for w, r in rank(language).items() if r < 150}
    words = [w for ln in lines for w in WORD.findall(ln.lower()) if w not in small and len(w) > 2]
    return sum(c > 1 for c in collections.Counter(words).values())


def _influence_names() -> list[str]:
    import yaml

    data = yaml.safe_load(Path("data/influences.yaml").read_text(encoding="utf-8"))
    return [p["name"] for p in data.get("spanish", [])]


class _Recorder:
    """Stands in for the model: keeps the prompt, answers nothing."""

    def __init__(self) -> None:
        self.prompt = ""

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        self.prompt = prompt
        return []


def _averell(pattern: str, language: str):
    for path in sorted(glob.glob(pattern)):
        for poem in json.loads(Path(path).read_text(encoding="utf-8")):
            stanzas = [
                [v["verse"] for v in st if v.get("verse", "").strip()]
                for st in poem.get("text", [])
            ]
            yield {
                "language": language,
                "title": str(poem.get("title", "")),
                "author": poem.get("author", ""),
                "stanzas": [s for s in stanzas if s],
            }


def _dlk(sample: int, rng: random.Random):
    files = sorted(glob.glob(GERMAN))
    for path in rng.sample(files, min(sample, len(files))):
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        for poem in doc.values():
            stanzas = [
                [ln["text"] for ln in st.values() if ln.get("text", "").strip()]
                for st in poem.get("poem", {}).values()
            ]
            yield {
                "language": "de",
                "title": poem["metadata"].get("title", ""),
                "author": poem["metadata"].get("author", {}).get("name", ""),
                "stanzas": [s for s in stanzas if s],
            }


def _master(language: str):
    with MASTER.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("language") != language:
                continue
            text = r.get("completion", "")
            stanzas = [
                [ln.strip() for ln in block.split("\n") if ln.strip()]
                for block in text.split("\n\n")
            ]
            yield {
                "language": language,
                "title": r.get("title", ""),
                "author": r.get("author", ""),
                "source": r.get("source", ""),
                "stanzas": [s for s in stanzas if s],
            }


def _plan(poem: dict) -> list[tuple[str, int, int | None]] | None:
    """(line, syllables, partner index) for the first MAX_LINES lines, or None if the poem does
    not look like rhymed metrical verse."""
    phon = phonology(poem["language"])
    flat, stanza_start = [], []
    for st in poem["stanzas"]:
        start = len(flat)
        for ln in st:
            flat.append(ln)
            stanza_start.append(start)
    flat, stanza_start = flat[:MAX_LINES], stanza_start[:MAX_LINES]
    if len(flat) < 8:
        return None
    keys = [phon.rhyme_key(ln).consonant for ln in flat]
    counts = [phon.scan_line(ln).metrical_syllable_count for ln in flat]
    plan, rhymed = [], 0
    for i, ln in enumerate(flat):
        partner = next(
            (
                j
                for j in range(i - 1, max(stanza_start[i], i - 4) - 1, -1)
                if keys[i] and keys[j] == keys[i] and not _near_copy(_end(flat[j]), _end(ln))
            ),
            None,
        )
        rhymed += partner is not None
        plan.append((ln, counts[i], partner))
    modal = collections.Counter(counts).most_common(1)[0][1]
    if rhymed < len(flat) / 2 or modal < len(flat) / 2:
        return None
    if _repeated_content_words(flat, poem["language"]) > MAX_REPEATED:
        return None
    return plan


def _examples(poem: dict) -> list[dict]:
    plan = _plan(poem)
    if plan is None:
        return []
    lang = poem["language"]
    title = poem["title"].strip()
    theme = title if 3 <= len(title) <= 60 and not title.strip(". ").isdigit() else plan[0][0]
    rec = _Recorder()
    gen = CandidateGenerator(rec)
    lines = [p[0] for p in plan]
    out = []
    for i, (line, syllables, partner) in enumerate(plan):
        if len(line.split()) < 3 or guess_language(line) not in (None, lang):
            continue
        word = key = None
        bank: list[str] = []
        if partner is not None:
            word = lines[partner].split()[-1].strip(".,;:!?¡¿«»\"'()")
            key = phonology(lang).rhyme_key(lines[partner]).consonant
            bank = rhyme_fetcher.fetch_rhyme_words(word, language=lang)
        gen.generate_lines(
            theme=theme,
            language=lang,
            n_candidates=1,
            prior_lines=lines[:i],
            target_syllables=syllables,
            target_rhyme_key=key,
            example_rhyme_word=word,
            rhyme_candidates=bank,
        )
        messages = [{"role": "user", "content": rec.prompt}, {"role": "assistant", "content": line}]
        if is_line_prompt(rec.prompt):
            messages.insert(0, {"role": "system", "content": LINE_SYSTEM_PROMPT})
        out.append(
            {
                "messages": messages,
                "language": lang,
                "kind": "corpus",
                "author": poem["author"],
                "title": title,
                "line_index": i,
                "rhymed": partner is not None,
                "shape": "pair" if partner is not None else "line",
            }
        )
    return out


def _benchmark_themes() -> dict[str, set[str]]:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "bench", Path(__file__).with_name("evaluate_adapter_mlflow.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {k: {t.lower() for t in v} for k, v in mod.THEMES.items()}


def _ordered(
    lang: str, poems: list[dict], rng: random.Random, influence_share: float
) -> list[dict]:
    """Spanish: interleave Angel's poets (data/influences.yaml, POETICS #7) at ``influence_share``."""
    if lang != "es" or influence_share <= 0:
        return poems
    names = [n.split()[-1].lower() for n in _influence_names()]
    theirs = [p for p in poems if any(n in str(p["author"]).lower() for n in names)]
    # Outside Angel's poets, leave the Golden Age collections out: their inverted word order
    # contradicts the prompt's "normal word order" rule (POETICS #4), so the pair would teach the
    # model to ignore it. Sor Juana stays (she is one of his poets).
    golden = re.compile(r"siglo_de_oro|stuniga|garcilaso", re.I)
    rest = [p for p in poems if p not in theirs and not golden.search(str(p.get("source", "")))]
    out, k = [], 0
    while theirs or rest:
        take_theirs = theirs and (not rest or rng.random() < influence_share)
        out.append(theirs.pop() if take_theirs else rest.pop())
        k += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--per-language", type=int, default=160, help="poems per language")
    ap.add_argument("--languages", nargs="+", default=["es", "en", "it", "de", "fr"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--influence-share", type=float, default=0.5, help="Spanish: share from Angel's poets"
    )
    ap.add_argument(
        "--holdout-per-language", type=int, default=50, help="poems kept out for the judge"
    )
    ap.add_argument("--out", required=True)
    ap.add_argument("--holdout-out", default=None)
    args = ap.parse_args()
    rhyme_fetcher._fetch_datamuse = lambda *_a, **_k: []  # the offline page never reaches Datamuse
    rng = random.Random(args.seed)
    themes = _benchmark_themes()
    sources = {
        "es": lambda: _master("es"),
        "en": lambda: _master("en"),
        "it": lambda: _averell(ITALIAN, "it"),
        "fr": lambda: _averell(FRENCH, "fr"),
        "de": lambda: _dlk(6000, rng),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    hold = (
        Path(args.holdout_out) if args.holdout_out else out.with_name(out.stem + "-holdout.jsonl")
    )
    totals = {}
    with out.open("w", encoding="utf-8") as fh, hold.open("w", encoding="utf-8") as hh:
        for lang in args.languages:
            poems = list(sources[lang]())
            rng.shuffle(poems)
            poems = [p for p in poems if p["title"].strip().lower() not in themes.get(lang, set())]
            poems = _ordered(lang, poems, rng, args.influence_share)
            openings, endings = collections.Counter(), collections.Counter()
            kept = held = n = capped = 0
            for poem in poems:
                ex = _examples(poem)
                if not ex:
                    continue
                if held < args.holdout_per_language:  # whole poems, never trained on
                    hh.write(
                        json.dumps(
                            {
                                "language": lang,
                                "author": poem["author"],
                                "title": poem["title"],
                                "lines": [e["messages"][-1]["content"] for e in ex],
                                "examples": ex,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    held += 1
                    continue
                for e in ex:
                    line = e["messages"][-1]["content"]
                    words = WORD.findall(line.lower())
                    first, last = (words[0], words[-1]) if words else ("", "")
                    total = max(n, 50)
                    if (
                        openings[first] + 1 > OPENING_CAP * total
                        or endings[last] + 1 > ENDING_CAP * total
                    ):
                        capped += 1
                        continue
                    openings[first] += 1
                    endings[last] += 1
                    fh.write(json.dumps(e, ensure_ascii=False) + "\n")
                    n += 1
                kept += 1
                if kept >= args.per_language:
                    break
            totals[lang] = {
                "poems": kept,
                "examples": n,
                "capped": capped,
                "holdout": held,
                "pool": len(poems),
            }
            print(lang, totals[lang], flush=True)
    print(json.dumps(totals))


if __name__ == "__main__":
    main()

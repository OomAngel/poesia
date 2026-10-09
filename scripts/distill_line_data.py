#!/usr/bin/env python3
"""Line-level training data from a teacher model, kept only where the engine accepts it.

The teacher (Apertus v1.5 70B on CSCS) writes sonnets through the same ``ConstrainedLoop`` the
page uses for its proposals. Every request is recorded; a line becomes a training example only
when it is in the finished poem and the engine accepts it: exact metre, the rhyme of its group
(not the partner's own word), the poem's language, three words or more. The example is that
line's exact request (the one-line system message and the user prompt, or a repair prompt)
with the line as the answer, so training sees the shapes the page sends (a line must also come
back unchanged when the teacher is asked to correct it, and no opening word may start more than
two kept lines of a poem); the July adapters,
trained on whole poems, failed on line and repair prompts they had never seen
(docs/GENERATION_QUALITY_PLAN.md). The benchmark's themes are left out.

    LLM_BASE_URL=http://127.0.0.1:8790/v1 LLM_NAME=swiss-ai/Apertus-v1.5-70B LLM_API_KEY=x \\
        python scripts/distill_line_data.py --languages es it de fr --seeds 0 1 \\
        --out data/distill/lines-70b-2026-10-09.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from poesia.generation.llm_client import LINE_SYSTEM_PROMPT, is_line_prompt
from poesia.generation.registry import get_llm

FORMS = {
    "es": "soneto",
    "it": "sonetto",
    "de": "sonett",
    "fr": "sonnet",
    "en": "sonnet_shakespearean",
}
# Not the benchmark's (luna/mar/tiempo/noche/soledad/memoria and their translations).
THEMES = {
    "es": [
        "la lluvia",
        "un jardín",
        "la infancia",
        "el otoño",
        "la amistad",
        "un viaje",
        "el silencio",
        "la ciudad",
        "el invierno",
        "una carta",
        "la madre",
        "el río",
        "la esperanza",
        "el pan",
        "una ventana",
        "el bosque",
        "la despedida",
        "el fuego",
        "la música",
        "un puerto",
    ],
    "it": [
        "la pioggia",
        "un giardino",
        "l'infanzia",
        "l'autunno",
        "l'amicizia",
        "un viaggio",
        "il silenzio",
        "la città",
        "l'inverno",
        "una lettera",
        "la madre",
        "il fiume",
        "la speranza",
        "il pane",
        "una finestra",
        "il bosco",
        "l'addio",
        "il fuoco",
        "la musica",
        "un porto",
    ],
    "de": [
        "der Regen",
        "ein Garten",
        "die Kindheit",
        "der Herbst",
        "die Freundschaft",
        "eine Reise",
        "die Stille",
        "die Stadt",
        "der Winter",
        "ein Brief",
        "die Mutter",
        "der Fluss",
        "die Hoffnung",
        "das Brot",
        "ein Fenster",
        "der Wald",
        "der Abschied",
        "das Feuer",
        "die Musik",
        "ein Hafen",
    ],
    "fr": [
        "la pluie",
        "un jardin",
        "l'enfance",
        "l'automne",
        "l'amitié",
        "un voyage",
        "le silence",
        "la ville",
        "l'hiver",
        "une lettre",
        "la mère",
        "la rivière",
        "l'espoir",
        "le pain",
        "une fenêtre",
        "la forêt",
        "l'adieu",
        "le feu",
        "la musique",
        "un port",
    ],
    "en": [
        "the rain",
        "a garden",
        "childhood",
        "autumn",
        "friendship",
        "a journey",
        "silence",
        "the city",
        "winter",
        "a letter",
        "mother",
        "the river",
        "hope",
        "bread",
        "a window",
        "the forest",
        "farewell",
        "fire",
        "music",
        "a harbour",
    ],
}


LANGUAGE_NAMES = {"es": "Spanish", "it": "Italian", "de": "German", "fr": "French", "en": "English"}
# The engine checks metre, rhyme and language, not grammar or sense: the teacher's German lines
# passed it with "der weite Meer" and "schenkt der Himmel geben". A yes/no question let half of
# such errors through; asking for the corrected line and keeping only lines it leaves unchanged
# caught all five in a 13-line test and kept the two correct controls (2026-10-09).
FIX_PROMPT = (
    "Correct any grammar, spelling, capitalisation or word-choice mistake in this line of a {lang} "
    "poem, changing as little as possible. If it is already correct, natural {lang}, repeat it "
    "exactly. Answer with the line only.\nLine: {line}"
)


def _unchanged_by_correction(language: str, line: str) -> bool:
    body = {
        "model": os.environ["LLM_NAME"],
        "messages": [
            {"role": "user", "content": FIX_PROMPT.format(lang=LANGUAGE_NAMES[language], line=line)}
        ],
        "temperature": 0,
        "max_tokens": 80,
    }
    req = urllib.request.Request(
        os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LLM_API_KEY', 'x')}",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        fixed = json.load(resp)["choices"][0]["message"]["content"].strip().strip('"„“«»')

    def norm(t: str) -> str:
        return re.sub(r"[^\w]+", " ", t).strip()

    return norm(fixed) == norm(line)


class RecordingLLM:
    """Passes requests to the teacher and keeps each (prompt, answers) pair."""

    def __init__(self, inner):
        self.inner = inner
        self.calls: list[tuple[str, list[str]]] = []
        self._lock = threading.Lock()

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        out = self.inner.generate(prompt, n=n, temperature=temperature)
        with self._lock:
            self.calls.append((prompt, list(out)))
        return out

    def __getattr__(self, name):  # anything else the loop asks for (model name, repair)
        return getattr(self.inner, name)


def _accepted(language: str, form: str, lines: list[str], i: int) -> bool:
    from poesia.webapp import scan_line

    line = lines[i]
    if len(line.split()) < 3:
        return False
    r = scan_line(line, language, form, i, lines[: i + 1])
    if r["status"] != "ok" or r["other_language"] is not None or r["rhymes"] is False:
        return False
    partner = r["rhyme_partner"]
    if partner is not None and lines[partner].split():
        same = lines[partner].split()[-1].strip(".,;:!?¡¿«»\"'").lower()
        if line.split()[-1].strip(".,;:!?¡¿«»\"'").lower() == same:
            return False
    return True


def _one_poem(language: str, theme: str, seed: int) -> list[dict]:
    import random

    from poesia.generation.constrained_loop import ConstrainedLoop

    random.seed(seed)
    llm = RecordingLLM(get_llm("openai_compat"))
    loop = ConstrainedLoop(language=language, form=FORMS[language], llm=llm)
    result = loop.run(theme=theme, n_candidates=8, max_repair_attempts=4)
    examples = []
    openings: dict[str, int] = {}
    for i, line in enumerate(result.lines):
        if not _accepted(language, FORMS[language], result.lines, i):
            continue
        first = line.split()[0].lower().strip(".,;:!?¡¿«»\"'")
        if openings.get(first, 0) >= 2:
            continue  # ten of thirteen teacher lines began "Durch" or "Im": keep openings varied
        if not _unchanged_by_correction(language, line):
            continue
        openings[first] = openings.get(first, 0) + 1
        source = next(
            (p for p, outs in llm.calls if any(o.strip() == line.strip() for o in outs)), None
        )
        if source is None:
            continue
        messages = [
            {"role": "user", "content": source},
            {"role": "assistant", "content": line.strip()},
        ]
        if is_line_prompt(source):
            messages.insert(0, {"role": "system", "content": LINE_SYSTEM_PROMPT})
        kind = "repair" if "Fix this poetic line" in source else "write"
        examples.append(
            {
                "messages": messages,
                "language": language,
                "theme": theme,
                "seed": seed,
                "line_index": i,
                "kind": kind,
            }
        )
    return examples


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--languages", nargs="+", default=["es", "it", "de", "fr"], choices=sorted(FORMS)
    )
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--themes-per-language", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    tasks = [
        (lang, theme, seed)
        for lang in args.languages
        for theme in THEMES[lang][: args.themes_per_language]
        for seed in args.seeds
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, str]] = set()
    kept = poems = 0
    with out.open("w", encoding="utf-8") as fh, ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(_one_poem, *t): t for t in tasks}
        for fut in as_completed(futures):
            lang, theme, seed = futures[fut]
            try:
                examples = fut.result()
            except Exception as exc:  # one failed poem must not stop the batch
                print(
                    f"[{lang}] {theme} seed {seed}: failed ({type(exc).__name__}: {exc})",
                    flush=True,
                )
                continue
            poems += 1
            for ex in examples:
                key = (ex["messages"][-2]["content"], ex["messages"][-1]["content"])
                if key in seen:
                    continue
                seen.add(key)
                fh.write(json.dumps(ex, ensure_ascii=False) + "\n")
                kept += 1
            fh.flush()
            print(
                f"[{lang}] {theme} seed {seed}: {len(examples)} lines kept; total {kept} from {poems} poems",
                flush=True,
            )
    print(f"done: {kept} examples from {poems} of {len(tasks)} poems")


if __name__ == "__main__":
    main()

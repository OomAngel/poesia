"""Build the runtime few-shot file for the Calaveritas generator from the transcribed broadsides.

Input: seeds/poetry_corpus/external/calaveritas/transcriptions/stanzas.jsonl (git-ignored, public-domain
unsigned Vanegas Arroyo sheets). Output: the same folder's fewshot.json, {"es": {tone: [stanza, ...]}}.
Kept: unsigned, high or medium legibility, quatrains whose four lines count 8 and rhyme ABAB, ABBA or
abcb; every one goes to its primary and secondary tone (2026-10-09: all of them, not 4 per tone, so
each prompt can sample 3 from a real pool). Escolar gets its own stanzas plus any Cariñosa stanza
that passes the Escolar word list and the hand-read exclusions below. The file is mounted read-only
into the container at run time; poems are never baked into images or committed (AGENTS.md).

Usage: python -I scripts/calaveritas_data/build_fewshot.py <calaveritas data folder>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from poesia.calaveritas.guard import ESCOLAR_EXTRA, _hits  # noqa: E402

# Read by hand 2026-10-09. Never shown: a suicide ("puso á su vida fin"; the guard bans self-harm)
# and maids mocked as "gatas" (a class slur the app must not teach).
NEVER = {"lacipi:LCMaderista.djvu:04", "lacipi:RDCalaveras.djvu:01"}
# Not for children: a caress at school, a bullfighter's kill.
NOT_ESCOLAR = {"lacipi:LCMaderista.djvu:07", "loc:99615913/04575:02"}
TONES = {
    "Cariñosa": "carinosa",
    "Pícara": "picara",
    "Política": "politica",
    "Escolar": "escolar",
    "Clásica": "clasica",
}


def main(folder: Path) -> None:
    rows = [json.loads(line) for line in (folder / "transcriptions" / "stanzas.jsonl").open()]
    out: dict[str, dict[str, list[dict]]] = {"es": {t: [] for t in TONES.values()}}
    for r in rows:
        if (
            r["stanza_id"] in NEVER
            or r.get("signed")
            or r.get("legibility") not in {"high", "medium"}
            or r.get("stanza_form") != "quatrain"
        ):
            continue
        if r.get("syllables") != [8, 8, 8, 8] or r.get("rhyme_scheme", "").upper() not in {
            "ABAB",
            "ABBA",
            "ABCB",
        }:
            continue
        tones = {
            TONES.get((label or "").split(" ")[0])
            for label in (r.get("tone"), r.get("tone_secondary"))
        }
        if "carinosa" in tones:
            tones.add("escolar")
        for tone in tones - {None}:
            if tone == "escolar" and (
                r["stanza_id"] in NOT_ESCOLAR or _hits("\n".join(r["lines"]), ESCOLAR_EXTRA)
            ):
                continue
            out["es"][tone].append(
                {
                    "id": r["stanza_id"],
                    "title": r["title"],
                    "year": r.get("year"),
                    "lines": r["lines"],
                }
            )
    target = folder / "transcriptions" / "fewshot.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(target, {t: len(v) for t, v in out["es"].items()})


if __name__ == "__main__":
    main(Path(sys.argv[1]))

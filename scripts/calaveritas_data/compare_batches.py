"""Compare review batches with the counts of the quality audit (2026-10-09).

Each batch is a git-ignored JSONL from generate_batch.py; the same seed gives the same 200 requests, so
the batches differ only in the engine. Counts (docs/research/research_notes/calaveritas_quality_audit_2026-10-09.md
section 2): failures, rhyme-closing lines on a family's six commonest words, end-word concentration,
endings tacked on after a comma, stanzas opening on a Death epithet, phone words with and without the
phone chip or a messages detail, trait or detail text pasted verbatim, and metre. These are defect
counts, not a quality score: the blind rating decides.

Usage: PYTHONPATH=src python scripts/calaveritas_data/compare_batches.py OLD.jsonl NEW.jsonl [...] [--recount]
(--recount re-scans every Spanish line with today's counter, so batches written by different
counters are compared with one instrument.)
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

from poesia.calaveritas import quality
from poesia.calaveritas.options import TRAITS
from poesia.calaveritas.rhymebank import common

PHONE = re.compile(
    r"\b(celular|m[óo]vil|tel[ée]fono|pantalla|mensajes?|selfies?|likes?|apps?|whatsapp|"
    r"phone|screen|texts?|messages?)\b",
    re.I,
)


def _end(line: str) -> str:
    words = re.findall(r"[A-Za-zÀ-ÿ'’]+", line)
    return words[-1].lower() if words else ""


def _msg(q: dict) -> bool:
    return "mensaje" in q["detail"] or "message" in q["detail"]


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "0/0"


def measure(path: Path) -> dict[str, str]:
    rows = [json.loads(x) for x in path.open(encoding="utf-8")]
    ok = [r for r in rows if "poem" in r]
    es = [r for r in ok if r["request"]["language"] == "es"]
    out: dict[str, str] = {}
    for lang in ("es", "en"):
        n = sum(r["request"]["language"] == lang for r in rows)
        bad = sum(r["request"]["language"] == lang and "poem" not in r for r in rows)
        out[f"failed ({lang})"] = _pct(bad, n)
    closing = [st["lines"][3] for r in es for st in r["poem"]["stanzas"]]
    out["line 4 on a family's 6 commonest words (es)"] = _pct(
        sum(_end(x) in common(_end(x), "es") for x in closing), len(closing)
    )
    lines = [x for r in es for st in r["poem"]["stanzas"] for x in st["lines"]]
    ends = Counter(_end(x) for x in lines)
    top10 = sum(c for _, c in ends.most_common(10))
    out["lines on the 10 commonest end words (es)"] = _pct(top10, len(lines))
    out["distinct end words / lines (es)"] = f"{len(ends)}/{len(lines)}"
    out["commonest endings (es)"] = ", ".join(f"{w} {c}" for w, c in ends.most_common(8))
    all_lines = [
        (r["request"]["language"], x)
        for r in ok
        for st in r["poem"]["stanzas"]
        for x in st["lines"]
    ]
    out["endings tacked on after a comma"] = _pct(
        sum(quality.tacked_on(x) for _, x in all_lines), len(all_lines)
    )
    stanzas = [
        (r["request"]["language"], i, st) for r in ok for i, st in enumerate(r["poem"]["stanzas"])
    ]
    out["stanzas opening on a Death epithet"] = _pct(
        sum(quality.death_opening(st["lines"][0], lg) for lg, _, st in stanzas), len(stanzas)
    )
    later = [(lg, st) for lg, i, st in stanzas if i > 0]
    out["... of stanzas 2+"] = _pct(
        sum(quality.death_opening(st["lines"][0], lg) for lg, st in later), len(later)
    )
    out["lines with a calaverita cliché"] = _pct(
        sum(quality.cliches(x, lg) > 0 for lg, x in all_lines), len(all_lines)
    )
    for label, sel in (
        ("phone chip", lambda q: "celular" in q["traits"]),
        ("messages detail, no chip", lambda q: "celular" not in q["traits"] and _msg(q)),
        ("neither", lambda q: "celular" not in q["traits"] and not _msg(q)),
    ):
        grp = [r for r in ok if sel(r["request"])]
        hit = sum(
            any(PHONE.search(x) for st in r["poem"]["stanzas"] for x in st["lines"]) for r in grp
        )
        out[f"poems with phone words: {label}"] = _pct(hit, len(grp))
    chip = [st for r in ok if "celular" in r["request"]["traits"] for st in r["poem"]["stanzas"]]
    out["stanzas with phone words, phone-chip poems"] = _pct(
        sum(any(PHONE.search(x) for x in st["lines"]) for st in chip), len(chip)
    )
    pasted = 0
    for r in ok:
        q = r["request"]
        mats = [q["detail"]] + [TRAITS[t][q["language"]] for t in q["traits"]]
        text = " ".join(x for st in r["poem"]["stanzas"] for x in st["lines"])
        pasted += any(m and quality.copied(text, m) for m in mats)
    out["poems pasting a trait or detail verbatim"] = _pct(pasted, len(ok))
    if RECOUNT:
        for r in es:  # the stored counts come from whichever counter wrote the batch
            for st in r["poem"]["stanzas"]:
                st["syllables"] = [
                    _spanish().scan_line(x).metrical_syllable_count for x in st["lines"]
                ]
    counts = [c for r in es for st in r["poem"]["stanzas"] for c in st["syllables"]]
    out["lines at exactly 8 (es)"] = _pct(sum(c == 8 for c in counts), len(counts))
    es_st = [st for r in es for st in r["poem"]["stanzas"]]
    out["stanzas 8-8-8-8 (es)"] = _pct(
        sum(st["syllables"] == [8, 8, 8, 8] for st in es_st), len(es_st)
    )
    out["schemes"] = ", ".join(
        f"{k} {v}" for k, v in Counter(st["scheme"] for _, _, st in stanzas).most_common()
    )
    secs = [r["seconds"] for r in ok]
    out["seconds (median / max)"] = (
        f"{statistics.median(secs):.0f} / {max(secs):.0f}" if secs else "-"
    )
    return out


RECOUNT = False
_PHON: list = []


def _spanish():
    if not _PHON:
        from poesia.phonology.spanish import SpanishPhonology

        _PHON.append(SpanishPhonology())
    return _PHON[0]


def main(paths: list[str]) -> None:
    global RECOUNT
    if "--recount" in paths:  # measure every batch with today's counter, not the stored counts
        RECOUNT = True
        paths = [p for p in paths if p != "--recount"]
    results = [(Path(p).name, measure(Path(p))) for p in paths]
    keys = list(results[0][1])
    print("| Count | " + " | ".join(n for n, _ in results) + " |")
    print("|---" * (len(results) + 1) + "|")
    for k in keys:
        print(f"| {k} | " + " | ".join(r.get(k, "") for _, r in results) + " |")


if __name__ == "__main__":
    main(sys.argv[1:])

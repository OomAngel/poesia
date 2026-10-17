"""Build the quality-gated fine-tuning set for the calaveritas writer (audit item 7, 2026-10-09).

Only what a person approved goes in: never "passed the form checks" alone. The audit found 96% of the
first batch's rhyme lines ended on rhyme-bank words; training on that would teach the defects.
Sources:
- the transcribed classic broadside stanzas (fewshot.json, already hand-filtered), as gold;
- review-page ratings: a poem marked "good" as written, or marked "fix" with its corrected text;
- blind-comparison ticks ("buena para entrenar") on either side of a pair, resolved with the pair key.

Every example is one stanza in the same chat format the engine uses at run time (prompt.messages), so
a fine-tune learns the task it will be asked. Output is git-ignored JSONL; poems never go into git.

Usage: PYTHONPATH=src python scripts/calaveritas_data/build_training_set.py DATA_DIR EXPORT_DIR OUT.jsonl
  DATA_DIR   seeds/poetry_corpus/external/calaveritas (batches in generated/, fewshot in transcriptions/)
  EXPORT_DIR the review page's database read with out_dir: EXPORT_DIR/{reviews,choices}/<id>.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from poesia.calaveritas import prompt
from poesia.calaveritas.guard import Rejection, check_output, validate_request
from poesia.calaveritas.options import Tone


def _docs(folder: Path) -> dict[str, dict]:
    out = {}
    for f in sorted(folder.glob("*.json")) if folder.exists() else []:
        doc = json.loads(f.read_text(encoding="utf-8"))
        out[f.stem] = doc.get("data", doc)
    return out


def _stanzas(text: str) -> list[list[str]]:
    blocks = [b for b in text.replace("\r", "").split("\n\n") if b.strip()]
    return [[x.strip() for x in b.splitlines() if x.strip()] for b in blocks]


def _examples(raw_request: dict, stanzas: list[list[str]], source: str) -> list[dict]:
    try:
        req = validate_request(raw_request)
    except Rejection:
        return []
    if any(len(st) != 4 for st in stanzas) or check_output([x for st in stanzas for x in st], req):
        return []
    out = []
    for i, st in enumerate(stanzas):
        msgs = prompt.messages(req, i, stanzas[:i]) + [
            {"role": "assistant", "content": "\n".join(st)}
        ]
        out.append({"source": source, "messages": msgs})
    return out


def main(data: Path, export: Path, out: Path) -> None:
    batches = {}
    for f in sorted((data / "generated").glob("*.jsonl")):
        for line in f.open(encoding="utf-8"):
            r = json.loads(line)
            batches[r["id"]] = r
    approved: list[tuple[str, str, list[list[str]]]] = []  # (poem id, source, stanzas)
    for pid, rev in _docs(export / "reviews").items():
        rec = batches.get(pid)
        if not rec or "poem" not in rec:
            continue
        if rev.get("status") == "good":
            approved.append((pid, "review:good", [s["lines"] for s in rec["poem"]["stanzas"]]))
        elif rev.get("status") == "fix" and rev.get("text"):
            approved.append((pid, "review:fixed", _stanzas(rev["text"])))
    key_path = data / "generated" / "pairs_key.json"
    key = json.loads(key_path.read_text()) if key_path.exists() else {}
    for pair_id, ch in _docs(export / "choices").items():
        for side in ("a", "b"):
            pid = key.get(pair_id, {}).get(side)
            rec = batches.get(pid or "")
            if ch.get(f"train_{side}") and rec and "poem" in rec:
                approved.append((pid, "pair:train", [s["lines"] for s in rec["poem"]["stanzas"]]))
    rows: list[dict] = []
    seen = set()
    for pid, source, stanzas in approved:
        if pid in seen:
            continue
        seen.add(pid)
        rows += _examples(batches[pid]["request"], stanzas, source)
    n_approved = len(seen)
    fewshot = json.loads((data / "transcriptions" / "fewshot.json").read_text(encoding="utf-8"))
    for tone, pool in fewshot.get("es", {}).items():
        for ex in pool:
            if ex["id"] in seen:  # a stanza can sit in two tones' pools; train on it once
                continue
            seen.add(ex["id"])
            raw = {
                "language": "es",
                "name": "la Calavera",
                "recipient": "publica",
                "tone": Tone(tone).value,
                "stanzas": 1,
                "traits": [],
                "detail": "",
                "birth_year": 1980,
            }
            rows += _examples(raw, [ex["lines"]], f"classic:{ex['id']}")
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = {}
    for r in rows:
        k = r["source"].split(":")[0]
        by[k] = by.get(k, 0) + 1
    print(f"{len(rows)} stanza examples -> {out}; by source: {by}; approved poems: {n_approved}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))

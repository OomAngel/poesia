"""Summarise a traced review batch (generate_batch.py --trace): why requests failed, which checks
discard drafts and lines, and how much of each finished stanza is still the model's own draft.

Usage: python scripts/calaveritas_data/trace_summary.py BATCH.jsonl [--lang es]
Prints counts only (no poem text), so the output can go into notes and commits.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path


def _key(line: str) -> str:
    return "".join(ch for ch in line.lower() if ch.isalnum())


def _cause(rec: dict) -> str:
    """The first reason the trace shows for a failed request."""
    tr = rec.get("trace") or []
    plan = next((e for e in tr if e["kind"] == "plan"), None)
    if plan is None or "error" in plan:
        return "plan call failed" + (f" ({plan['seconds']} s)" if plan else "")
    if any(e["kind"] == "provider_error" for e in tr):
        return "provider error after the plan"
    if any(e["kind"] == "over_budget" for e in tr) or any(
        e["kind"] == "fallback_failed" and e.get("over_budget") for e in tr
    ):
        return "time budget ran out"
    if any(e["kind"] == "fallback_failed" for e in tr):
        return "fallback found no line"
    return "other: " + rec.get("error", "?")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--lang", default="es")
    args = ap.parse_args()
    recs = [json.loads(x) for x in Path(args.batch).open()]
    recs = [r for r in recs if r["request"]["language"] == args.lang]
    ok = [r for r in recs if "poem" in r]
    print(f"{args.lang}: {len(ok)}/{len(recs)} poems; failed {len(recs) - len(ok)}")
    print("  failures:", dict(Counter(_cause(r) for r in recs if "poem" not in r)))

    plans = [e["seconds"] for r in recs for e in r.get("trace", []) if e["kind"] == "plan"]
    if plans:
        print(
            f"  plan call: median {statistics.median(plans):.1f} s, max {max(plans):.1f} s, "
            f"over 25 s: {sum(p > 25 for p in plans)}/{len(plans)}"
        )
    secs = [r["seconds"] for r in recs]
    print(f"  seconds per request: median {statistics.median(secs):.0f}, max {max(secs):.0f}")
    print(f"  calls per request: median {statistics.median(r['calls'] for r in recs):.0f}")

    ev = [e for r in recs for e in r.get("trace", [])]
    drafts = [e for e in ev if e["kind"] == "draft"]
    print("  stanza drafts:", dict(Counter(e["verdict"] for e in drafts)))
    syl = [s for e in drafts if e.get("syllables") for s in e["syllables"]]
    if syl:
        print(
            f"  draft lines: {len(syl)}; at 8: {sum(s == 8 for s in syl) / len(syl):.0%}; "
            f"7-9: {sum(7 <= s <= 9 for s in syl) / len(syl):.0%}; "
            f"10+: {sum(s >= 10 for s in syl) / len(syl):.0%}"
        )
    print("  condensed drafts:", sum(e["kind"] == "condensed" for e in ev))
    fails = Counter(e["problem"] for e in ev if e["kind"] == "mend_failed")
    print("  mend failed (draft dropped), by the line's problem:", dict(fails.most_common()))
    rep = Counter((e["problem"], e["after"] is not None) for e in ev if e["kind"] == "repair")
    by = {f"{p} {'repaired' if got else 'not repaired'}": n for (p, got), n in rep.items()}
    print("  line repairs:", dict(sorted(by.items())))
    print("  tightened lines:", sum(e["kind"] == "tighten" for e in ev))
    print("  fallback entered:", dict(Counter(e["stage"] for e in ev if e["kind"] == "fallback")))

    own = total = 0
    for r in ok:
        tr = r.get("trace", [])
        mended = [e for e in tr if e["kind"] == "mended"]
        for si, st in enumerate(r["poem"]["stanzas"]):
            final = [_key(x) for x in st["lines"]]
            src = next(
                (m for m in reversed(mended) if [_key(x) for x in m["lines"]] == final), None
            )
            total += len(final)
            if src is not None:
                own += sum(_key(a) == b for a, b in zip(src["draft"], final, strict=False))
    if total:
        print(
            f"  final lines that are the model's own draft line: {own}/{total} ({own / total:.0%})"
        )


if __name__ == "__main__":
    main()

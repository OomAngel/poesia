"""Write local_octosyllabic/ids.tsv: the 1,159 short octosyllabic quatrain-shaped Spanish poems
in poesia corpus_master (OCTO and Q_LOOSE and SHORT, as defined in octo_quatrains.py).

IDs and metadata only, no poem text. cm:N = 1-based line N of
/home/angel/dev/poesia/seeds/poetry_corpus/corpus_master/poems.jsonl
(sha256 41c6a60d372b87a890feb9260656afa69eaba6fa0dad233dc211d73bb65b5a76, 85,027 lines).

Inputs (copied from the 2026-10-08 research scratchpad into inputs/):
  octo_quatrains.tsv   per-poem flags, produced by octo_quatrains.py (run with the poesia env,
                       which imports poesia.phonology.spanish.SpanishPhonology.scan_line)
  mexican_authors.out  Mexican author list, produced by mexican_authors.py
The Mexican-author match (ismex) is copied verbatim from octo_breakdown.py.

Usage: python -I make_local_ids.py <inputs dir> <output ids.tsv>
"""

import csv
import re
import sys
import unicodedata

inp, out = sys.argv[1], sys.argv[2]
rows = list(
    csv.DictReader(
        open(f"{inp}/octo_quatrains.tsv", encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE
    )
)
mex = [l.split("\t")[1] for l in list(open(f"{inp}/mexican_authors.out", encoding="utf-8"))[1:]]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    if "," in s:
        a, b = s.split(",", 1)
        s = b + " " + a
    return set(re.findall(r"[a-z]+", s)) - {"de", "la", "y", "del", "fray", "sor"}


mk = [[t for t in norm(m) if len(t) > 1] for m in mex]


def ismex(a):
    at = norm(a)
    if "rojas" in at:
        return False
    return any(len(k) >= 2 and all(t in at for t in k) for k in mk)


sel = [r for r in rows if r["octo"] == "1" and r["q_loose"] == "1" and r["short"] == "1"]
with open(out, "w", encoding="utf-8") as o:
    o.write("id\tauthor\ttitle\tlines\tstanzas\tmexican\tdeath_theme\tq_strict\tsource\n")
    for r in sel:
        o.write(
            "\t".join(
                [
                    r["id"],
                    r["author"],
                    r["title"],
                    r["lines"],
                    r["stanzas"],
                    str(int(ismex(r["author"]))),
                    r["death"],
                    r["q_strict"],
                    r["source"],
                ]
            )
            + "\n"
        )
print(
    f"{len(sel)} rows; mexican {sum(ismex(r['author']) for r in sel)}; death {sum(r['death'] == '1' for r in sel)}; "
    f"q_strict {sum(r['q_strict'] == '1' for r in sel)}"
)

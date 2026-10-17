"""Octosyllabic-quatrain census of the Spanish half of corpus_master (read-only).

Per poem: engine syllable count per line (poesia SpanishPhonology.scan_line), stanza shape.
  OCTO   := >=80% of lines scan 7-9 AND mean scan in [7.3, 8.7]
            (tolerance because scan_line is exact on 63-71% of gold lines, within +-1 on ~95%;
             see validate_scan.py; classifier itself validated on gold below)
  Q_STRICT := >=2 stanzas (blank-line separated) and >=75% of stanzas have exactly 4 lines
  Q_LOOSE  := Q_STRICT, or one unbroken block whose line count is a multiple of 4 (many POSTDATA
             records carry no blank lines, so stanza breaks are unknown)
  SHORT    := 4..40 non-empty lines (calaverita size)
  DEATH    := death vocabulary (muert*, parca, calaver*, tumba, panteón, sepult*, difunt*, entierro,
             esqueleto, huesud*, flaca, pelona, calaca, catrina, ataúd, cementerio, camposanto)
Writes octo_quatrains.tsv (one row per Spanish poem, metadata + flags, no text) and prints counts.
Usage: python octo_quatrains.py
"""

import json
import re
import statistics
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, "/home/angel/dev/poesia/src")

CM = "/home/angel/dev/poesia/seeds/poetry_corpus/corpus_master/poems.jsonl"
GOLD = "/home/angel/dev/poesia/seeds/poetry_corpus/training_data_structured/"
DEATH = re.compile(
    r"\bmuert[eoa]s?\b|\bparca\b|\bcalaver|\btumbas?\b|\bpante[oó]n|\bsepult|\bdifunt|"
    r"\bentierro|\besqueleto|\bhuesud|\bflaca\b|\bpelona\b|\bcalaca|\bcatrina\b|\bata[uú]d|"
    r"\bcementerio|\bcamposanto",
    re.I,
)
_P = None


def scan(lines):
    global _P
    if _P is None:
        from poesia.phonology.spanish import SpanishPhonology

        _P = SpanishPhonology()
    out = []
    for l in lines:
        try:
            out.append(_P.scan_line(l).metrical_syllable_count)
        except Exception:
            out.append(0)
    return out


def is_octo(counts):
    if not counts:
        return False
    share = sum(1 for c in counts if 7 <= c <= 9) / len(counts)
    return share >= 0.8 and 7.3 <= statistics.mean(counts) <= 8.7


def analyse(item):
    i, r = item
    txt = r["completion"]
    stanzas = [
        [l for l in s.split("\n") if l.strip()] for s in re.split(r"\n\s*\n", txt) if s.strip()
    ]
    lines = [l.strip() for s in stanzas for l in s]
    n = len(lines)
    q_strict = len(stanzas) >= 2 and sum(1 for s in stanzas if len(s) == 4) / len(stanzas) >= 0.75
    q_loose = q_strict or (len(stanzas) == 1 and n >= 4 and n % 4 == 0)
    octo = is_octo(scan(lines[:80])) if 4 <= n <= 200 else False
    return (
        f"cm:{i}",
        r.get("source", ""),
        r.get("author", ""),
        (r.get("title") or "")[:60].replace("\t", " "),
        r.get("form", ""),
        r.get("century", ""),
        n,
        len(stanzas),
        int(octo),
        int(q_strict),
        int(q_loose),
        int(4 <= n <= 40),
        int(bool(DEATH.search(txt))),
    )


def gold_check():
    """Classifier recall on gold-octosyllabic poems, false-positive rate on gold sonnets."""

    def gold_counts(fname):
        for l in open(GOLD + fname, encoding="utf-8"):
            r = json.loads(l)
            lines = [x for x in r["completion"].split("\n") if x.strip()]
            m = r.get("metre") or []
            if len(lines) == len(m) and lines:
                g = [len([x for x in b.split("|") if x]) if "|" in b else len(b) for b in m]
                yield lines, g

    pos = [
        (ls)
        for ls, g in gold_counts("lirica_siglo_de_oro.jsonl")
        if sum(1 for x in g if x == 8) / len(g) >= 0.8
    ]
    neg = [ls for ls, g in gold_counts("sonetos_siglo_de_oro.jsonl")][:400]
    neg7 = [
        ls
        for ls, g in gold_counts("lirica_siglo_de_oro.jsonl")
        if sum(1 for x in g if x == 7) / len(g) >= 0.8
    ]
    rec = sum(is_octo(scan(ls[:80])) for ls in pos) / max(1, len(pos))
    fp = sum(is_octo(scan(ls)) for ls in neg) / len(neg)
    fp7 = sum(is_octo(scan(ls[:80])) for ls in neg7) / max(1, len(neg7))
    print(
        f"GOLD CHECK: recall on {len(pos)} gold-octosyllabic poems = {rec:.3f}; "
        f"false-positive on {len(neg)} gold hendecasyllabic sonnets = {fp:.3f}; "
        f"flagged on {len(neg7)} gold-heptasyllabic poems = {fp7:.3f}"
    )


def main():
    gold_check()
    items = []
    with open(CM, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            r = json.loads(line)
            if r["language"] == "es":
                items.append((i, r))
    with Pool(12) as pool:
        rows = pool.map(analyse, items, chunksize=200)
    with open("octo_quatrains.tsv", "w", encoding="utf-8") as o:
        o.write(
            "id\tsource\tauthor\ttitle\tform\tcentury\tlines\tstanzas\tocto\tq_strict\tq_loose\tshort\tdeath\n"
        )
        for row in rows:
            o.write("\t".join(map(str, row)) + "\n")
    c = Counter()
    for row in rows:
        octo, qs, ql, short, death = row[8:13]
        c["es poems"] += 1
        c["octo"] += octo
        c["q_strict"] += qs
        c["octo & q_strict"] += octo and qs
        c["octo & q_loose"] += octo and ql
        c["octo & q_strict & short"] += octo and qs and short
        c["octo & q_loose & short"] += octo and ql and short
        c["octo & q_loose & short & death"] += octo and ql and short and death
        c["octo & q_strict & short & death"] += octo and qs and short and death
    for k, v in c.items():
        print(f"{k}\t{v}")


if __name__ == "__main__":
    main()

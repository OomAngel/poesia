#!/usr/bin/env python3
"""Corpus analytics — bronze JSONL -> silver parquet -> gold SQL insights.

A self-contained medallion pipeline over the poetry corpus (~31k poems,
~1.3k authors) using DuckDB: read the raw .jsonl files (bronze), write a
normalized parquet (silver), then surface insights (gold) — form/author/
language/source distributions and, using the real Spanish phonology scanner,
per-author metre consistency for sonetos.

Usage:
    python scripts/corpus_analytics.py
    python scripts/corpus_analytics.py --sample 500    # cap soneto scan (fast)
    python scripts/corpus_analytics.py --sample 0      # scan every soneto
"""

from __future__ import annotations

import argparse
import os


def _scan_soneto_metre(con, sample: int) -> list[tuple]:
    """Per-author 11-syllable adherence for Spanish sonetos (Python+phonology)."""
    from poesia.phonology.spanish import SpanishPhonology

    phonology = SpanishPhonology()
    rows = con.execute(
        "SELECT author, completion FROM poems "
        "WHERE lower(form) = 'soneto' AND lower(language) = 'es' AND completion IS NOT NULL"
    ).fetchall()
    if sample > 0:
        rows = rows[:sample]

    per_author: dict[str, list[int]] = {}
    for author, completion in rows:
        lines = [ln for ln in completion.split("\n") if ln.strip()]
        if not lines:
            continue
        ok = sum(1 for ln in lines if phonology.scan_line(ln).metrical_syllable_count == 11)
        per_author.setdefault(author or "(unknown)", [0, 0])
        per_author[author or "(unknown)"][0] += ok
        per_author[author or "(unknown)"][1] += len(lines)

    return sorted(
        ((a, ok, tot, round(ok / tot, 3)) for a, (ok, tot) in per_author.items() if tot >= 20),
        key=lambda r: -r[3],
    )[:15]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=1000, help="sonetos to scan (0 = all)")
    parser.add_argument("--out", default="data/insights", help="output directory")
    args = parser.parse_args()

    import duckdb

    os.makedirs(args.out, exist_ok=True)
    con = duckdb.connect()

    # ---- bronze -> silver --------------------------------------------------
    print("· bronze: reading corpus .jsonl into DuckDB …", flush=True)
    con.execute(
        """
        CREATE TABLE poems AS
        SELECT
            *,
            regexp_extract(filename, 'seeds/poetry_corpus/([^/]+)/', 1) AS source_dir,
            length(regexp_extract_all(completion, '\\n')) + 1 AS n_lines
        FROM read_json_auto('seeds/poetry_corpus/*/*.jsonl', union_by_name=true)
        WHERE completion IS NOT NULL AND completion != ''
        """
    )
    total = con.execute("SELECT COUNT(*) FROM poems").fetchone()[0]
    print(f"  → {total} poems loaded", flush=True)

    print(f"· silver: writing {args.out}/poems.parquet …", flush=True)
    con.execute(f"COPY poems TO '{args.out}/poems.parquet' (FORMAT PARQUET)")

    # ---- gold: SQL insights ------------------------------------------------
    print("· gold: running SQL insights …", flush=True)
    gold: list[tuple[str, list[tuple]]] = []
    gold.append(
        (
            "form_distribution",
            con.execute(
                "SELECT lower(form) AS form, COUNT(*) AS poems FROM poems GROUP BY 1 ORDER BY 2 DESC"
            ).fetchall(),
        )
    )
    gold.append(
        (
            "language_distribution",
            con.execute(
                "SELECT lower(language) AS language, COUNT(*) AS poems FROM poems GROUP BY 1 ORDER BY 2 DESC"
            ).fetchall(),
        )
    )
    gold.append(
        (
            "source_distribution",
            con.execute(
                "SELECT source, COUNT(*) AS poems FROM poems GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
            ).fetchall(),
        )
    )
    gold.append(
        (
            "top_20_authors",
            con.execute(
                "SELECT author, COUNT(*) AS poems FROM poems WHERE author IS NOT NULL "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 20"
            ).fetchall(),
        )
    )
    gold.append(
        (
            "lines_per_poem",
            con.execute(
                "SELECT MIN(n_lines) AS min_lines, ROUND(AVG(n_lines),1) AS avg_lines, "
                "MAX(n_lines) AS max_lines FROM poems"
            ).fetchall(),
        )
    )

    print(f"· gold: scanning soneto metre (sample={args.sample}) …", flush=True)
    metre = _scan_soneto_metre(con, args.sample)
    gold.append(("soneto_metre_consistency_top15 (11-syllable adherence, >=20 lines)", metre))

    # ---- report ------------------------------------------------------------
    report_path = f"{args.out}/report.txt"
    print(f"· writing {report_path} …", flush=True)
    with open(report_path, "w") as fh:
        fh.write("POESIA CORPUS INSIGHTS\n")
        fh.write(f"poems: {total}\n")
        fh.write("=" * 60 + "\n\n")
        for name, rows in gold:
            fh.write(f"[{name}]\n")
            for r in rows:
                fh.write("  " + " | ".join(str(x) for x in r) + "\n")
            fh.write("\n")
    print(f"done. report → {report_path}")


if __name__ == "__main__":
    main()

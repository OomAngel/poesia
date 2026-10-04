#!/usr/bin/env python3
"""Ingest downloaded poetry corpora (Spanish and English) into training_data_structured/.

Sources (downloaded into seeds/poetry_corpus/external/, see docs/CORPUS_SOURCES.md
"External corpora"):

    disco-5.0/                                    DISCO v5.0, 4,530 sonnets, CC BY 4.0
    CorpusSonetosSigloDeOro-master/               5,078 Golden-Age sonnets, metre per line
    CorpusGeneralPoesiaLiricaCastellanaDelSigloDeOro-master/   475 lyric poems, metre per line
    gold/                                         ADSO gold standard, 100 sonnets (hand scansion)
    postdata_poesias/                             POSTDATA poesias (Hugging Face), 25,300 poems, es
    pd_poetry/poems.json                          DanFosing/public-domain-poetry, 38,499 poems, en, CC0
    poetry_foundation/PoetryFoundationData.csv    suayptalha/Poetry-Foundation-Poems, 13,854 poems, en

The ADSO gold sonnets are drawn from the Golden-Age sonnet corpus, so they are written to
seeds/poetry_corpus/eval_gold/ and excluded from the training output: they are the
held-out reference for the metre scorer, not training data.

A poem is skipped when its normalised text (lowercase, letters only) or its normalised
first line already exists anywhere in training_data_structured/: the first-line rule
catches the same poem in another edition (different spelling or punctuation), which
exact matching misses. Re-running adds nothing. Counts of new vs skipped are printed.

Usage:
    python scripts/ingest_external_corpora.py            # write
    python scripts/ingest_external_corpora.py --dry-run  # count only
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

from defusedxml.ElementTree import DefusedXMLParser
from defusedxml.ElementTree import parse as safe_parse

CORPUS_DIR = "seeds/poetry_corpus"
EXTERNAL_DIR = os.path.join(CORPUS_DIR, "external")
STRUCTURED_DIR = os.path.join(CORPUS_DIR, "training_data_structured")
EVAL_GOLD_DIR = os.path.join(CORPUS_DIR, "eval_gold")
TEI = "{http://www.tei-c.org/ns/1.0}"
SONETO_RHYME = "ABBA ABBA CDC DCD"


def normalise(text: str) -> str:
    return re.sub(r"[^a-záéíóúüñ]", "", text.lower())


def first_line_key(text: str) -> str:
    lines = [line for line in text.split("\n") if line.strip()]
    return "first:" + normalise(lines[0])[:40] if lines else ""


def existing_keys() -> set[str]:
    keys = set()
    for path in glob.glob(os.path.join(STRUCTURED_DIR, "*.jsonl")):
        for line in open(path, encoding="utf-8"):
            comp = json.loads(line).get("completion", "")
            if isinstance(comp, list):
                comp = "\n".join(comp)
            keys.add(normalise(comp))
            keys.add(first_line_key(comp))
    return keys


def clean(text: str) -> str:
    lines = [
        line.rstrip() for line in text.replace("\r", "").replace("\u2028", "\n").strip().split("\n")
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def record(
    text: str, author: str, title: str, source: str, form: str, language: str = "es", **extra
) -> dict:
    first = " ".join(re.sub(r"[^\wáéíóúüñ ]", "", text.split("\n")[0].lower()).split()[:3])
    lang_name = "Spanish" if language == "es" else "English"
    if form == "soneto":
        prompt = f"Write a soneto in Spanish.\nRhyme scheme: {SONETO_RHYME}.\nTheme: {first}.\n\n"
    else:
        prompt = f"Write a {lang_name} poem: {title}"
    return {
        "prompt": prompt,
        "completion": text,
        "author": author,
        "source": source,
        "title": title,
        "form": form,
        "language": language,
        **extra,
    }


# --- DISCO v5 (plain text per sonnet + metadata tables) ---------------------------


def read_disco() -> list[dict]:
    root = os.path.join(EXTERNAL_DIR, "disco-5.0")
    meta = {
        r["poem_id"]: r
        for r in csv.DictReader(
            open(os.path.join(root, "poem_metadata.tsv"), encoding="utf-8"), delimiter="\t"
        )
    }
    authors = {
        r["aid"]: r
        for r in csv.DictReader(
            open(os.path.join(root, "author_metadata.tsv"), encoding="utf-8"), delimiter="\t"
        )
    }
    out = []
    for path in sorted(glob.glob(os.path.join(root, "txt", "*", "per-sonnet", "*.txt"))):
        poem_id = os.path.basename(path)[len("disco") : -len(".txt")]
        m = meta.get(poem_id, {})
        a = authors.get(m.get("author_id", ""), {})
        text = "\n".join(
            line.rstrip() for line in open(path, encoding="utf-8").read().strip().splitlines()
        )
        period = path.split(os.sep)[-3]
        out.append(
            record(
                text,
                m.get("author", ""),
                m.get("title", "") or m.get("incipit", ""),
                "disco_v5",
                "soneto",
                poem_id=poem_id,
                period=period,
                author_death=a.get("death", ""),
            )
        )
    return out


# --- TEI corpora by Navarro-Colorado (metre annotated per line) -------------------


def _tei_poem(path: str) -> tuple[str, str, list[tuple[str, str]], list[str]]:
    # Comments are kept: the lyric corpus stores each plain line in one.
    parser = DefusedXMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = safe_parse(path, parser=parser).getroot()
    author_el = tree.find(f".//{TEI}sourceDesc//{TEI}author")
    if author_el is None:
        author_el = tree.find(f".//{TEI}author")
    author = " ".join((author_el.text or "").split()) if author_el is not None else ""
    title_el = tree.find(f".//{TEI}body/{TEI}head/{TEI}title")
    title = " ".join("".join(title_el.itertext()).split()) if title_el is not None else ""
    stanzas, types = [], []
    for lg in tree.iter(f"{TEI}lg"):
        lines = []
        for l in lg.findall(f"{TEI}l"):
            words = l.findall(f"{TEI}w")
            if words:  # lyric corpus: syllabified words, the plain line sits in a comment
                comment = next((c for c in l.iter() if c.tag is ET.Comment), None)
                text = (
                    comment.text.strip()
                    if comment is not None and comment.text
                    else " ".join("".join(w.itertext()).replace("|", "") for w in words)
                )
            else:
                text = " ".join("".join(l.itertext()).split())
            lines.append((text, l.get("met", "")))
        if lines:
            stanzas.append(lines)
            types.append((lg.get("type") or "").lower())
    flat = [x for s in stanzas for x in s]
    text = "\n\n".join("\n".join(t for t, _ in s) for s in stanzas)
    return author, title, flat, [text] + types


def read_tei(folder: str, source: str, exclude: set[str]) -> list[dict]:
    out = []
    for path in sorted(
        glob.glob(os.path.join(EXTERNAL_DIR, folder, "**", "*.xml"), recursive=True)
    ):
        if os.path.basename(path) in exclude:
            continue
        author, title, lines, (text, *types) = _tei_poem(path)
        if not lines:
            continue
        is_soneto = len(lines) == 14 or "cuarteto" in types
        form = "soneto" if is_soneto else (types[0] if types and types[0] else "poema")
        out.append(
            record(
                text,
                author,
                title,
                source,
                form,
                metre=[m for _, m in lines],
                file=os.path.basename(path),
            )
        )
    return out


# --- Plain tables from Hugging Face ------------------------------------------------


def read_postdata() -> list[dict]:
    csv.field_size_limit(10**9)
    out = []
    for name in ("poesias_train.csv", "poesias_eval.csv"):
        for r in csv.DictReader(
            open(os.path.join(EXTERNAL_DIR, "postdata_poesias", name), encoding="utf-8")
        ):
            if r["language"] not in ("es", "en"):
                continue
            author = " ".join(reversed(r["author"].replace("_", " ").split(",", 1))).strip()
            out.append(
                record(
                    clean(r["text"]),
                    author,
                    r["title"].replace("_", " "),
                    "postdata_poesias",
                    "poema",
                    r["language"],
                    century=r["century"],
                )
            )
    return out


def read_pd_poetry() -> list[dict]:
    rows = json.load(open(os.path.join(EXTERNAL_DIR, "pd_poetry", "poems.json"), encoding="utf-8"))
    return [
        record(clean(r["text"]), r["Author"], r["Title"].strip(), "pd_poetry", "poem", "en")
        for r in rows
    ]


def _undouble(text: str) -> str:
    """Poetry Foundation scrape: every line ends in a double newline and stanza breaks are
    longer runs. Collapse when most lines are followed by a blank one."""
    text = text.replace("\r", "").replace("\u2028", "\n").strip("\n")
    lines = text.split("\n")
    blank = sum(1 for line in lines if not line.strip())
    if blank < 0.8 * (len(lines) - blank):
        return clean(text)
    text = re.sub(r"\n(?:[ \t]*\n){2,}", "\x00", text)  # 3+ newlines: stanza break
    text = re.sub(r"\n[ \t]*\n", "\n", text).replace("\x00", "\n\n")
    return clean(text)


def read_poetry_foundation() -> list[dict]:
    csv.field_size_limit(10**9)
    path = os.path.join(EXTERNAL_DIR, "poetry_foundation", "PoetryFoundationData.csv")
    return [
        record(
            _undouble(r["Poem"]),
            r["Poet"].strip(),
            " ".join(r["Title"].split()),
            "poetry_foundation",
            "poem",
            "en",
        )
        for r in csv.DictReader(open(path, encoding="utf-8"))
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gold_files = {
        os.path.basename(p) for p in glob.glob(os.path.join(EXTERNAL_DIR, "gold", "*.xml"))
    }
    seen = existing_keys()
    print(
        f"existing structured poems (normalised): {sum(not k.startswith('first:') for k in seen)}"
    )

    sets = {
        "disco_v5": read_disco(),
        "sonetos_siglo_de_oro": read_tei(
            "CorpusSonetosSigloDeOro-master", "sonetos_siglo_de_oro", gold_files
        ),
        "lirica_siglo_de_oro": read_tei(
            "CorpusGeneralPoesiaLiricaCastellanaDelSigloDeOro-master", "lirica_siglo_de_oro", set()
        ),
        "postdata_poesias": read_postdata(),
        "pd_poetry_en": read_pd_poetry(),
        "poetry_foundation_en": read_poetry_foundation(),
    }
    gold = read_tei("gold", "adso_gold_100", set())

    for name, records in sets.items():
        new = []
        for r in records:
            key, first = normalise(r["completion"]), first_line_key(r["completion"])
            if len(key) >= 60 and key not in seen and first not in seen:
                seen.update((key, first))
                new.append(r)
        print(
            f"{name}: read {len(records)}, new {len(new)}, already present {len(records) - len(new)}"
        )
        if not args.dry_run and new:
            with open(os.path.join(STRUCTURED_DIR, f"{name}.jsonl"), "w", encoding="utf-8") as f:
                for r in new:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"adso_gold_100 (eval only, excluded from training): {len(gold)}")
    if not args.dry_run:
        os.makedirs(EVAL_GOLD_DIR, exist_ok=True)
        with open(os.path.join(EVAL_GOLD_DIR, "adso_gold_100.jsonl"), "w", encoding="utf-8") as f:
            for r in gold:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

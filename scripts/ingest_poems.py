#!/usr/bin/env python3
"""Convert raw poem collections into structured training format.

Reads raw poem JSONL files and converts them to the structured format
expected by train_poetry_lora.py. Auto-detects poetic form from line count.

Usage:
    # Convert 1000 curated sonetos
    python scripts/ingest_poems.py --input seeds/poetry_corpus/sonetos_curated/sonetos.jsonl \\
        --output seeds/poetry_corpus/training_data_structured/sonetos_expanded.jsonl \\
        --max-poems 1000 --form soneto

    # Convert raw training data (detect form automatically)
    python scripts/ingest_poems.py --input seeds/poetry_corpus/training_data/train.jsonl \\
        --output seeds/poetry_corpus/training_data_structured/poems_expanded.jsonl \\
        --max-poems 1000
"""

import argparse
import json
import os
import sys
from pathlib import Path


# Line count -> poetic form mapping for Spanish
FORM_BY_LINE_COUNT = {
    14: "soneto",      # 4+4+3+3
    4: "cuarteto",     # 4 lines
    5: "quintilla",    # 5 lines (or quinteto)
    8: "romance",      # 8+ syllable 8-line stanzas
    10: "decima",      # 10 lines
    3: "haiku",        # 3 lines (Japanese form, also used in Spanish)
}

# Rhyme scheme by form
RHYME_SCHEMES = {
    "soneto": "ABBA ABBA CDC DCD",
    "cuarteto": "ABBA",
    "decima": "ABBAA CCDDC",  # Espinela
    "haiku": "5-7-5",
    "romance": "8-",  # Assonant rhyme in even lines
}


def detect_form(text: str) -> str | None:
    """Detect poetic form from the number of lines in the text."""
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    n_lines = len(lines)
    return FORM_BY_LINE_COUNT.get(n_lines)


def extract_theme(text: str) -> str:
    """Extract a theme from the first line of a poem (best guess).

    Takes the first content words from line 1, excluding articles/prepositions.
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return "poesia"
    first_line = lines[0].lower().strip("¿¡«»\"'.,;:!?—")
    # Take 2-3 significant words from the first line
    stopwords = {"el", "la", "los", "las", "un", "una", "en", "de", "del", "por",
                 "con", "sin", "para", "que", "y", "e", "o", "a", "al", "su",
                 "tu", "mi", "se", "no", "es", "como", "más", "tan", "cuando",
                 "entre", "todo", "tras"}
    words = [w for w in first_line.split() if w not in stopwords][:3]
    if words:
        return " ".join(words)
    return "poesia"


def convert_raw_poem(record: dict, source: str, force_form: str | None = None) -> dict | None:
    """Convert a raw poem record to structured training format.

    Handles two input formats:
    1. {'text': '...', 'source': '...', 'author': '...'}  (curated)
    2. {'prompt': 'Poem:\\n', 'completion': '...', 'author': '...'}  (training_data)

    Returns structured record or None if conversion fails.
    """
    # Extract poem text from either format
    text = record.get("text") or record.get("completion")
    if not text:
        return None

    author = record.get("author", "unknown")
    source_field = record.get("source", source)

    # Detect or force form
    form = force_form or detect_form(text)
    if not form:
        return None  # Skip unknown forms

    # Extract a theme from the first line
    theme = extract_theme(text)

    # Build structured prompt
    rhyme = RHYME_SCHEMES.get(form, "")
    if form == "soneto":
        prompt = (
            f"Write a soneto in Spanish.\n"
            f"Rhyme scheme: {rhyme}.\n"
            f"Theme: {theme}.\n\n"
        )
    elif form == "haiku":
        prompt = (
            f"Write a haiku in Spanish.\n"
            f"Syllable pattern: {rhyme}.\n"
            f"Theme: {theme}.\n\n"
        )
    else:
        prompt = (
            f"Write a {form} in Spanish.\n"
            f"Theme: {theme}.\n\n"
        )

    return {
        "prompt": prompt,
        "completion": text.strip(),
        "author": author,
        "source": source_field,
        "form": form,
        "language": "es",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    parser.add_argument("--max-poems", type=int, default=1000, help="Max poems to convert")
    parser.add_argument("--form", default=None, help="Force form (soneto, haiku, etc.)")
    parser.add_argument("--source", default="ingested", help="Source label for records")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Input not found: {args.input}")
        sys.exit(1)

    # Read and convert
    converted = 0
    skipped = 0
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_path) as fin, open(output_path, "w") as fout:
        for line in fin:
            if converted >= args.max_poems:
                break
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                structured = convert_raw_poem(record, args.source, force_form=args.form)
                if structured:
                    fout.write(json.dumps(structured, ensure_ascii=False) + "\n")
                    converted += 1
                else:
                    skipped += 1
            except json.JSONDecodeError:
                skipped += 1

    print(f"✅ Converted {converted} poems to {args.output}")
    print(f"   Skipped: {skipped} (unknown forms or parse errors)")
    print(f"   Forms: run this to check:")
    print(f"     python3 -c \"import json,collections; "
          f"c=collections.Counter(json.loads(l)['form'] for l in open('{args.output}')); "
          f"print(dict(c))\"")


if __name__ == "__main__":
    main()

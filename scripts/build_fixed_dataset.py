#!/usr/bin/env python3
"""Build fixed-format training data matching the inference prompt structure.

The bug: training used full-poem prompts ("Write a soneto... Theme: X"),
but inference uses line-by-line prompts ("Write line 3. Exactly 11 syllables...
Output ONLY the single bare poetry line"). The model learned to echo the
full-poem instruction format.

Fix: convert each poem into line-by-line training examples where the prompt
EXACTLY matches what candidate_generator.py sends at inference. Also add
title-generation examples so the model can title its own poems.

Usage:
    python scripts/build_fixed_dataset.py --output mlops/data/train_fixed.jsonl
    python scripts/build_fixed_dataset.py --dry-run
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import sys
from collections import Counter

POESIA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRUCTURED_DIR = os.path.join(POESIA_ROOT, "seeds", "poetry_corpus", "training_data_structured")

LANG_NAMES = {"es": "Spanish", "en": "English", "nl": "Dutch"}
SONETO_RHYME = "ABBA ABBA CDC DCD"


def rhyme_key_for_line(line_idx: int, scheme: str) -> str | None:
    scheme = scheme.replace(" ", "")
    if line_idx < len(scheme):
        return scheme[line_idx]
    return None


def syllable_target(lines: list[str], line_idx: int, form: str) -> int | None:
    if form == "soneto":
        return 11
    if form == "haiku":
        return [5, 7, 5][line_idx] if line_idx < 3 else None
    if form in ("romance", "decima"):
        return 8
    return None


def build_line_prompt(theme, language, form, prior_lines, line_idx,
                      target_syllables, rhyme_word) -> str:
    """Build a prompt EXACTLY matching candidate_generator.py's inference prompt."""
    lang_name = LANG_NAMES.get(language, language)
    prior_block = ""
    if prior_lines:
        numbered = "\n".join(f"{i+1}. {ln}" for i, ln in enumerate(prior_lines))
        prior_block = f"Poem so far:\n{numbered}\n\n"

    constraints = []
    if target_syllables:
        constraints.append(f"Exactly {target_syllables} syllables.")
    if rhyme_word:
        constraints.append(f'End the line with a word that rhymes with "{rhyme_word}" (use a DIFFERENT word).')
    constraints.append("Do NOT begin the line with the same word as any prior line.")
    constraints_str = " ".join(constraints)

    return (
        f"You are writing a {lang_name} {form} on the theme: {theme}.\n"
        f"{prior_block}"
        f"Write line {line_idx + 1}. {constraints_str}\n"
        f"Output ONLY the single bare poetry line — no explanation, no preamble, no numbering, no quotes."
    )


def build_title_prompt(theme, language, form, poem_lines) -> str:
    lang_name = LANG_NAMES.get(language, language)
    numbered = "\n".join(f"{i+1}. {ln}" for i, ln in enumerate(poem_lines))
    return (
        f"You are writing a {lang_name} {form} on the theme: {theme}.\n"
        f"Poem:\n{numbered}\n\n"
        f"Write a title for this {form}.\n"
        f"Output ONLY the title."
    )


def poem_to_examples(record: dict, poem_id: str) -> list[dict]:
    """Convert one poem record into line-by-line + title training examples."""
    theme = record.get("theme") or record.get("title") or "poesia"
    language = record.get("language", "es")
    form = record.get("form", "poema")
    completion = record.get("completion", "")
    if isinstance(completion, list):
        completion = "\n".join(completion)
    lines = [l.strip() for l in completion.split("\n") if l.strip()]
    if len(lines) < 3:
        return []

    examples = []
    rhyme_scheme = SONETO_RHYME if form == "soneto" else None

    for idx, line in enumerate(lines):
        target_syll = syllable_target(lines, idx, form)
        rhyme_word = None
        if rhyme_scheme and target_syll:
            key = rhyme_key_for_line(idx, rhyme_scheme)
            if key:
                for prev_idx in range(idx):
                    if rhyme_key_for_line(prev_idx, rhyme_scheme) == key:
                        words = lines[prev_idx].split()
                        if words:
                            rhyme_word = words[-1].strip(".,;:¡!¿?")
                        break
        prompt = build_line_prompt(theme, language, form, lines[:idx], idx,
                                   target_syll, rhyme_word)
        examples.append({
            "prompt": prompt,
            "completion": line,
            "poem_id": poem_id,
            "title": record.get("title", ""),
            "author": record.get("author", ""),
            "source": record.get("source", ""),
            "form": form,
            "language": language,
        })

    title = record.get("title", "").strip()
    if title and len(title) > 2:
        title_prompt = build_title_prompt(theme, language, form, lines)
        examples.append({
            "prompt": title_prompt,
            "completion": title,
            "poem_id": poem_id,
            "title": title,
            "author": record.get("author", ""),
            "source": record.get("source", ""),
            "form": form,
            "language": language,
            "is_title": True,
        })

    return examples


def load_all_poems() -> list[dict]:
    """Load and dedup all structured poems."""
    seen = set()
    poems = []
    files = sorted(glob.glob(os.path.join(STRUCTURED_DIR, "*.jsonl")))
    skip_prefixes = ("master_train_filtered", "sonetos_filtered_t2_scored",
                     "sonetos_scored", "eval_expanded")
    for path in files:
        base = os.path.basename(path)
        if any(base.startswith(p) for p in skip_prefixes):
            continue
        try:
            for line in open(path):
                d = json.loads(line)
                comp = d.get("completion", "")
                if isinstance(comp, list):
                    comp = "\n".join(comp)
                h = hashlib.md5(comp.encode()).hexdigest()[:12]
                if h in seen:
                    continue
                seen.add(h)
                d["completion"] = comp
                d["source"] = base.replace(".jsonl", "")
                poems.append(d)
        except Exception as e:
            print(f"  [skip] {base}: {e}", file=sys.stderr)
    return poems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.path.join(POESIA_ROOT, "mlops", "data", "train_fixed.jsonl"))
    parser.add_argument("--max-poems", type=int, default=0, help="0 = use all")
    parser.add_argument("--max-examples", type=int, default=0, help="0 = no limit")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-ratio", type=float, default=0.05)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)

    print("Loading poems...")
    poems = load_all_poems()
    print(f"  Loaded {len(poems)} unique poems")

    form_counts = Counter(p.get("form", "unknown") for p in poems)
    print(f"  Forms: {dict(form_counts)}")

    if args.max_poems:
        poems = random.sample(poems, min(args.max_poems, len(poems)))

    print("\nBuilding examples...")
    all_examples = []
    title_count = 0
    for p in poems:
        pid = hashlib.md5(p.get("completion", "").encode()).hexdigest()[:10]
        examples = poem_to_examples(p, pid)
        all_examples.extend(examples)
        title_count += sum(1 for e in examples if e.get("is_title"))
    print(f"  Generated {len(all_examples)} examples ({title_count} title examples)")

    if args.max_examples:
        all_examples = all_examples[: args.max_examples]

    if args.dry_run:
        print("\n=== DRY RUN — sample examples ===")
        for e in all_examples[:3]:
            print(f"\nPROMPT:\n{e['prompt']}\n")
            print(f"COMPLETION: {e['completion']}")
            print("-" * 50)
        return

    random.shuffle(all_examples)
    n_eval = int(len(all_examples) * args.eval_ratio)
    eval_examples = all_examples[:n_eval]
    train_examples = all_examples[n_eval:]

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    train_path = args.output
    eval_path = args.output.replace("train_fixed", "eval_fixed")

    with open(train_path, "w") as f:
        for e in train_examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(eval_path, "w") as f:
        for e in eval_examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"\n✅ Train: {len(train_examples)} examples → {train_path}")
    print(f"✅ Eval:  {len(eval_examples)} examples → {eval_path}")


if __name__ == "__main__":
    main()

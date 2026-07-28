"""Distill perfect sonetos from a teacher LLM (Groq) for training data.

Generates N sonetos using Groq (Llama 3.3 70B), validates each for:
- Exactly 14 lines
- Syllable count ≈ 11 per line (verified by phonology backend)
- Rejects and retries failed generations

Output: seeds/poetry_corpus/training_data_distilled/sonetos.jsonl
(in structured format ready for train_poetry_lora.py)

Usage:
    python scripts/distill_sonetos.py --count 100 --output seeds/poetry_corpus/training_data_distilled
"""

import argparse, json, os, re, sys, time, urllib.request

# ── Config ────────────────────────────────────────────────────────────
GROQ_API_KEY_ENV = "GROQ_API_KEY"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

DEFAULT_THEMES = [
    "la luna", "el mar", "la noche", "el amor", "la muerte",
    "la soledad", "el tiempo", "la primavera", "el silencio", "el fuego",
    "la lluvia", "el viento", "las estrellas", "el camino", "la memoria",
    "el sueño", "la luz", "la sombra", "el río", "la montaña",
]

SYLLABLE_TARGET = 11
MAX_RETRIES_PER_THEME = 5


def generate_soneto(api_key: str, theme: str, temperature: float = 0.8) -> str | None:
    """Ask Groq to generate one soneto on the given theme."""
    prompt = (
        f"Write a soneto in Spanish about {theme}.\n"
        f"Requirements:\n"
        f"- Exactly 14 lines\n"
        f"- Each line must be exactly {SYLLABLE_TARGET} syllables\n"
        f"- Rhyme scheme: ABBA ABBA CDC DCD\n"
        f"- Use poetic language with imagery and metaphor\n"
        f"- Output ONLY the 14 lines, nothing else, no title, no explanation\n"
    )
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 400,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{GROQ_BASE_URL}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            text = res["choices"][0]["message"]["content"].strip()
            return text
    except Exception as e:
        print(f"  [ERROR] Groq API: {e}")
        return None


def validate_soneto(text: str) -> tuple[bool, list[str], list[int]]:
    """Validate a soneto: 14 lines, correct syllable counts.

    Returns: (is_valid, lines, syllable_counts)
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Remove any non-poetic lines (explanations, titles)
    lines = [l for l in lines if not l.startswith('"') and not l.startswith('—') and not l.startswith('-')]
    
    if len(lines) != 14:
        return False, lines[:14], []

    # Lazy-import phonology (only when needed)
    from poesia.phonology.spanish import SpanishPhonology
    phonology = SpanishPhonology()

    counts = []
    for l in lines:
        scan = phonology.scan_line(l)
        counts.append(scan.metrical_syllable_count)

    # Allow deviation of ±2 syllables from target
    valid = all(abs(c - SYLLABLE_TARGET) <= 2 for c in counts)
    return valid, lines, counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100, help="Number of sonetos to generate")
    parser.add_argument("--output", default="seeds/poetry_corpus/training_data_distilled", help="Output directory")
    parser.add_argument("--themes", nargs="+", default=None, help="List of themes (default: 20 pre-defined)")
    args = parser.parse_args()

    api_key = os.environ.get(GROQ_API_KEY_ENV)
    if not api_key:
        print(f"ERROR: Set {GROQ_API_KEY_ENV} environment variable")
        sys.exit(1)

    themes = args.themes or DEFAULT_THEMES
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    generated = []
    attempts = 0
    theme_idx = 0

    print(f"Distilling {args.count} sonetos via {GROQ_MODEL}...")
    print(f"Themes: {len(themes)} available, cycling as needed")
    print()

    while len(generated) < args.count:
        theme = themes[theme_idx % len(themes)]
        theme_idx += 1
        attempts += 1

        print(f"  [{len(generated)+1}/{args.count}] {theme} (attempt {attempts})...", end=" ", flush=True)

        text = generate_soneto(api_key, theme)
        if not text:
            print("✗ API error")
            time.sleep(2)
            continue

        is_valid, lines, counts = validate_soneto(text)
        if not is_valid:
            avg = sum(counts) / len(counts) if counts else 0
            print(f"✗ {len(lines)} lines, avg={avg:.1f} syll (need 14×{SYLLABLE_TARGET})")
            time.sleep(1)
            continue

        avg_syll = round(sum(counts) / len(counts))

        # Format as structured training example
        example = {
            "prompt": f"Write a soneto in Spanish.\nSyllables per line: {avg_syll}.\nRhyme scheme: ABBA ABBA CDC DCD.\nTheme: {theme}.\n\n",
            "completion": "\n".join(lines),
            "author": "groq-llama-3.3-70b",
            "source": "distilled",
            "avg_syllables": avg_syll,
            "form": "soneto",
            "language": "es",
        }
        generated.append(example)
        print(f"✓ {len(lines)} lines, {avg_syll} syll avg")

        # Save incrementally
        if len(generated) % 10 == 0:
            out_path = os.path.join(output_dir, "sonetos.jsonl")
            with open(out_path, 'w') as f:
                for ex in generated:
                    f.write(json.dumps(ex, ensure_ascii=False) + '\n')
            print(f"  Saved {len(generated)} so far → {out_path}")

        # Rate-limit: Groq free tier = 30 RPM
        time.sleep(2.1)

    # Final save
    out_path = os.path.join(output_dir, "sonetos.jsonl")
    with open(out_path, 'w') as f:
        for ex in generated:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nDone! {len(generated)} sonetos saved to {out_path}")
    print(f"Total API attempts: {attempts}, success rate: {len(generated)/attempts*100:.0f}%")
    print(f"\nTo train with this data:")
    print(f"  python scripts/train_poetry_lora.py mlops/configs/train_v1.yaml")
    print(f"(You'll need to update train_v1.yaml to point at the distilled data)")


if __name__ == "__main__":
    main()

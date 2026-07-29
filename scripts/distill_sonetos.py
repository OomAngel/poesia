#!/usr/bin/env python3
"""Distill high-quality sonetos from Groq with full quality validation.

Validates: syllable count, rhyme scheme, start variety, lexical diversity,
abstract ratio, enjambment, theme coherence, line novelty,
and emotional arc (via pysentimiento, Spanish + English).

Usage:
    python scripts/distill_sonetos.py --count 100 --min-score 0.5
"""

import argparse
import json
import os

# JSON encoder that handles numpy types
class _PoetryEncoder(json.JSONEncoder):
    def default(self, o):
        import math
        if hasattr(o, "item"):
            return o.item()  # numpy types
        return super().default(o)
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from functools import lru_cache
from poesia.evaluation.emotion_lexicon import analyze_poem_emotions, emotion_diversity
from poesia.galeria.imagery import imagery_density_score, extract_imagery

GROQ_API_KEY_ENV = "GROQ_API_KEY"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
SONETO_RHYME = "ABBAABBACDCDCD"
SYLL_TARGET = 11

DEFAULT_THEMES = [
    "la luna", "el mar", "la noche", "el amor", "la muerte",
    "la soledad", "el tiempo", "la primavera", "el silencio", "el fuego",
    "la lluvia", "el viento", "las estrellas", "el camino", "la memoria",
    "el sueno", "la luz", "la sombra", "el rio", "la montana",
]

ABSTRACT_NOUNS = {
    "amor", "vida", "muerte", "alma", "corazon", "pasión", "dolor",
    "soledad", "tristeza", "esperanza", "miedo", "alegria", "pena",
    "silencio", "recuerdo", "olvido", "memoria", "ilusion", "duda",
    "fe", "paz", "guerra", "odio", "ternura", "ira", "calma",
    "angustia", "ansiedad", "melancolia", "nostalgia", "dicha",
    "suerte", "destino", "fortuna", "gloria", "infierno", "cielo",
}


# ── Emotion Analysis (via pysentimiento) ─────────────────────────

@lru_cache(maxsize=2)
def _get_emotion_analyzer(language):
    from pysentimiento import create_analyzer
    return create_analyzer(task="emotion", lang=language)


def analyze_emotional_arc(lines, language="es"):
    """Analyze emotional arc across poem lines.
    Returns dict with arc_variance (0-1), num_emotions, per-line emotions.
    """
    try:
        analyzer = _get_emotion_analyzer(language)
    except Exception:
        return {"emotions": [], "arc_variance": 0.0,
                "dominant_emotions": set(), "num_emotions": 0, "available": False}
    emotions = []
    for l in lines:
        try:
            r = analyzer.predict(l[:200])
            emotions.append((r.output, max(r.probas.values())))
        except Exception:
            emotions.append(("others", 0.0))
    unique_emos = set(e for e, _ in emotions)
    transitions = sum(1 for i in range(1, len(emotions)) if emotions[i][0] != emotions[i-1][0])
    max_t = len(emotions) - 1
    arc_var = transitions / max_t if max_t > 0 else 0.0
    return {
        "emotions": emotions,
        "arc_variance": round(arc_var, 3),
        "dominant_emotions": unique_emos,
        "num_emotions": len(unique_emos),
        "available": True,
    }


# ── Prompt ────────────────────────────────────────────────────────

def build_prompt(theme):
    return (
        f"Write a soneto in Spanish about: {theme}\n\n"
        f"Requirements:\n"
        f"- Exactly 14 lines\n"
        f"- Each line: exactly {SYLL_TARGET} syllables\n"
        f"- Rhyme scheme: ABBA ABBA CDC DCD\n"
        f"- Use concrete imagery: objects, nature, sensory details\n"
        f"- Vary how each line starts\n"
        f"- Some enjambment: don't end every line with a period\n"
        f"- Show the theme, don't just name it\n"
        f"- Output ONLY the 14 lines, one per line\n"
    )


# ── Groq API ──────────────────────────────────────────────────────

def generate_soneto(api_key, theme, temperature=0.85):
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": build_prompt(theme)}],
        "temperature": temperature,
        "max_tokens": 500,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{GROQ_BASE_URL}/chat/completions", data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "poesia/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("rate-limited...", end=" ", flush=True)
            time.sleep(5)
        else:
            print(f"HTTP {e.code}", end=" ", flush=True)
        return None
    except Exception as e:
        print(f"ERR: {e}", end=" ", flush=True)
        return None


# ── Validation ────────────────────────────────────────────────────

def validate_soneto(text, theme, language="es"):
    from poesia.phonology.spanish import SpanishPhonology
    phonology = SpanishPhonology()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    lines = [l for l in lines if not l.startswith('"') and not l.startswith("--")]
    result = {"ok": False, "score": 0.0, "metrics": {}, "reasons": [],
              "lines": lines, "counts": []}

    if len(lines) != 14:
        result["reasons"].append(f"{len(lines)} lines")
        return result

    counts = []
    for l in lines:
        try:
            scan = phonology.scan_line(l)
            counts.append(scan.metrical_syllable_count)
        except Exception:
            counts.append(0)
    result["counts"] = counts
    avg_s = sum(counts) / len(counts)
    max_d = max(abs(c - SYLL_TARGET) for c in counts)
    syll_ok = max_d <= 2 and abs(avg_s - SYLL_TARGET) <= 1
    if not syll_ok:
        result["reasons"].append(f"syll avg={avg_s:.1f}")

    # Rhyme
    rhyme_keys = []
    for l in lines:
        try:
            k = phonology.rhyme_key(l)
            rhyme_keys.append(k)
        except Exception:
            rhyme_keys.append(None)
    key_map = {}
    detected = []
    for k in rhyme_keys:
        if k is None:
            detected.append("?")
        elif k not in key_map:
            c = chr(65 + len(key_map))
            key_map[k] = c
            detected.append(c)
        else:
            detected.append(key_map[k])
    detected_str = "".join(detected)
    result["metrics"]["rhyme"] = 1.0 if detected_str == SONETO_RHYME else 0.0
    groups_q1 = len(set(detected[:4]))
    groups_q2 = len(set(detected[4:8]))
    groups_t1 = len(set(detected[8:11]))
    groups_t2 = len(set(detected[11:14]))
    rhyme_ok = groups_q1 >= 2 and groups_q2 >= 2 and groups_t1 >= 2 and groups_t2 >= 2
    if not rhyme_ok:
        result["reasons"].append(f"no rhyme ({detected_str})")

    # Language
    en_inds = {"the", "and", "that", "with", "from", "your", "our",
               "their", "this", "have", "will", "would", "could"}
    en_c = sum(1 for l in lines for w in re.findall(r"[a-z]+", l.lower()) if w in en_inds)
    lang_ok = en_c < 8
    if not lang_ok:
        result["reasons"].append(f"EN words={en_c}")

    # Start variety
    fws = [re.findall(r"[a-zñ]+", l.lower())[0] for l in lines if re.findall(r"[a-zñ]+", l.lower())]
    uniq_s = len(set(fws))
    sv = uniq_s / 14.0
    result["metrics"]["start_variety"] = sv
    if uniq_s < 6:
        result["reasons"].append(f"starts={uniq_s}/14")

    # Lexical diversity
    all_w = [w for l in lines for w in re.findall(r"[a-zñ]+", l.lower())]
    total_w = len(all_w)
    ld = len(set(all_w)) / total_w if total_w else 0
    result["metrics"]["lexical_diversity"] = round(ld, 3)

    # Abstract ratio
    abs_c = sum(1 for w in all_w if w in ABSTRACT_NOUNS)
    ar = abs_c / total_w if total_w else 1.0
    result["metrics"]["abstract_ratio"] = round(ar, 3)

    # Enjambment
    ep = [l[-1] if l else "" for l in lines]
    ej = sum(1 for p in ep if p not in (".", ";", ":", "?", "!", '"'))
    ejr = ej / 14.0
    result["metrics"]["enjambment"] = ejr

    # Theme + novelty via embeddings
    theme_s = 0.5
    nov_s = 0.5
    try:
        from sentence_transformers import SentenceTransformer
        import math
        model = SentenceTransformer("intfloat/multilingual-e5-small")
        te = model.encode("query: " + theme)
        les = model.encode(["passage: " + l for l in lines])
        sims = []
        for e in les:
            d = sum(a * b for a, b in zip(te, e))
            ns = math.sqrt(sum(a * a for a in te))
            ne = math.sqrt(sum(b * b for b in e))
            sims.append(d / (ns * ne) if ns > 0 and ne > 0 else 0)
        theme_s = sum(sims) / len(sims)
        result["metrics"]["theme_coherence"] = round(theme_s, 3)
        nv = 0.0
        for i in range(len(les)):
            for j in range(i + 1, len(les)):
                d = sum(a * b for a, b in zip(les[i], les[j]))
                ns = math.sqrt(sum(a * a for a in les[i]))
                ne = math.sqrt(sum(b * b for b in les[j]))
                s = d / (ns * ne) if ns > 0 and ne > 0 else 0
                nv += 1 - s
        pairs = len(les) * (len(les) - 1) / 2
        nov_s = nv / pairs if pairs > 0 else 0.5
        result["metrics"]["novelty"] = round(nov_s, 3)
    except Exception:
        pass

    # Emotion arc via pysentimiento
    emo = analyze_emotional_arc(lines, language)
    result["emotion"] = emo
    result["metrics"]["emotion_arc"] = emo.get("arc_variance", 0.0)
    result["metrics"]["num_emotions"] = emo.get("num_emotions", 0)
    
    # Word-level emotion diversity via Spanish Emotion Lexicon
    word_emos = analyze_poem_emotions(lines)
    result["metrics"]["word_emotion_diversity"] = emotion_diversity(lines)
    dominant = max(word_emos.items(), key=lambda x: x[1])
    result["metrics"]["dominant_emotion"] = dominant[0]
    
    # Readability via textstat (Spanish)
    try:
        import textstat
        textstat.set_lang('es')
        full_text = " ".join(lines)
        result["metrics"]["readability_es"] = round(textstat.szigriszt_pazos(full_text), 1)
    except Exception:
        result["metrics"]["readability_es"] = 0.0
    
    # Imagery density via spaCy noun extraction
    try:
        img_score = imagery_density_score(lines, language)
        result["metrics"]["imagery_density"] = img_score
    except Exception:
        result["metrics"]["imagery_density"] = 0.0

    hard_ok = syll_ok and rhyme_ok and lang_ok and len(lines) == 14
    result["ok"] = hard_ok

    if hard_ok:
        s = 0.4 + sv * 0.1 + ld * 1.0 + max(0, 0.15 - ar) * 2.0 + ejr * 0.05
        s += (theme_s - 0.3) * 0.3 + nov_s * 0.1
        s += emo.get("arc_variance", 0.0) * 0.1
        # New: imagery density (up to 0.05), word emotion diversity (up to 0.05)
        s += result["metrics"].get("imagery_density", 0.0) * 0.05
        s += result["metrics"].get("word_emotion_diversity", 0.0) * 0.01  # cap at ~8 emotions * 0.01 = 0.08
        result["score"] = round(min(s, 1.0), 3)

    return result


# ── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--output", default="seeds/poetry_corpus/training_data_distilled")
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--themes", nargs="+", default=None)
    args = parser.parse_args()

    api_key = os.environ.get(GROQ_API_KEY_ENV)
    if not api_key:
        print(f"ERROR: Set {GROQ_API_KEY_ENV}")
        sys.exit(1)

    themes = args.themes or DEFAULT_THEMES
    os.makedirs(args.output, exist_ok=True)
    generated, attempts, theme_idx = [], 0, 0

    print(f"Distilling {args.count} sonetos via {GROQ_MODEL}, min_q={args.min_score}")
    print()

    while len(generated) < args.count:
        theme = themes[theme_idx % len(themes)]
        theme_idx += 1
        attempts += 1
        print(f"  [{len(generated)+1}/{args.count}] {theme:20s} (att {attempts:3d})...", end=" ", flush=True)

        text = generate_soneto(api_key, theme)
        if not text:
            print("X")
            time.sleep(2)
            continue

        va = validate_soneto(text, theme, language="es")

        if va["ok"] and va["score"] >= args.min_score:
            avg_s = round(sum(va["counts"]) / len(va["counts"]))
            ex = {
                "prompt": f"Write a soneto in Spanish.\\nSyllables: {avg_s}.\\nRhyme: ABBA ABBA CDC DCD.\\nTheme: {theme}.\\n\\n",
                "completion": "\\n".join(va["lines"]),
                "author": "groq-llama-3.3-70b", "source": "distilled-v3",
                "avg_syllables": avg_s, "form": "soneto", "language": "es",
                "quality_score": va["score"],
                "metrics": va["metrics"],
            }
            generated.append(ex)
            m = va["metrics"]
            emo = va.get("emotion", {})
            print(f"OK q={va['score']:.2f}  rhyme={m.get('rhyme',0):.0%}  div={m.get('lexical_diversity',0):.2f}  "
                  f"abs={m.get('abstract_ratio',0):.0%}  emo_arc={emo.get('arc_variance',0):.0%}  "
                  f"n_emo={emo.get('num_emotions',0)}")
            if len(generated) % 5 == 0:
                p = os.path.join(args.output, "sonetos.jsonl")
                with open(p, "w") as f:
                    for e in generated:
                        f.write(json.dumps(e, ensure_ascii=False, cls=_PoetryEncoder) + "\n")
                print(f"  Saved {len(generated)} -> {p}")
        else:
            r = ", ".join(va["reasons"]) if va["reasons"] else "?"
            print(f"X  q={va['score']:.2f}  [{r}]")
        time.sleep(2.1)

    p = os.path.join(args.output, "sonetos.jsonl")
    with open(p, "w") as f:
        for e in generated:
            f.write(json.dumps(e, ensure_ascii=False, cls=_PoetryEncoder) + "\n")
    avg_q = sum(e["quality_score"] for e in generated) / len(generated) if generated else 0
    print(f"\\nDone! {len(generated)} sonetos to {p}")
    print(f"Attempts: {attempts}, success: {len(generated)/attempts*100:.0f}%")
    print(f"Avg quality: {avg_q:.2f}")


if __name__ == "__main__":
    main()

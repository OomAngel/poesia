#!/usr/bin/env python3
"""Pre-compute multi-dimensional quality scores for training examples.

Uses ALL available metrics:
- Line count accuracy
- Syllable accuracy (phonology)
- Rhyme scheme adherence (phonology.rhyme_key)
- Lexical diversity (unique / total words)
- Abstract noun ratio (emotion_lexicon word list)
- Emotion diversity (pysentimiento)
- Imagery density (spaCy noun extraction)
- Readability (textstat Spanish)

Usage:
    python scripts/score_training_data.py \
        --input data.jsonl --output scored.jsonl
"""

import argparse
import json
import re


def score_poem(completion, syll_target=11):
    """Score a poem 0-1 on ALL available quality metrics."""
    from poesia.evaluation.emotion_lexicon import emotion_diversity
    from poesia.galeria.imagery import imagery_density_score
    from poesia.phonology.spanish import SpanishPhonology

    lines = [l.strip() for l in completion.split("\n") if l.strip()]
    if not lines:
        return 0.0, {"line_count": 0, "error": "empty"}

    phonology = SpanishPhonology()
    breakdown = {}
    scores = []

    # 1. LINE COUNT: 14 is perfect for soneto
    line_ok = 1.0 if len(lines) == 14 else max(0.0, 1.0 - abs(14 - len(lines)) * 0.1)
    scores.append(line_ok * 0.15)
    breakdown["line_count"] = round(line_ok, 3)

    # 2. SYLLABLE COUNT: each line close to target
    syll_scores = []
    for l in lines:
        try:
            scan = phonology.scan_line(l)
            diff = abs(scan.metrical_syllable_count - syll_target)
            syll_scores.append(max(0.0, 1.0 - diff * 0.15))
        except Exception:
            syll_scores.append(0.0)
    syll_avg = sum(syll_scores) / len(syll_scores) if syll_scores else 0.0
    scores.append(syll_avg * 0.25)
    breakdown["syllable"] = round(syll_avg, 3)

    # 3. RHYME SCHEME: detect ABBA ABBA CDC DCD pattern
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
    # Score: 1.0 for exact match, 0.5 for plausible rhyme groups, 0 for none
    if detected_str == "ABBAABBACDCDCD":
        rhyme_score = 1.0
    elif len(set(detected[:4])) >= 2 and len(set(detected[8:])) >= 2:
        rhyme_score = 0.5
    else:
        rhyme_score = 0.0
    scores.append(rhyme_score * 0.15)
    breakdown["rhyme"] = round(rhyme_score, 3)

    # 4. LEXICAL DIVERSITY: unique / total word ratio
    all_words = [w for l in lines for w in re.findall(r"[a-z" + chr(241) + "]+", l.lower())]
    total = len(all_words)
    lex_div = len(set(all_words)) / total if total else 0
    # Normalize: typical range 0.3-0.8, scale to 0-1
    lex_score = min(lex_div * 1.5, 1.0)
    scores.append(lex_score * 0.1)
    breakdown["lexical_diversity"] = round(lex_div, 3)

    # 5. ABSTRACT NOUN RATIO: lower is better (more concrete)
    ABSTRACT_NOUNS = {
        "amor",
        "vida",
        "muerte",
        "alma",
        "corazon",
        "pasión",
        "dolor",
        "soledad",
        "tristeza",
        "esperanza",
        "miedo",
        "alegria",
        "pena",
        "silencio",
        "recuerdo",
        "olvido",
        "memoria",
        "ilusion",
        "duda",
        "fe",
        "paz",
        "guerra",
        "odio",
        "ternura",
        "ira",
        "calma",
        "angustia",
        "ansiedad",
        "melancolia",
        "nostalgia",
        "dicha",
        "suerte",
        "destino",
        "fortuna",
        "gloria",
        "infierno",
        "cielo",
    }
    abs_count = sum(1 for w in all_words if w in ABSTRACT_NOUNS)
    abs_ratio = abs_count / total if total else 1.0
    abs_score = max(0.0, 1.0 - abs_ratio * 3)  # Penalize if >33% abstract
    scores.append(abs_score * 0.10)
    breakdown["abstract_ratio"] = round(abs_ratio, 3)

    # 6. EMOTION DIVERSITY: more emotions = richer poem
    try:
        emo_div = emotion_diversity(lines)
        emo_score = min(emo_div / 6.0, 1.0)  # 6 emotions max
    except Exception:
        emo_score = 0.0
    scores.append(emo_score * 0.10)
    breakdown["emotion_diversity"] = round(emo_score, 3)

    # 7. IMAGERY DENSITY: concrete nouns vs total words
    try:
        img_score = imagery_density_score(lines, language="es")
    except Exception:
        img_score = 0.0
    scores.append(img_score * 0.10)
    breakdown["imagery"] = round(img_score, 3)

    # 8. READABILITY: Spanish textstat
    try:
        import textstat

        textstat.set_lang("es")
        full_text = " ".join(lines)
        readability = textstat.szigriszt_pazos(full_text)
        # Normalize: typical range 60-120 for poetry, score 0-1
        read_score = max(0.0, min((readability - 40) / 80, 1.0))
    except Exception:
        read_score = 0.5
    scores.append(read_score * 0.05)
    breakdown["readability"] = round(read_score, 3)

    total_score = round(min(sum(scores), 1.0), 3)
    return total_score, breakdown


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", type=int, default=11)
    args = parser.parse_args()

    total = 0
    with open(args.input) as fin, open(args.output, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            total += 1
            quality, breakdown = score_poem(record.get("completion", ""), args.target)
            record["quality_score"] = quality
            record["quality_breakdown"] = breakdown
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Scored {total} poems with full metric suite")
    print("Metrics: syllable, rhyme, lexical diversity, abstract ratio,")
    print("         emotion diversity, imagery density, readability")


if __name__ == "__main__":
    main()

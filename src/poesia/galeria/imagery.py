"""Imagery extraction from poems."""

from __future__ import annotations

import re

_SENSORY_MAP = {
    # Visual
    "luz": "visual",
    "sol": "visual",
    "luna": "visual",
    "estrella": "visual",
    "brillo": "visual",
    "color": "visual",
    "rojo": "visual",
    "azul": "visual",
    "verde": "visual",
    "blanco": "visual",
    "negro": "visual",
    "nube": "visual",
    "cielo": "visual",
    "sombra": "visual",
    "rayo": "visual",
    "relampago": "visual",
    "arcoiris": "visual",
    "llama": "visual",
    "fuego": "visual",
    # Auditory
    "sonido": "auditory",
    "ruido": "auditory",
    "viento": "auditory",
    "canto": "auditory",
    "grito": "auditory",
    "susurro": "auditory",
    "silbido": "auditory",
    "trueno": "auditory",
    "eco": "auditory",
    "llanto": "auditory",
    "risa": "auditory",
    "musica": "auditory",
    "campana": "auditory",
    "silencio": "auditory",
    # Tactile
    "mano": "tactile",
    "piel": "tactile",
    "caricia": "tactile",
    "calor": "tactile",
    "frio": "tactile",
    "suave": "tactile",
    "aspero": "tactile",
    "espina": "tactile",
    "piedra": "tactile",
    "arena": "tactile",
    "agua": "tactile",
    # Olfactory
    "olor": "olfactory",
    "aroma": "olfactory",
    "perfume": "olfactory",
    "fragancia": "olfactory",
    "hedor": "olfactory",
    "flor": "olfactory",
    "jazmin": "olfactory",
    "rosa": "olfactory",
    # Gustatory
    "sabor": "gustatory",
    "dulce": "gustatory",
    "salado": "gustatory",
    "amargo": "gustatory",
    "miel": "gustatory",
    "vino": "gustatory",
}


def _get_spacy(language="es"):
    import spacy

    model = "es_core_news_sm" if language == "es" else "en_core_web_sm"
    try:
        return spacy.load(model)
    except OSError:
        import subprocess
        import sys

        subprocess.run([sys.executable, "-m", "spacy", "download", model], check=True)  # noqa: S603 - pip-style trusted call
        return spacy.load(model)


def extract_imagery(lines, language="es"):
    """Extract concrete imagery from poem lines."""
    nlp = _get_spacy(language)
    text = "\n".join(lines)
    doc = nlp(text)

    nouns = [t.text.lower() for t in doc if t.pos_ == "NOUN" and t.is_alpha]
    adjectives = [t.text.lower() for t in doc if t.pos_ == "ADJ" and t.is_alpha]
    phrases = []
    for chunk in doc.noun_chunks:
        p = chunk.text.strip().lower()
        ws = p.split()
        if len(ws) <= 4 and p not in phrases:
            phrases.append(p)

    words_lower = set(re.findall(r"[a-z" + chr(241) + "]+", text.lower()))
    senses = set()
    for word, sense in _SENSORY_MAP.items():
        if word in words_lower:
            senses.add(sense)

    all_w = [t.text.lower() for t in doc if t.is_alpha]
    density = round(len(nouns) / len(all_w), 3) if all_w else 0.0

    return {
        "nouns": sorted(set(nouns)),
        "phrases": phrases[:10],
        "adjectives": sorted(set(adjectives)),
        "sensory_modalities": sorted(senses),
        "imagery_density": density,
    }


def build_image_prompt(imagery, theme="", style=None):
    """Build image generation prompt from extracted imagery."""
    parts = [theme] if theme else []
    if imagery["phrases"]:
        parts.extend(sorted(imagery["phrases"], key=len, reverse=True)[:4])
    elif imagery["nouns"]:
        parts.extend(imagery["nouns"][:5])
    prompt = ". ".join(p.capitalize() for p in parts)
    return f"{prompt}, estilo {style}" if style else prompt


def imagery_density_score(lines, language="es"):
    """Score 0-1 for imagery richness."""
    img = extract_imagery(lines, language)
    s = min(img["imagery_density"] * 5, 0.5)
    s += min(len(img["sensory_modalities"]) * 0.06, 0.3)
    s += min(len(img["phrases"]) * 0.02, 0.2)
    return round(s, 3)

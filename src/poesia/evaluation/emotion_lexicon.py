"""Spanish Emotion Lexicon — word-level emotion associations.

Based on NRC Emotion Lexicon categories (anger, fear, trust, surprise,
sadness, joy, disgust, anticipation). Each entry maps a Spanish word
to its associated emotion(s).

Usage:
    from poesia.evaluation.emotion_lexicon import get_word_emotions, analyze_poem_emotions

    emotions = get_word_emotions("muerte")  # -> {"fear", "sadness"}
    poem_emotions = analyze_poem_emotions(["linea 1...", "linea 2..."])
    # -> {"joy": 0.3, "sadness": 0.5, ...}
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

# Emotion categories (matching NRC)
EMOTIONS = ["anger", "fear", "trust", "surprise", "sadness", "joy", "disgust", "anticipation"]

# Load lexicon
_LEXICON_PATH = Path(__file__).parent.parent.parent.parent / "data" / "emotion_lexicon_es.json"

_lexicon: dict[str, list[str]] | None = None


def _load_lexicon() -> dict[str, list[str]]:
    global _lexicon
    if _lexicon is not None:
        return _lexicon
    if _LEXICON_PATH.exists():
        with open(_LEXICON_PATH) as f:
            _lexicon = json.load(f)
    else:
        _lexicon = {}
    return _lexicon


def get_word_emotions(word: str) -> set[str]:
    """Get emotion associations for a single word.

    Args:
        word: Spanish word (case-insensitive).

    Returns:
        Set of emotion labels (e.g., {"joy", "trust"}).
    """
    lexicon = _load_lexicon()
    return set(lexicon.get(word.lower(), []))


def analyze_poem_emotions(lines: list[str]) -> dict[str, float]:
    """Analyze word-level emotion distribution across a poem.

    Args:
        lines: List of poem lines.

    Returns:
        Dict mapping emotion -> proportion of emotional words with that emotion.
    """
    lexicon = _load_lexicon()
    word_emotions: Counter = Counter()
    total_emotional = 0

    for line in lines:
        words = re.findall(r"[a-záéíóúüñ]+", line.lower())
        for w in words:
            emos = lexicon.get(w, [])
            if emos:
                total_emotional += 1
                for e in emos:
                    word_emotions[e] += 1

    if total_emotional == 0:
        return {e: 0.0 for e in EMOTIONS}

    return {e: round(word_emotions.get(e, 0) / total_emotional, 3) for e in EMOTIONS}


def dominant_emotion(lines: list[str]) -> tuple[str, float]:
    """Get the dominant emotion in a poem.

    Returns:
        (emotion_label, proportion) e.g. ("sadness", 0.42).
    """
    dist = analyze_poem_emotions(lines)
    dominant = max(dist.items(), key=lambda x: x[1])
    return dominant


def emotion_diversity(lines: list[str]) -> float:
    """How many different emotions appear above threshold (0.1).

    Returns:
        Count of emotions present (1.0 = monotone, 8.0 = fully varied).
    """
    dist = analyze_poem_emotions(lines)
    return sum(1 for v in dist.values() if v >= 0.1)

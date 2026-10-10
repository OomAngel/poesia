"""Spanish metrical count with licences (poesia.phonology.spanish_metre)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fonemas")

from poesia.phonology.spanish_metre import metrical_counts  # noqa: E402

GOLD = Path("seeds/poetry_corpus/eval_gold/adso_gold_100.jsonl")


@pytest.mark.parametrize(
    ("line", "best"),
    [
        ("tú, a quien los ojos dieron la bebida", 11),  # "los o-" stays apart (old rule: 10)
        ("vive seguro de que eternamente", 11),  # -mente ends on its "men" stress
        ("las alas rojas mueve dulcemente", 11),
        ("Ya se fue la Calavera", 8),  # "ya" starts with a consonant
        ("Que en Morelos fué fatal", 8),  # old spelling "fué" is one syllable, oxytone end
        ("tuerces soberbio, raudo y espumoso", 11),  # "y" joins one side only
        ("Andaba la Calavera", 8),
        ("mas Lupita no venía", 8),
    ],
)
def test_best_count(line: str, best: int) -> None:
    assert metrical_counts(line)[0] == best


def test_licences_widen_the_set() -> None:
    # dieresis: "su-a-ve" (Garcilaso) is 11 with the split diphthong
    best, licensed = metrical_counts("Este suave incendio me sustenta")
    assert best == 10 and 11 in licensed
    # dialefa before a stressed vowel: "mi | alma" kept apart
    best, licensed = metrical_counts("cuando imprimí en mi alma la figura")
    assert 11 in licensed


@pytest.mark.skipif(not GOLD.exists(), reason="ADSO gold set is DVC/local data")
def test_adso_regression() -> None:
    """Held-out half (sonnets 51-100): 93.8% exact, 99.7% in the licensed set (2026-10-10)."""
    rows = [json.loads(x) for x in GOLD.open(encoding="utf-8")][50:]
    n = exact = inset = 0
    for r in rows:
        verses = [v for v in r["completion"].split("\n") if v.strip()]
        for v, met in zip(verses, r.get("metre", []), strict=False):
            if not met:
                continue
            gold = len(met.replace("|", ""))
            best, licensed = metrical_counts(v)
            n += 1
            exact += best == gold
            inset += gold in licensed
    assert exact / n >= 0.90 and inset / n >= 0.98

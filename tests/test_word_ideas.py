"""Rhyme words first (poesia.word_ideas, /api/words): small, offline suggestions (plan U6)."""

from __future__ import annotations

import pytest

from poesia.word_ideas import _italian_stress_is_certain, rhyme_words

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from poesia.webapp import create_app  # noqa: E402

# (language, form, first line, index of a line that rhymes with line 1)
CASES = [
    ("es", "soneto", "La luna vierte su silencio en el mar", 3),
    ("en", "sonnet_shakespearean", "The restless sea in endless rhythm rolls", 2),
    ("it", "sonetto", "il mare che respira nella sera", 3),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(llm=object()))


@pytest.mark.parametrize(("language", "form", "first", "index"), CASES)
def test_every_offered_word_passes_the_pages_rhyme_check(client, language, form, first, index):
    lines = [first] + [""] * index
    r = client.post(
        "/api/words", json={"language": language, "form": form, "index": index, "lines": lines}
    ).json()
    assert r["partner"] == 0 and len(r["words"]) >= 5
    for w in r["words"]:
        line = f"{'y' if language == 'es' else 'and' if language == 'en' else 'e'} {w['word']}"
        scan = client.post(
            "/api/scan",
            json={
                "language": language,
                "form": form,
                "index": index,
                "lines": [*lines[:index], line],
            },
        ).json()
        assert scan["rhymes"] is True, (w["word"], scan["rhyme_key"])


def test_a_word_that_does_not_rhyme_fails_the_same_check(client):
    # Positive control for the test above: the check can say no.
    lines = ["La luna vierte su silencio en el mar", "", "", "y la noche"]
    scan = client.post(
        "/api/scan", json={"language": "es", "form": "soneto", "index": 3, "lines": lines}
    ).json()
    assert scan["rhymes"] is False


def test_first_line_of_a_rhyme_and_free_verse_say_why_there_are_no_words(client):
    first = client.post(
        "/api/words", json={"language": "es", "form": "soneto", "index": 0, "lines": [""]}
    ).json()
    assert first == {"words": [], "partner": None, "reason": "first"}
    free = client.post(
        "/api/words", json={"language": "en", "form": "free", "index": 2, "lines": ["a", "b", ""]}
    ).json()
    assert free["reason"] == "free"
    empty = client.post(
        "/api/words",
        json={"language": "es", "form": "soneto", "index": 3, "lines": ["", "", "", ""]},
    ).json()
    assert empty["reason"] == "partner_empty" and empty["partner"] == 0


def test_words_already_ending_a_line_are_not_offered():
    first = "La luna vierte su silencio en el mar"
    offered = [w["word"] for w in rhyme_words("es", first)]
    again = [w["word"] for w in rhyme_words("es", first, avoid={offered[0]})]
    assert offered[0] not in again and "mar" not in offered


def test_italian_never_offers_an_unmarked_third_to_last_stress():
    # crèscita, pèrdita, òpera look like partìta, manièra without a dictionary.
    words = {w["word"] for w in rhyme_words("it", "Nel mezzo del cammin di nostra vita", k=40)}
    words |= {w["word"] for w in rhyme_words("it", "il mare che respira nella sera", k=40)}
    assert not words & {"crescita", "perdita", "vendita", "nascita", "opera", "camera", "lettera"}
    assert _italian_stress_is_certain("bellezza", 3) and not _italian_stress_is_certain(
        "crescita", 3
    )
    assert _italian_stress_is_certain("città", 2) and not _italian_stress_is_certain("tenebre", 3)


def test_each_word_says_why_in_the_poems_language():
    (es,) = rhyme_words("es", "La luna vierte su silencio en el mar", k=1)
    assert es["why"].startswith("rima con «mar»") and "sílaba" in es["why"]
    (en,) = rhyme_words("en", "I wandered lonely as a cloud", k=1)
    assert en["why"].startswith("rhymes with “cloud”")

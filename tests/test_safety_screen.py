"""Safety screen: phrases per language, the model question, and the page endpoint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from poesia.safety import RESOURCES, keyword_matches, screen

DATA = Path(__file__).resolve().parent.parent / "data" / "safety" / "safety_reflections.jsonl"


class _Model:
    model = "fake"

    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        self.prompts.append(prompt)
        if isinstance(self.answer, Exception):
            raise self.answer
        return [self.answer]


@pytest.mark.parametrize(
    "text",
    [
        "Últimamente no quiero despertar.",
        "I've been thinking about killing myself.",
        "Ich will mir das Leben nehmen.",
        "Je pense à en finir.",
        "Voglio farla finita.",
        "SUICIDIO",
    ],
)
def test_phrases_flag_risk_in_every_language(text: str) -> None:
    assert keyword_matches(text)


@pytest.mark.parametrize(
    "text",
    [
        "Mi padre murió en marzo y las hojas caen.",
        "Autumn always feels like a small death.",
        "Der Herbst fühlt sich wie ein kleiner Tod an.",
        "I could die laughing at that dog.",
    ],
)
def test_grief_and_figures_of_speech_are_not_flagged(text: str) -> None:
    assert not keyword_matches(text)


def test_model_yes_flags_even_without_a_phrase() -> None:
    result = screen("I can't see myself here next spring.", llm=_Model("YES"))
    assert result.flagged and result.model_says is True and not result.matched
    assert result.resources == RESOURCES


def test_model_outage_falls_back_to_phrases() -> None:
    assert screen("quiero morir", llm=_Model(RuntimeError("offline"))).flagged
    assert not screen("las hojas caen", llm=_Model(RuntimeError("offline"))).flagged


def test_reflection_reaches_the_model_inside_markers() -> None:
    model = _Model("NO")
    assert not screen("the lake was still", llm=model).flagged
    assert "<<<\nthe lake was still\n>>>" in model.prompts[0]


def test_test_set_is_balanced_and_phrases_raise_no_false_alarms() -> None:
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 60
    assert sum(r["risk"] for r in rows) == 20
    assert {r["language"] for r in rows} == {"es", "en", "de", "fr", "it"}
    assert not [r["id"] for r in rows if not r["risk"] and keyword_matches(r["text"])]


def test_page_endpoint_returns_resources_only_when_flagged() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from poesia.webapp import create_app

    client = TestClient(create_app(llm=_Model("NO")))
    calm = client.post("/api/safety", json={"text": "the chestnut tree turned gold"}).json()
    assert calm == {"flagged": False, "resources": []}
    risk = client.post("/api/safety", json={"text": "no quiero seguir viviendo"}).json()
    assert risk["flagged"] and risk["resources"][0]["number"] == "143"


def test_helplines_follow_the_page_language_with_the_same_facts():
    # U9: a pause shown in Spanish or Italian must not switch to English.
    from poesia.safety.screen import RESOURCES_BY_LANGUAGE, resources_for

    en = RESOURCES_BY_LANGUAGE["en"]
    for lang in ("es", "it"):
        loc = resources_for(lang)
        assert [r["number"] for r in loc] == [r["number"] for r in en]
        assert all(a["note"] != b["note"] for a, b in zip(loc, en, strict=True))
        assert all("0800 143 000" in r["note"] for r in loc[:1])  # the English line kept
    assert resources_for("de") == en  # not translated yet: English, never empty


def test_safety_endpoint_answers_in_the_requested_language():
    import pytest

    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from poesia.webapp import create_app

    client = TestClient(create_app(llm=object()))
    r = client.post(
        "/api/safety",
        json={
            "text": "Últimamente no quiero despertar. Todos estarían mejor sin mí.",
            "language": "es",
        },
    ).json()
    assert r["flagged"] and r["resources"][0]["note"].startswith("Siempre disponible")
    calm = client.post("/api/safety", json={"text": "el mar en otoño", "language": "es"}).json()
    assert calm == {"flagged": False, "resources": []}

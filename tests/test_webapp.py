"""The local writing page (poesia.webapp): deterministic checks, ranked proposals, no storage."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from poesia.webapp import create_app


class _FakeLLM:
    model = "fake"

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.prompts: list[str] = []

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        self.prompts.append(prompt)
        return self.lines[:n]

    def repair(self, line: str, defect_description: str) -> str:
        return line


def _client(lines: list[str] | None = None) -> tuple[TestClient, _FakeLLM]:
    llm = _FakeLLM(lines or [])
    return TestClient(create_app(llm=llm)), llm


def test_page_and_forms_are_served() -> None:
    client, _ = _client()
    assert "<title>PoesIA</title>" in client.get("/").text
    forms = {(f["language"], f["form"]): f for f in client.get("/api/forms").json()}
    assert forms[("es", "soneto")]["lines"] == 14
    assert forms[("es", "soneto")]["syllables"][0] == 11
    assert forms[("en", "sonnet_shakespearean")]["scheme"] == "ABABCDCDEFEFGG"


def test_scan_counts_and_explains_a_short_line() -> None:
    client, _ = _client()
    r = client.post(
        "/api/scan", json={"language": "es", "form": "soneto", "index": 0, "lines": ["La luna"]}
    ).json()
    assert r["target"] == 11
    assert r["syllables"] < 11
    assert r["status"] == "short"
    assert r["messages"]


def test_scan_flags_a_broken_rhyme_with_its_partner() -> None:
    client, _ = _client()
    lines = [
        "The restless waves are breaking on the shore",
        "",
        "The gulls are crying high above the sand",
    ]
    r = client.post(
        "/api/scan",
        json={"language": "en", "form": "sonnet_shakespearean", "index": 2, "lines": lines},
    ).json()
    assert r["rhyme_letter"] == "A" and r["rhyme_partner"] == 0
    assert r["rhymes"] is False
    assert any("line 1" in m for m in r["messages"])


def test_unknown_form_is_rejected() -> None:
    client, _ = _client()
    r = client.post(
        "/api/scan", json={"language": "es", "form": "sonnet_shakespearean", "index": 0}
    )
    assert r.status_code == 400


def test_proposals_are_ranked_by_the_scan_and_fragments_dropped() -> None:
    client, llm = _client(
        [
            "more",  # a bare rhyme word: dropped
            "And all the long grey morning, nothing more",  # 10 syllables, rhymes with shore
            "The wind",  # fragment: dropped
            "And far away the tired sailors sing their weary songs",  # far too long
        ]
    )
    lines = [
        "The restless waves are breaking on the shore",
        "Above the cliffs the gulls are wheeling white",
    ]
    r = client.post(
        "/api/propose",
        json={"language": "en", "form": "sonnet_shakespearean", "index": 2, "lines": lines, "n": 3},
    ).json()
    texts = [p["text"] for p in r["proposals"]]
    assert texts[0] == "And all the long grey morning, nothing more"
    assert "more" not in texts and "The wind" not in texts
    assert 'rhymes with "shore"' in llm.prompts[0]


def test_reflection_reaches_the_prompt_but_is_capped() -> None:
    client, llm = _client(["Under the copper leaves I count the hours"])
    client.post(
        "/api/propose",
        json={
            "language": "en",
            "form": "sonnet_shakespearean",
            "index": 0,
            "lines": [],
            "theme": "autumn tree",
            "reflection": "x" * 4000,
        },
    )
    assert "autumn tree" in llm.prompts[0]
    assert "x" * 400 in llm.prompts[0] and "x" * 401 not in llm.prompts[0]


def test_model_failure_is_a_503_not_a_crash() -> None:
    class _Down(_FakeLLM):
        def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
            raise RuntimeError("ollama offline")

    client = TestClient(create_app(llm=_Down([])))
    r = client.post("/api/propose", json={"language": "es", "form": "soneto", "index": 0})
    assert r.status_code == 503


def test_readback_returns_wav_or_a_clear_503(monkeypatch) -> None:
    import poesia.webapp as webapp

    client, _ = _client()
    monkeypatch.setattr(webapp, "read_aloud", lambda text, language: b"RIFF....WAVEfmt ")
    r = client.post("/api/readback", json={"language": "es", "text": "La luna vierte su silencio"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"

    def _missing(text: str, language: str) -> bytes:
        raise FileNotFoundError("voice not installed")

    monkeypatch.setattr(webapp, "read_aloud", _missing)
    r = client.post("/api/readback", json={"language": "en", "text": "a line"})
    assert r.status_code == 503 and "voice not installed" in r.json()["detail"]

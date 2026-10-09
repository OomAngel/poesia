"""The local writing page (poesia.webapp): deterministic checks, ranked proposals, no storage."""

from __future__ import annotations

import os

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


def test_italian_sonetto_is_offered_and_scanned() -> None:
    client, _ = _client()
    forms = {(f["language"], f["form"]): f for f in client.get("/api/forms").json()}
    assert forms[("it", "sonetto")]["syllables"][0] == 11
    r = client.post(
        "/api/scan",
        json={
            "language": "it",
            "form": "sonetto",
            "index": 0,
            "lines": ["Nel mezzo del cammin di nostra vita"],
        },
    ).json()
    assert r["syllables"] == 11 and r["status"] == "ok"


def test_free_verse_scans_without_targets_and_proposes() -> None:
    client, llm = _client(["the river keeps the colour of the leaves"])
    forms = {(f["language"], f["form"]): f for f in client.get("/api/forms").json()}
    assert forms[("en", "free")]["free"] and forms[("en", "free")]["scheme"] == ""
    assert forms[("es", "soneto")]["stanzas"] == [4, 4, 3, 3]
    r = client.post(
        "/api/scan",
        json={"language": "en", "form": "free", "index": 3, "lines": ["", "", "", "a b c"]},
    ).json()
    assert r["target"] is None and r["rhyme_letter"] == "" and r["rhymes"] is None
    p = client.post("/api/propose", json={"language": "en", "form": "free", "index": 0}).json()
    assert p["proposals"][0]["text"] == "the river keeps the colour of the leaves"
    assert "Exactly" not in llm.prompts[0]


def test_lessons_follow_the_page_language() -> None:
    client, _ = _client()
    r = client.post(
        "/api/scan", json={"language": "es", "form": "soneto", "index": 0, "lines": ["La luna"]}
    ).json()
    assert r["messages"][0].startswith("Faltan")


def test_scan_returns_the_syllable_view() -> None:
    client, _ = _client()
    r = client.post(
        "/api/scan",
        json={
            "language": "es",
            "form": "soneto",
            "index": 0,
            "lines": ["La luna ilumina la noche serena"],
        },
    ).json()
    words = r["view"]
    assert [s["t"] for s in words[1]["syl"]] == ["lu", "na"] and words[1][
        "join"
    ] is True  # luna‿ilumina
    assert any(s["s"] for s in words[2]["syl"])  # a stressed syllable is marked


def test_a_line_in_another_language_gets_a_hint() -> None:
    client, _ = _client()
    r = client.post(
        "/api/scan",
        json={
            "language": "es",
            "form": "soneto",
            "index": 0,
            "lines": ["The chestnut drops its leaves along the lane"],
        },
    ).json()
    assert r["other_language"] == "en"
    assert r["messages"][0].startswith("Este verso parece estar en inglés")
    ok = client.post(
        "/api/scan",
        json={
            "language": "es",
            "form": "soneto",
            "index": 0,
            "lines": ["La luna vierte su silencio blanco"],
        },
    ).json()
    assert ok["other_language"] is None


def test_with_ollama_says_how_to_install_when_none_runs(monkeypatch):
    from poesia import webapp

    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    with pytest.raises(SystemExit, match="Install the Ollama app"):
        webapp._use_local_ollama("http://127.0.0.1:9")  # discard port: nothing listens
    assert "LLM_BASE_URL" not in os.environ


def test_proposals_in_another_language_come_last() -> None:
    # Apertus slips into English in German, French and Italian sonnets (2026-10-09 benchmark);
    # an English line that happens to scan must not be offered first.
    client, _ = _client(
        [
            "Bright delight gleams on the silent sea",  # English, and the German counter says 10
            "Ein stiller Zauber zieht durch jede Nacht",  # German, 10 to the last stress
        ]
    )
    r = client.post(
        "/api/propose",
        json={"language": "de", "form": "sonett", "index": 0, "lines": [], "n": 2},
    ).json()
    texts = [p["text"] for p in r["proposals"]]
    assert texts[0] == "Ein stiller Zauber zieht durch jede Nacht"
    assert texts[-1].startswith("Bright")

"""Calaveritas web app: pages, the poem API, rate limits, reports and the scoped auto-pause."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from poesia import calaveritas_web  # noqa: E402
from poesia.calaveritas import generator, service  # noqa: E402
from poesia.phonology.base import ScanResult

GOOD = (
    "Andaba la Calavera\nbuscando a Lupita un día\npor pasillo y escalera,\nmas nadie le respondía."
)


class Fake(generator.Provider):
    def __init__(self):
        super().__init__("Apertus · test", "http://x", "m", "", True)
        self.calls = 0

    def chat(self, msgs, temperature=0.9, max_tokens=160):
        self.calls += 1
        return GOOD


def body(**kw):
    b = {
        "language": "es",
        "name": "Lupita",
        "recipient": "amistad",
        "tone": "picara",
        "stanzas": 1,
        "traits": ["tarde"],
        "detail": "",
        "birth_year": 1990,
    }
    b.update(kw)
    return b


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        generator, "scan", lambda line, lang: ScanResult(line=line, metrical_syllable_count=8)
    )
    monkeypatch.delenv("CALAVERITAS_PAUSE_RISKY", raising=False)
    return TestClient(calaveritas_web.create_app(providers=[Fake()]))


def test_pages_and_headers(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/es/"
    es, en = client.get("/es/"), client.get("/en/")
    assert '<html lang="es">' in es.text and '<html lang="en">' in en.text
    csp = es.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "fonts.googleapis" not in csp
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/fonts/fonts.css").status_code == 200
    assert client.get("/healthz").json()["status"] == "ok"


def test_writes_a_poem(client):
    r = client.post("/api/calaverita", json=body())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] and d["poem"]["stanzas"][0]["lines"][0] == "Andaba la Calavera"
    assert d["poem"]["model"] == "Apertus · test"
    assert r.headers["cache-control"] == "no-store"


def test_rejections_carry_a_message_in_the_page_language(client):
    r = client.post("/api/calaverita", json=body(language="en", detail="call 55 1234 5678"))
    assert r.status_code == 400 and r.json()["code"] == "personal_data"
    assert "phone" in r.json()["message"]
    r = client.post(
        "/api/calaverita", content=b"x" * 5000, headers={"content-type": "application/json"}
    )
    assert r.status_code == 413


def test_rate_limit(monkeypatch, client):
    for _ in range(5):
        assert client.post("/api/calaverita", json=body()).status_code == 200
    r = client.post("/api/calaverita", json=body())
    assert r.status_code == 429 and r.json()["code"] == "rate_client"


def test_reports_pause_only_risky_paths(monkeypatch):
    monkeypatch.setattr(
        generator, "scan", lambda line, lang: ScanResult(line=line, metrical_syllable_count=8)
    )
    sent = []
    monkeypatch.setattr(
        calaveritas_web, "send_github_issue", lambda t, b, labels: sent.append(labels) or True
    )
    c = TestClient(calaveritas_web.create_app(providers=[Fake()]))
    for _ in range(3):
        assert c.post(
            "/api/report", json={"language": "es", "poem": "texto", "reason": "ofende"}
        ).json()["ok"]
    assert ["auto-pause"] in sent
    assert c.post("/api/calaverita", json=body(recipient="trabajo")).status_code == 503
    assert (
        c.post("/api/calaverita", json=body(recipient="mascota", name="Firulais")).status_code
        == 200
    )
    assert (
        c.post(
            "/api/calaverita", json=body(recipient="mascota", name="Firulais", detail="ladra")
        ).status_code
        == 503
    )


def test_report_without_channel_says_so(monkeypatch, client):
    monkeypatch.delenv("CALAVERITAS_GITHUB_REPO", raising=False)
    r = client.post("/api/report", json={"language": "en", "poem": "text"})
    assert r.status_code == 503 and r.json()["code"] == "report_unavailable"


def test_rate_limiter_unit():
    rl = service.RateLimiter(
        service.Limits(per_client_window=2, per_client_day=3, global_day=4, window_s=10)
    )
    assert rl.check("a", 0) is None and rl.check("a", 1) is None
    assert rl.check("a", 2) == "client"
    assert rl.check("a", 20) is None  # window passed
    assert rl.check("a", 40) == "client"  # daily cap of 3
    assert rl.check("b", 40) is None
    assert rl.check("c", 40) == "global"


def test_model_health_reports_a_dead_model(monkeypatch):
    from poesia.calaveritas.service import ModelWatch

    class Dead(generator.Provider):
        def __init__(self):
            super().__init__("x", "http://127.0.0.1:9/v1", "m", "k", True)

        def chat(self, msgs, temperature=0.9, max_tokens=160):
            raise OSError("down")

    c = TestClient(calaveritas_web.create_app(providers=[Dead()]))
    r = c.get("/healthz/model")
    assert r.status_code == 503 and r.json()["model"] == "down"
    assert c.get("/healthz").status_code == 200  # the app itself is fine
    w = ModelWatch([Dead()], ttl=600)
    w.record(True, "a request was answered")
    assert w.status() == (True, "a request was answered")  # fresh result, no new probe

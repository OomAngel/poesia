"""First-run model setup through Ollama's API (poesia.model_setup)."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

from poesia.model_setup import ModelSpec, OllamaSetup


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_ollama(present: list[str], calls: list[tuple[str, dict]]):
    def urlopen(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        if url.endswith("/api/tags"):
            return _Resp(json.dumps({"models": [{"name": n} for n in present]}).encode())
        body = json.loads(req.data)
        calls.append((url.rsplit("/", 1)[-1], body))
        if url.endswith("/api/pull"):
            events = [{"status": "pulling", "total": 100, "completed": 40}, {"status": "success"}]
            return _Resp(b"\n".join(json.dumps(e).encode() for e in events))
        return _Resp(b"{}")

    return urlopen


def _specs() -> list[ModelSpec]:
    return [
        ModelSpec(
            name="poesia-apertus",
            source="hf.co/x/y:Q4",
            template="T",
            parameters={"num_ctx": 4096},
            warm=True,
            label="poetry",
        ),
        ModelSpec(name="poesia-embed", source="bge-m3", parameters={"num_gpu": 0}, label="linking"),
    ]


def test_fresh_server_pulls_creates_and_warms() -> None:
    calls: list[tuple[str, dict]] = []
    setup = OllamaSetup("http://ollama:11434", _specs())
    with patch("urllib.request.urlopen", _fake_ollama([], calls)):
        status = setup.ensure()
    assert status.phase == "ready"
    assert [c[0] for c in calls] == ["pull", "create", "generate", "pull", "create"]
    create = calls[1][1]
    assert (
        create["model"] == "poesia-apertus"
        and create["from"] == "hf.co/x/y:Q4"
        and create["template"] == "T"
    )
    assert calls[4][1]["parameters"] == {"num_gpu": 0}


def test_ready_server_only_warms() -> None:
    calls: list[tuple[str, dict]] = []
    setup = OllamaSetup("http://ollama:11434", _specs())
    with patch(
        "urllib.request.urlopen",
        _fake_ollama(["poesia-apertus:latest", "poesia-embed:latest"], calls),
    ):
        assert setup.ensure().phase == "ready"
    assert [c[0] for c in calls] == ["generate"]


def test_unreachable_server_reports_error_without_raising() -> None:
    import urllib.error

    setup = OllamaSetup("http://nowhere:1", _specs())
    with patch("urllib.request.urlopen", MagicMock(side_effect=urllib.error.URLError("refused"))):
        status = setup.ensure()
    assert status.phase == "error" and "refused" in status.error


def test_status_endpoint_reports_setup_progress() -> None:
    import pytest

    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from poesia.webapp import create_app

    class _LLM:
        model = "fake"

        def generate(self, prompt, n=1, temperature=0.9):
            return ["x"]

    setup = OllamaSetup("http://ollama:11434", _specs())
    setup.status.phase, setup.status.model, setup.status.completed, setup.status.total = (
        "downloading",
        "poetry",
        2,
        5,
    )
    client = TestClient(create_app(llm=_LLM(), setup=setup))
    assert client.get("/api/status").json() == {
        "phase": "downloading",
        "model": "poetry",
        "completed": 2,
        "total": 5,
        "error": "",
    }
    assert TestClient(create_app(llm=_LLM())).get("/api/status").json() == {"phase": "ready"}


def test_gpu_fraction_reads_ollama_ps() -> None:
    setup = OllamaSetup("http://ollama:11434", _specs())
    ps = {
        "models": [
            {"name": "poesia-apertus:latest", "size": 1000, "size_vram": 890},
            {"name": "poesia-embed:latest", "size": 10, "size_vram": 0},
        ]
    }
    with patch("urllib.request.urlopen", lambda url, timeout=None: _Resp(json.dumps(ps).encode())):
        assert setup.gpu_fraction() == 0.89
    with patch("urllib.request.urlopen", lambda url, timeout=None: _Resp(b'{"models": []}')):
        assert setup.gpu_fraction() is None

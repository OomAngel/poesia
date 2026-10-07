"""Linking: nearest poems by vector, and the page endpoint."""

from __future__ import annotations

import json

import numpy as np
import pytest

from poesia.linking import LinkIndex


def _write_index(tmp_path) -> None:
    poems = [
        {"title": "Autumn", "author": "A", "text": "leaves fall", "licence": "CC0", "source": "x"},
        {"title": "Sea", "author": "B", "text": "waves", "licence": "CC0", "source": "x"},
        {"title": "Grief", "author": "C", "text": "my father", "licence": "CC0", "source": "x"},
    ]
    (tmp_path / "poems_en.jsonl").write_text("\n".join(json.dumps(p) for p in poems) + "\n")
    np.save(tmp_path / "vectors_en.npy", np.eye(3, dtype="float16"))
    (tmp_path / "index.json").write_text(json.dumps({"model": "fake", "languages": ["en"]}))


def test_nearest_ranks_by_cosine(tmp_path) -> None:
    _write_index(tmp_path)
    index = LinkIndex.load(tmp_path)
    got = index.nearest([0.1, 0.0, 0.9], "en", k=2)
    assert [p["title"] for p in got] == ["Grief", "Autumn"]
    assert got[0]["similarity"] > got[1]["similarity"]
    assert index.nearest([1, 0, 0], "es") == []


def test_mismatched_index_is_rejected(tmp_path) -> None:
    _write_index(tmp_path)
    np.save(tmp_path / "vectors_en.npy", np.eye(2, 3, dtype="float16"))
    with pytest.raises(ValueError):
        LinkIndex.load(tmp_path)


def test_page_link_endpoint(tmp_path, monkeypatch) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import poesia.webapp as webapp
    from poesia.linking import EmbeddingClient

    _write_index(tmp_path)
    monkeypatch.setenv("POESIA_LINK_INDEX", str(tmp_path))
    monkeypatch.setattr(webapp, "_link_index", None)
    monkeypatch.setattr(EmbeddingClient, "embed", lambda self, texts: [[0.0, 1.0, 0.0]])

    class _LLM:
        model = "fake"

        def generate(self, prompt, n=1, temperature=0.9):
            return ["NO"]

    client = TestClient(webapp.create_app(llm=_LLM()))
    r = client.post("/api/link", json={"language": "en", "text": "the sea at dusk"}).json()
    assert r["poems"][0]["title"] == "Sea" and r["poems"][0]["licence"] == "CC0"


def test_poems_with_unicode_line_separators_load(tmp_path) -> None:
    _write_index(tmp_path)
    poem = {"title": "LS", "author": "D", "text": "one two", "licence": "CC0", "source": "x"}
    lines = (tmp_path / "poems_en.jsonl").read_text().splitlines()
    lines[0] = json.dumps(poem, ensure_ascii=False)
    (tmp_path / "poems_en.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert LinkIndex.load(tmp_path).poems["en"][0]["text"] == "one two"

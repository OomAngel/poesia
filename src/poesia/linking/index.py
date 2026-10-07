"""Precomputed poem vectors + one embedding call per query; see ``poesia.linking``."""

from __future__ import annotations

import json
import math
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EmbeddingClient:
    """OpenAI-compatible ``/embeddings`` (Ollama /v1, vLLM, CSCS).

    ``EMBED_BASE_URL`` (default ``LLM_BASE_URL``), ``EMBED_NAME`` (default ``bge-m3``),
    ``EMBED_API_KEY`` (default ``LLM_API_KEY``).
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("EMBED_BASE_URL") or os.environ.get("LLM_BASE_URL", "")
        ).rstrip("/")
        self.model = model or os.environ.get("EMBED_NAME", "bge-m3")
        key = api_key if api_key is not None else os.environ.get("EMBED_API_KEY")
        self.api_key = key if key is not None else os.environ.get("LLM_API_KEY", "")
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.base_url:
            raise RuntimeError("no embedding endpoint: set EMBED_BASE_URL or LLM_BASE_URL")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps({"model": self.model, "input": texts}).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))["data"]
        return [row["embedding"] for row in sorted(data, key=lambda r: r["index"])]


def _normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


@dataclass
class LinkIndex:
    """Poems per language with unit-length vectors (``poems_<lang>.jsonl`` +
    ``vectors_<lang>.npy``, float16, in ``index_dir``)."""

    poems: dict[str, list[dict[str, Any]]]
    vectors: dict[str, Any]  # numpy arrays, shape (n_poems, dim)
    model: str

    @classmethod
    def load(cls, index_dir: str | Path) -> LinkIndex:
        root = Path(index_dir)
        meta = json.loads((root / "index.json").read_text(encoding="utf-8"))
        poems, vectors = {}, {}
        for lang in meta["languages"]:
            # Iterate the file, not .splitlines(): poems may contain U+2028.
            with (root / f"poems_{lang}.jsonl").open(encoding="utf-8") as f:
                poems[lang] = [json.loads(line) for line in f if line.strip()]
            import numpy as np

            vectors[lang] = np.load(root / f"vectors_{lang}.npy").astype("float32")
            if len(poems[lang]) != len(vectors[lang]):
                raise ValueError(f"index for {lang}: poems and vectors differ in length")
        return cls(poems=poems, vectors=vectors, model=meta["model"])

    def nearest(self, query_vec: list[float], language: str, k: int = 3) -> list[dict[str, Any]]:
        import numpy as np

        if language not in self.vectors:
            return []
        sims = self.vectors[language] @ np.asarray(_normalise(query_vec), dtype="float32")
        out = []
        for i in np.argsort(-sims)[:k]:
            poem = dict(self.poems[language][int(i)])
            poem["similarity"] = round(float(sims[i]), 3)
            out.append(poem)
        return out

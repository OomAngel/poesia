"""First-run model setup through Ollama's API, with progress the page can show (plan P4).

On a fresh machine the models are not there yet: Apertus v1.5 8B (GGUF, ~5 GB) and the
embedding model for linking (bge-m3, ~1.2 GB). ``OllamaSetup.ensure()`` pulls what is
missing, streaming Ollama's progress into ``status``, registers each under the name the page
uses with the right chat format and options, and loads the chat model once so the first
suggestion does not wait for it. The page polls ``status`` and shows "downloading the poetry
model (2.1 of 5.0 GB)" instead of a blank terminal; scanning, the safety screen and read-back
work meanwhile. The same code serves the Docker stack and a plain Ollama app install.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

# Apertus chat format (llama.cpp models/templates/Apertus-8B-Instruct.jinja), thinking off.
APERTUS_TEMPLATE = (
    "{{- if .System }}<|system_start|>{{ .System }}<|system_end|>"
    "{{- else }}<|system_start|>You are Apertus, a helpful assistant created by the SwissAI "
    "initiative.<|system_end|>{{- end }}"
    "<|developer_start|>Deliberation: disabled\nTool Capabilities: disabled<|developer_end|>"
    '{{- range .Messages }}{{- if eq .Role "user" }}<|user_start|>{{ .Content }}<|user_end|>'
    '{{- else if eq .Role "assistant" }}<|assistant_start|>{{ .Content }}<|assistant_end|>'
    "{{- end }}{{- end }}<|assistant_start|>"
)
APERTUS_GGUF = "hf.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF:Q4_K_M"


@dataclass
class ModelSpec:
    name: str  # what the page asks for (LLM_NAME / EMBED_NAME)
    source: str  # what Ollama pulls
    template: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    warm: bool = False  # load it once after setup
    label: str = ""  # for the page: "poetry model", "linking model"


def default_specs() -> list[ModelSpec]:
    return [
        ModelSpec(
            name=os.environ.get("LLM_NAME", "poesia-apertus"),
            source=os.environ.get("POESIA_APERTUS_GGUF", APERTUS_GGUF),
            template=APERTUS_TEMPLATE,
            parameters={"stop": ["<|assistant_end|>", "<|user_start|>"], "num_ctx": 4096},
            warm=True,
            label="poetry",
        ),
        ModelSpec(
            name=os.environ.get("EMBED_NAME", "poesia-embed"),
            source="bge-m3",
            # On the CPU, so Apertus keeps the GPU to itself (an 8 GB card has no room for both).
            parameters={"num_gpu": 0},
            label="linking",
        ),
    ]


@dataclass
class SetupStatus:
    phase: str = "checking"  # checking | downloading | preparing | loading | ready | error
    model: str = ""  # label of the model being worked on
    completed: int = 0
    total: int = 0
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class OllamaSetup:
    """Pull, register and warm the page's models on an Ollama server."""

    def __init__(
        self, host: str, specs: list[ModelSpec] | None = None, timeout: float = 30.0
    ) -> None:
        self.host = host.rstrip("/")
        self.specs = specs if specs is not None else default_specs()
        self.timeout = timeout
        self.status = SetupStatus()
        self._lock = threading.Lock()

    # -- HTTP --------------------------------------------------------------

    def _post(self, path: str, body: dict[str, Any], timeout: float | None = None) -> Any:
        req = urllib.request.Request(
            f"{self.host}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        return urllib.request.urlopen(req, timeout=timeout or self.timeout)

    def _present(self) -> set[str]:
        with urllib.request.urlopen(f"{self.host}/api/tags", timeout=self.timeout) as resp:
            models = json.loads(resp.read()).get("models", [])
        names = {m.get("name", "") for m in models}
        return names | {n.removesuffix(":latest") for n in names}

    def _set(self, **kw: Any) -> None:
        with self._lock:
            for k, v in kw.items():
                setattr(self.status, k, v)

    # -- steps -------------------------------------------------------------

    def _pull(self, spec: ModelSpec) -> None:
        self._set(phase="downloading", model=spec.label, completed=0, total=0)
        with self._post("/api/pull", {"model": spec.source, "stream": True}, timeout=3600) as resp:
            for raw in resp:
                if not raw.strip():
                    continue
                event = json.loads(raw)
                if event.get("error"):
                    raise RuntimeError(event["error"])
                if event.get("total"):
                    self._set(completed=int(event.get("completed", 0)), total=int(event["total"]))

    def _create(self, spec: ModelSpec) -> None:
        self._set(phase="preparing", model=spec.label)
        body: dict[str, Any] = {"model": spec.name, "from": spec.source, "stream": False}
        if spec.template:
            body["template"] = spec.template
        if spec.parameters:
            body["parameters"] = spec.parameters
        with self._post("/api/create", body, timeout=600) as resp:
            resp.read()

    def _warm(self, spec: ModelSpec) -> None:
        self._set(phase="loading", model=spec.label)
        body = {
            "model": spec.name,
            "prompt": "Hola",
            "stream": False,
            "options": {"num_predict": 1},
        }
        with self._post("/api/generate", body, timeout=600) as resp:
            resp.read()

    def ensure(self) -> SetupStatus:
        """Bring every model to ready; never raises (errors land in ``status``)."""
        try:
            present = self._present()
            for spec in self.specs:
                if spec.name not in present:
                    if spec.source not in present:
                        self._pull(spec)
                    self._create(spec)
                if spec.warm:
                    self._warm(spec)
            self._set(phase="ready", model="", completed=0, total=0)
        except (urllib.error.URLError, OSError, RuntimeError, ValueError) as exc:
            self._set(phase="error", error=str(exc))
        return self.status

    def gpu_fraction(self) -> float | None:
        """Share of the chat model in GPU memory (Ollama /api/ps), or None if not loaded.

        1.0 is the whole model on the GPU; less means part runs on the CPU and suggestions
        slow down (2026-10-07: 11% on CPU when another model already held the card).
        """
        chat = next((s.name for s in self.specs if s.warm), None)
        try:
            with urllib.request.urlopen(f"{self.host}/api/ps", timeout=5) as resp:
                models = json.loads(resp.read()).get("models", [])
        except (urllib.error.URLError, OSError, ValueError):
            return None
        for m in models:
            if chat and m.get("name", "").removesuffix(":latest") == chat and m.get("size"):
                return round(m.get("size_vram", 0) / m["size"], 2)
        return None

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.ensure, name="poesia-model-setup", daemon=True)
        thread.start()
        return thread

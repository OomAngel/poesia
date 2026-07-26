"""Abstract LLM client interface.

Concrete backends (hosted API, llama.cpp local inference, transformers local
inference) implement this Protocol so the generation loop stays decoupled
from any single provider. This mirrors the "typed port" discipline used
elsewhere: no SDK-specific import should leak into evaluation/ or phonology/.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol


class LLMClient(Protocol):
    """Minimal interface the generation loop needs from any LLM backend."""

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        """Return `n` candidate completions for `prompt`."""
        ...

    def repair(self, line: str, defect_description: str) -> str:
        """Ask the model to fix one explicit, named defect in a single line."""
        ...


class StubLLMClient:
    """Deterministic no-op client for tests and offline development.

    Returns the prompt itself (or a trivially modified variant) instead of
    calling any real model. Useful for exercising the generation loop's
    control flow without network access or GPU/CPU inference cost.
    """

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        return [f"{prompt} [candidate {i}]" for i in range(n)]

    def repair(self, line: str, defect_description: str) -> str:
        return f"{line} [repaired: {defect_description}]"


class HostedLLMClient:
    """Hosted LLM provider via standard HTTP API requests (Gemini or OpenAI format).

    Reads GEMINI_API_KEY or OPENAI_API_KEY from environment. Does not require
    external SDK packages, relying on standard library urllib.
    """

    def __init__(
        self,
        provider: str = "auto",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.provider = provider
        self.timeout = timeout

        if api_key:
            self.api_key = api_key
        elif os.environ.get("GEMINI_API_KEY"):
            self.api_key = os.environ.get("GEMINI_API_KEY", "")
            if provider == "auto":
                self.provider = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            self.api_key = os.environ.get("OPENAI_API_KEY", "")
            if provider == "auto":
                self.provider = "openai"
        else:
            self.api_key = ""

        if model:
            self.model = model
        elif self.provider == "gemini":
            self.model = "gemini-2.5-flash"
        else:
            self.model = "gpt-4o-mini"

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        if not self.api_key:
            raise RuntimeError(
                "HostedLLMClient requires an API key. Set GEMINI_API_KEY or "
                "OPENAI_API_KEY environment variable, or pass api_key to HostedLLMClient."
            )

        if self.provider == "gemini":
            return self._generate_gemini(prompt, n, temperature)
        else:
            return self._generate_openai(prompt, n, temperature)

    def repair(self, line: str, defect_description: str) -> str:
        prompt = (
            f"Fix the following poetic line to resolve this defect: {defect_description}.\n"
            f"Line: \"{line}\"\n"
            "Output ONLY the corrected single line without quotation marks, intro, or explanation."
        )
        candidates = self.generate(prompt, n=1, temperature=0.7)
        if candidates:
            return candidates[0].strip().strip('"\'')
        return line

    def _generate_gemini(self, prompt: str, n: int, temperature: float) -> list[str]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        candidates: list[str] = []
        for _ in range(n):
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature},
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    text = (
                        res.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    candidates.append(text.strip())
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8")
                raise RuntimeError(f"Gemini API HTTP Error {e.code}: {err_msg}") from e
            except Exception as e:
                raise RuntimeError(f"Gemini API request failed: {e}") from e

        return candidates

    def _generate_openai(self, prompt: str, n: int, temperature: float) -> list[str]:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "n": n,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return [c["message"]["content"].strip() for c in res.get("choices", [])]
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"OpenAI API HTTP Error {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAI API request failed: {e}") from e


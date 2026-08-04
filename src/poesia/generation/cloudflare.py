"""Cloudflare Workers AI text backend — reuse the image account's API for poems.

The same free Workers AI account/token that GalerIA uses for SDXL images also
serves text-to-text LLMs through an OpenAI-compatible endpoint:

    POST /client/v4/accounts/{account_id}/ai/v1/chat/completions

That endpoint honours ``n`` (candidate count) in a single request, so a whole
line's candidate batch comes back in one round trip — 70B quality at
roughly the speed of the local 3B batched path.

Model: ``@cf/meta/llama-3.3-70b-instruct-fp8-fast`` by default (override with
``CLOUDFLARE_LLM_MODEL`` or the ``model`` constructor arg). Requires the same
``CLOUDFLARE_ACCOUNT_ID`` / ``CLOUDFLARE_API_TOKEN`` used for image generation.

Same seams as the other LLM clients: stdlib urllib, provider/model attributes,
``LLMUsage`` timing, structured ``LLMProviderError``.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from poesia.exceptions import LLMProviderError
from poesia.generation.llm_client import LLMUsage


class CloudflareLLMClient:
    """LLMClient over Cloudflare Workers AI (OpenAI-compatible chat endpoint)."""

    DEFAULT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{}/ai/v1/chat/completions"
    TIMEOUT = 90.0
    USER_AGENT = "poesia/1.0"

    def __init__(
        self,
        model: str | None = None,
        account_id: str | None = None,
        api_token: str | None = None,
        timeout: float = 90.0,
    ) -> None:
        self.account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self.model = model or os.environ.get("CLOUDFLARE_LLM_MODEL") or self.DEFAULT_MODEL
        self.timeout = timeout
        self.provider = "cloudflare"
        self.usage: LLMUsage = LLMUsage()

    def generate(self, prompt: str, n: int = 1, temperature: float = 0.9) -> list[str]:
        """Return ``n`` candidate completions for ``prompt`` in one request."""
        if not self.account_id or not self.api_token:
            raise LLMProviderError(
                "CloudflareLLMClient requires CLOUDFLARE_ACCOUNT_ID and "
                "CLOUDFLARE_API_TOKEN (same free Workers AI account used for "
                "image generation).",
                provider=self.provider,
            )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "n": max(n, 1),
            "temperature": temperature,
        }
        url = self.BASE_URL.format(self.account_id)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": self.USER_AGENT,
            },
        )

        self.usage = LLMUsage()
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise LLMProviderError(
                f"Cloudflare Workers AI LLM HTTP Error {e.code}: "
                f"{e.read().decode('utf-8', 'replace')[:300]}",
                provider=self.provider,
                status_code=e.code,
            ) from e
        except Exception as e:
            raise LLMProviderError(
                f"Cloudflare Workers AI LLM request failed: {e}", provider=self.provider
            ) from e

        choices = res.get("choices") or []
        texts: list[str] = []
        for choice in choices:
            content = (choice.get("message") or {}).get("content")
            if content:
                texts.append(str(content).strip())
        self.usage.latency_ms = (time.time() - t0) * 1000
        return texts[:n]

    def repair(self, line: str, defect_description: str) -> str:
        """Ask the model to fix one explicit, named defect in a single line."""
        prompt = (
            f"Fix this poetic line to resolve this defect: {defect_description}.\n"
            f'Line: "{line}"\n'
            "Output ONLY the corrected line, nothing else."
        )
        candidates = self.generate(prompt, n=1, temperature=0.7)
        return candidates[0].strip().strip('"').strip("'") if candidates else line


def _client_for(provider: str, **kwargs: Any) -> Any:
    """Small factory used by tests to build a client with explicit creds."""
    return CloudflareLLMClient(**kwargs)

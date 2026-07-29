"""Image-generation backend port.

Mirrors the `poesia.generation.llm_client.LLMClient` Protocol discipline:
GalerIA's illustration logic (composition, auca layout, PDF export) must
never import a specific image-gen SDK directly. Concrete backends
(`openai`, `replicate`, local `diffusers`) implement this Protocol.
"""

from __future__ import annotations

from typing import Protocol


class ImageBackend(Protocol):
    """Minimal interface GalerIA needs from any image-generation backend."""

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        """Return raw image bytes (PNG) for a text prompt + optional style tag."""
        ...


class StubImageBackend:
    """Deterministic no-op backend for tests and offline development.

    Returns a tiny valid 1x1 PNG instead of calling any real image model.
    """

    _MINIMAL_PNG = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        return self._MINIMAL_PNG


class HostedImageBackend:
    """Hosted image generation provider (OpenAI DALL-E or Replicate format).

    Reads OPENAI_API_KEY or REPLICATE_API_TOKEN from environment. Uses standard
    library urllib to avoid direct third-party SDK coupling.
    """

    DEFAULT_STYLE = "traditional spanish woodcut line-art, engraving style"

    def __init__(
        self,
        provider: str = "auto",
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        import os

        self.provider = provider
        self.timeout = timeout

        if api_key:
            self.api_key = api_key
        elif os.environ.get("OPENAI_API_KEY"):
            self.api_key = os.environ.get("OPENAI_API_KEY", "")
            if provider == "auto":
                self.provider = "openai"
        elif os.environ.get("REPLICATE_API_TOKEN"):
            self.api_key = os.environ.get("REPLICATE_API_TOKEN", "")
            if provider == "auto":
                self.provider = "replicate"
        else:
            self.api_key = ""

        if model:
            self.model = model
        elif self.provider == "openai":
            self.model = "dall-e-3"
        else:
            self.model = "stability-ai/sdxl"

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        if not self.api_key:
            raise RuntimeError(
                "HostedImageBackend requires an API key. Set OPENAI_API_KEY or "
                "REPLICATE_API_TOKEN environment variable."
            )

        style_str = style if style is not None else self.DEFAULT_STYLE
        full_prompt = f"{prompt}, {style_str}" if style_str else prompt

        if self.provider == "openai":
            return self._generate_openai(full_prompt)
        else:
            return self._generate_replicate(full_prompt)

    def _generate_openai(self, prompt: str) -> bytes:
        import json
        import urllib.error
        import urllib.request

        url = "https://api.openai.com/v1/images/generations"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
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
                import base64
                b64_data = res["data"][0]["b64_json"]
                return base64.b64decode(b64_data)
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"OpenAI Image API HTTP Error {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAI Image API request failed: {e}") from e

    def _generate_replicate(self, prompt: str) -> bytes:
        import json
        import time
        import urllib.error
        import urllib.request

        url = "https://api.replicate.com/v1/predictions"
        payload = {
            "version": "8be28070e64d571299506207e0aec08562019b22e0ef5d26e060f900ffb5cfe3",
            "input": {"prompt": prompt},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Token {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                get_url = res["urls"]["get"]

            # Poll until prediction completes
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                poll_req = urllib.request.Request(
                    get_url,
                    headers={"Authorization": f"Token {self.api_key}"},
                )
                with urllib.request.urlopen(poll_req, timeout=10.0) as poll_resp:
                    poll_res = json.loads(poll_resp.read().decode("utf-8"))
                    status = poll_res.get("status")
                    if status == "succeeded":
                        img_url = poll_res["output"][0]
                        with urllib.request.urlopen(img_url, timeout=30.0) as img_resp:
                            return img_resp.read()
                    elif status == "failed":
                        raise RuntimeError(f"Replicate prediction failed: {poll_res.get('error')}")
                time.sleep(2.0)

            raise RuntimeError("Replicate image generation timed out.")
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            raise RuntimeError(f"Replicate API HTTP Error {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"Replicate API request failed: {e}") from e


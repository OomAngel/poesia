"""Cloudflare Workers AI backend — free daily-quota online image generation.

Cloudflare's serverless AI runs text-to-image models on their edge network.
The free plan includes **10,000 neurons/day** (reset 00:00 UTC); the Beta
stable-diffusion-xl-base-1.0 model is listed at **$0.00/step**, making a
1024×1024 image effectively free.

Unlike Pollinations, this requires a (free) Cloudflare account:

- ``CLOUDFLARE_ACCOUNT_ID`` and ``CLOUDFLARE_API_TOKEN`` environment variables,
  or the ``account_id`` / ``api_token`` constructor args.
  (Dashboard → Workers AI → "Use REST API" → create a Workers AI API token.)

Why GalerIA cares (see docs/IMAGE_GENERATION_PROVIDERS.md):

- reliable: commercial infrastructure with a real free tier — our #2 pick
- deterministic: the ``seed`` input parameter is supported by the
  text-to-image schema — same prompt ⇒ same image
- stdlib-only: a urllib POST, same seam as the other hosted backends

Caveats: account required (more friction than Pollinations); image models are
labelled Beta; free-tier GPU requests may queue during demand spikes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request


def _looks_like_image(data: bytes) -> bool:
    """Detect common image magic bytes (PNG/JPEG/GIF/WebP) in a response body."""
    return (
        data[:8] == b"\x89PNG\r\n\x1a\n"
        or data[:3] in (b"\xff\xd8\xff", b"GIF")
        or data[:4] == b"RIFF"
    )


class CloudflareImageBackend:
    """Cloudflare Workers AI text-to-image generation (needs a free account).

    Implements the ``ImageBackend`` Protocol.

    Determinism note (live-verified 2026-08-03): a prompt-derived ``seed`` is
    sent (the TextToImage schema lists it), but the served SDXL wrapper does
    **not** honour it in practice — the same prompt+seed produced different
    images on every call. Treat output as *novel per request*; use
    ``--backend pollinations`` or ``--backend procedural`` when bit-for-bit
    reproducibility matters.
    """

    BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{}/ai/run/{}"
    DEFAULT_MODEL = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
    DEFAULT_STYLE = "traditional spanish woodcut line-art, engraving style"
    WIDTH = 1024
    HEIGHT = 1024
    NUM_STEPS = 20  # SDXL schema: default 20, maximum 20
    GUIDANCE = 7.5
    TIMEOUT = 90.0
    USER_AGENT = "poesia/1.0"

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        model: str | None = None,
        timeout: float = 90.0,
    ) -> None:
        import os

        self.account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        """Return image bytes for a prompt + optional style tag.

        The response is base64 image data inside JSON ``result.data`` (a list,
        sometimes a bare string — both are handled). Raises RuntimeError with an
        actionable message for missing credentials, HTTP failures or an
        unexpected response shape.
        """
        if not self.account_id or not self.api_token:
            raise RuntimeError(
                "Cloudflare Workers AI requires CLOUDFLARE_ACCOUNT_ID and "
                "CLOUDFLARE_API_TOKEN (free Cloudflare account, Workers AI → "
                "'Use REST API' → create token). See docs/IMAGE_GENERATION_PROVIDERS.md."
            )

        style_str = style if style is not None else self.DEFAULT_STYLE
        full_prompt = f"{prompt}, {style_str}" if style_str else prompt
        # Prompt-derived seed: the schema lists ``seed`` and it is harmless to
        # send, but live testing (2026-08-03) showed the SDXL wrapper ignores
        # it — do not rely on it for reproducibility.
        seed = int(hashlib.sha256(full_prompt.encode()).hexdigest()[:8], 16) & 0x7FFFFFFF

        payload = {
            "prompt": full_prompt,
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "num_steps": self.NUM_STEPS,
            "guidance": self.GUIDANCE,
            "seed": seed,
        }
        url = self.BASE_URL.format(self.account_id, self.model)
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
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"Cloudflare Workers AI HTTP Error {e.code}: "
                f"{e.read().decode('utf-8', 'replace')[:300]}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Cloudflare Workers AI request failed: {e}") from e

        # Live-verified 2026-08-03: the REST endpoint returns *raw image bytes*
        # (PNG magic 0x89) for text-to-image — despite the API reference's
        # base64 ``result.data`` binding schema. Handle both shapes.
        if _looks_like_image(body):
            return body

        try:
            res = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError(
                "Cloudflare Workers AI returned a non-image, non-JSON response "
                f"({len(body)} bytes)."
            ) from None

        if not res.get("success", True):
            errors = res.get("errors") or []
            raise RuntimeError(f"Cloudflare Workers AI error: {errors}")

        result = res.get("result") or {}
        raw = result.get("data")
        if raw is None:
            raw = result.get("image")
        if isinstance(raw, list):
            if not raw:
                raise RuntimeError("Cloudflare Workers AI returned no image data.")
            raw = raw[0]
        if isinstance(raw, str):
            return base64.b64decode(raw)
        raise RuntimeError(
            f"Cloudflare Workers AI returned an unexpected result shape: {type(raw).__name__}"
        )

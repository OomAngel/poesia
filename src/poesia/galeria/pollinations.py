"""Pollinations.ai backend — free, key-less online image generation.

Pollinations is an open (MIT), community-supported platform: a single GET to
``image.pollinations.ai`` returns a generated image. No API key or signup is
needed for anonymous use (≈1 request/15 s; free registration at
auth.pollinations.ai raises the limits).

Fit with GalerIA:

- free: $0, no key — works out of the box for anyone cloning the repo
- deterministic: a seed derived from the prompt reproduces the same image for
  the same stanza, matching PoesIA's reproducibility discipline
- stdlib-only: a urllib GET, same seam as the other hosted backends

Caveats (verified live 2026-08-03, see docs/IMAGE_GENERATION_PROVIDERS.md):

- response is image bytes — JPEG in practice, not PNG; size may be rounded
  (a 1024x1024 request returned 768x768)
- the ``model`` parameter is not authoritative (observed ``sana`` even when
  ``flux`` was requested) — keep this backend model-agnostic
- community-funded, no SLA; callers must degrade gracefully
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.parse
import urllib.request


class PollinationsImageBackend:
    """Free, key-less online image generation via pollinations.ai.

    Implements the ``ImageBackend`` Protocol. A deterministic seed is derived
    from the prompt so the same stanza always requests the same image.
    """

    BASE_URL = "https://image.pollinations.ai/prompt/{}"
    DEFAULT_STYLE = "traditional spanish woodcut line-art, engraving style"
    SIZE = 1024
    TIMEOUT = 90.0
    USER_AGENT = "poesia/1.0"

    def __init__(self, model: str | None = None, timeout: float = 90.0) -> None:
        # NOTE: ``model`` is forwarded but is NOT authoritative — the service
        # routes internally (observed ``sana`` even with ``model=flux``). Kept
        # for users who want to try; never promised by the docs or the CLI.
        self.model = model
        self.timeout = timeout

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        """Return image bytes for a prompt + optional style tag.

        Returns whatever the service sends (JPEG/PNG — never assert a format;
        ``AucaComposer`` opens via Pillow). Raises RuntimeError with an
        actionable message when the service is unreachable, so the CLI can
        suggest ``--backend procedural``.
        """
        style_str = style if style is not None else self.DEFAULT_STYLE
        full_prompt = f"{prompt}, {style_str}" if style_str else prompt
        # Deterministic seed for the same stanza. Must be a 32-bit *signed* int:
        # Sana rejects seeds > 2147483647 with a 400 ("Too big") — verified live.
        seed = int(hashlib.sha256(full_prompt.encode()).hexdigest()[:8], 16) & 0x7FFFFFFF

        params: dict[str, str | int] = {
            "width": self.SIZE,
            "height": self.SIZE,
            "seed": seed,
            "nologo": "true",
        }
        if self.model:
            params["model"] = self.model
        query = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL.format(urllib.parse.quote(full_prompt))}?{query}"

        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"Pollinations API HTTP Error {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Pollinations API request failed: {e} "
                "(offline? use --backend procedural for the offline renderer)"
            ) from e

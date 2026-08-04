"""End-to-end illustration pipeline: poem text -> auca panels.

Wires the GalerIA building blocks together:

    lines -> split_stanzas() -> extract_imagery() -> build_image_prompt()
        -> ImageBackend.generate_image() -> AucaPanel[]

Backend selection mirrors the ``--llm`` registry pattern: ``auto`` resolves to
the first configured hosted provider (OPENAI_API_KEY / REPLICATE_API_TOKEN)
and falls back to the offline StubImageBackend when no key is present, so the
pipeline always works out of the box.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from poesia.galeria.auca import AucaPanel
from poesia.galeria.backends import HostedImageBackend, ImageBackend, StubImageBackend
from poesia.galeria.cloudflare import CloudflareImageBackend
from poesia.galeria.imagery import build_image_prompt, extract_imagery
from poesia.galeria.pollinations import PollinationsImageBackend
from poesia.galeria.procedural import ProceduralImageBackend

if TYPE_CHECKING:
    from poesia.memoria.records import InfluenceRecord


class IllustrateError(RuntimeError):
    """Raised when illustration cannot be completed for a resolvable reason."""


def split_stanzas(lines: list[str], max_lines_per_stanza: int = 8) -> list[list[str]]:
    """Split poem lines into stanza groups for one image per stanza.

    Blank lines delimit stanzas. If the poem has no blank lines and exceeds
    ``max_lines_per_stanza``, it is chunked so very long poems still produce
    multiple panels instead of a single unwieldy one.
    """
    stanzas: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                stanzas.append(current)
                current = []
        else:
            current.append(line.strip())

    if current:
        stanzas.append(current)

    # No blank-line structure: chunk long single blocks for visual balance.
    if len(stanzas) == 1 and len(stanzas[0]) > max_lines_per_stanza:
        block = stanzas[0]
        stanzas = [
            block[i : i + max_lines_per_stanza] for i in range(0, len(block), max_lines_per_stanza)
        ]

    return stanzas if stanzas else [[]]


def get_image_backend(
    backend: str = "auto",
    api_key: str | None = None,
) -> ImageBackend:
    """Resolve a backend name to an ImageBackend instance.

    ``auto``: use the first configured hosted provider, else the deterministic
    offline procedural renderer (no key needed, no network).
    ``stub``: tiny 1x1 PNG for tests.
    ``procedural``: deterministic offline generative art (no key needed).
    ``pollinations``: free online generation (no key needed; community service,
    ≈1 req/15s anonymous — see docs/IMAGE_GENERATION_PROVIDERS.md).
    ``cloudflare``: Workers AI free tier (needs free CLOUDFLARE_ACCOUNT_ID +
    CLOUDFLARE_API_TOKEN; 10k neurons/day).
    ``openai`` / ``replicate``: hosted backends (requires an API key, from the
    ``api_key`` argument or the environment).
    """
    name = backend.lower()
    if name == "stub":
        return StubImageBackend()
    if name == "procedural":
        return ProceduralImageBackend()
    if name == "pollinations":
        return PollinationsImageBackend()
    if name == "cloudflare":
        return CloudflareImageBackend()
    if name in ("openai", "replicate"):
        return HostedImageBackend(provider=name, api_key=api_key)
    if name == "auto":
        import os

        has_cloudflare = bool(
            os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN")
        )
        if (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("REPLICATE_API_TOKEN")
            or has_cloudflare
        ):
            if os.environ.get("OPENAI_API_KEY") or os.environ.get("REPLICATE_API_TOKEN"):
                return HostedImageBackend(provider="auto", api_key=api_key)
            return CloudflareImageBackend()
        return ProceduralImageBackend()
    raise ValueError(
        f"Unknown image backend: {backend!r}. "
        "Available: auto, stub, procedural, pollinations, cloudflare, openai, replicate."
    )


def derive_style(
    style: str | None,
    influences: list[InfluenceRecord] | None = None,
    retrieval_style: str | None = None,
) -> str | None:
    """Merge influence-derived and retrieval-derived style with the base tag."""
    parts: list[str] = []
    if influences:
        from poesia.galeria.style_anchoring import style_from_influences

        inf_style = style_from_influences(influences)
        if inf_style:
            parts.append(inf_style)
    if retrieval_style:
        parts.append(retrieval_style)
    if style:
        parts.append(style)
    return ", ".join(parts) if parts else None


def illustrate_poem(
    lines: list[str],
    *,
    language: str = "es",
    theme: str = "",
    style: str | None = None,
    backend: str = "auto",
    api_key: str | None = None,
    influences: list[InfluenceRecord] | None = None,
    retrieval_style: str | None = None,
    max_lines_per_stanza: int = 8,
    panel_mode: Literal["stanza", "poem"] = "stanza",
) -> tuple[list[AucaPanel], list[str]]:
    """Generate illustrated panels for a poem.

    ``panel_mode``:
      - ``stanza`` (default): one panel per stanza — the auca tradition,
        captioned with each stanza's verses.
      - ``poem``: a single panel for the whole poem, built from one longer,
        holistic prompt over the entire text (theme + imagery + style).

    Args:
        lines: Poem lines (may include blank lines between stanzas).
        language: Language code for imagery extraction ('es' or 'en').
        theme: Optional thematic anchor prepended to image prompts.
        style: Base style tag appended by the image backend.
        backend: 'auto', 'stub', 'procedural', 'pollinations', 'cloudflare',
            'openai', or 'replicate'.
        api_key: Optional API key override for hosted backends.
        influences: Optional influence records for style anchoring (Phase 4C).
        retrieval_style: Optional comma-separated visual-style keywords derived
            from retrieved library content (--style-from-retrieval).
        max_lines_per_stanza: Fallback chunk size for stanza-less poems
            (ignored in ``poem`` mode).
        panel_mode: 'stanza' or 'poem'.

    Returns:
        ``(panels, prompts)`` — one AucaPanel per unit (stanza or whole poem)
        plus the exact image prompts used, so callers can show or log them.

    Raises:
        ValueError: Unknown ``panel_mode``.
    """
    if panel_mode == "poem":
        stanzas = [lines]
    elif panel_mode == "stanza":
        stanzas = split_stanzas(lines, max_lines_per_stanza=max_lines_per_stanza)
    else:
        raise ValueError(f"Unknown panel_mode: {panel_mode!r}. Available: stanza, poem.")

    img_backend = get_image_backend(backend, api_key)
    final_style = derive_style(style, influences, retrieval_style)

    panels: list[AucaPanel] = []
    prompts: list[str] = []
    for stanza in stanzas:
        imagery = extract_imagery(stanza, language=language)
        prompt = build_image_prompt(imagery, theme=theme, style=None)
        try:
            image_bytes = img_backend.generate_image(prompt=prompt, style=final_style)
        except RuntimeError as exc:
            raise IllustrateError(
                f"Image generation failed for stanza {len(panels) + 1}: {exc}"
            ) from exc
        panels.append(AucaPanel(image_bytes=image_bytes, caption_lines=stanza))
        prompts.append(prompt)

    return panels, prompts

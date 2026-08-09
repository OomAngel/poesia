"""Deterministic offline generative-art backend for GalerIA.

Renders a real, reproducible illustration without any API key or network:
the image is drawn procedurally with Pillow from a seed derived from the
prompt + style, so the same poem always produces the same sheet. Palette is
selected from the poem's imagery keywords (Spanish + English); the style tag
tunes the visual language:

- ``grabado`` / woodcut (default) — high-contrast engraving, double frame
- ``acuarela`` / watercolor — soft translucent washes
- ``art nouveau`` / modernismo — arch frame, gold accents

This keeps GalerIA usable offline end-to-end, in the spirit of the
deterministic phonology spine: algorithms for the craft.
"""

from __future__ import annotations

import hashlib
import io
import math
import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _Palette:
    """A 6-stop color family for one visual mood."""

    sky_top: tuple[int, int, int]
    sky_bottom: tuple[int, int, int]
    land: tuple[int, int, int]
    accent: tuple[int, int, int]
    ink: tuple[int, int, int]
    glow: tuple[int, int, int]


_PALETTES: dict[str, _Palette] = {
    "night": _Palette(
        sky_top=(14, 18, 48),
        sky_bottom=(8, 10, 26),
        land=(16, 22, 44),
        accent=(96, 116, 200),
        ink=(4, 6, 14),
        glow=(224, 234, 255),
    ),
    "water": _Palette(
        sky_top=(8, 46, 56),
        sky_bottom=(4, 26, 34),
        land=(10, 40, 48),
        accent=(56, 160, 170),
        ink=(3, 20, 26),
        glow=(226, 246, 248),
    ),
    "ember": _Palette(
        sky_top=(56, 18, 8),
        sky_bottom=(34, 10, 6),
        land=(48, 16, 10),
        accent=(232, 128, 44),
        ink=(24, 6, 3),
        glow=(255, 228, 168),
    ),
    "forest": _Palette(
        sky_top=(16, 38, 20),
        sky_bottom=(8, 24, 12),
        land=(12, 30, 16),
        accent=(96, 146, 74),
        ink=(6, 16, 8),
        glow=(232, 240, 214),
    ),
    "rose": _Palette(
        sky_top=(64, 26, 34),
        sky_bottom=(36, 14, 20),
        land=(48, 20, 26),
        accent=(216, 122, 142),
        ink=(26, 8, 14),
        glow=(255, 240, 234),
    ),
    # Classic engraving paper — the fallback for abstract/philosophical poems.
    "paper": _Palette(
        sky_top=(248, 242, 230),
        sky_bottom=(236, 226, 208),
        land=(214, 196, 168),
        accent=(150, 60, 40),
        ink=(44, 34, 26),
        glow=(255, 252, 246),
    ),
}

# Keyword groups checked in priority order; rose before forest so "flor" reads
# as a flower, not foliage. Spanish first (image prompts are built in Spanish).
_PALETTE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("night", ["luna", "noche", "estrell", "sombra", "oscuro", "moon", "night", "star"]),
    (
        "water",
        ["agua", "mar", "rio", "río", "lluvia", "lago", "oceano", "water", "sea", "river", "rain"],
    ),
    ("ember", ["sol", "fuego", "llama", "calor", "rojo", "rayo", "sun", "fire", "flame", "ember"]),
    ("rose", ["rosa", "jazmin", "perfume", "rose", "flower", "bloom", "blossom"]),
    (
        "forest",
        [
            "bosque",
            "arbol",
            "árbol",
            "verde",
            "semilla",
            "raiz",
            "raíz",
            "flor",
            "primavera",
            "forest",
            "tree",
            "green",
            "seed",
            "root",
            "radicle",
        ],
    ),
]


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linear interpolation between two RGB colors, t in [0, 1]."""
    return (
        round(c1[0] + (c2[0] - c1[0]) * t),
        round(c1[1] + (c2[1] - c1[1]) * t),
        round(c1[2] + (c2[2] - c1[2]) * t),
    )


def _select_palette(text: str) -> _Palette:
    lowered = text.lower()
    for key, keywords in _PALETTE_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return _PALETTES[key]
    return _PALETTES["paper"]


def _style_mode(style: str | None) -> str:
    s = (style or "").lower()
    if any(k in s for k in ("acuarela", "watercolor", "aquarelle")):
        return "watercolor"
    if any(k in s for k in ("art nouveau", "modernismo", "nouveau")):
        return "nouveau"
    return "woodcut"


def _draw_sky(draw: Any, size: int, pal: Any) -> None:
    """Paint the vertical sky gradient."""
    for y in range(size):
        t = y / size
        draw.line([(0, y), (size, y)], fill=_mix(pal.sky_top, pal.sky_bottom, t))


def _draw_grain(draw: Any, size: int, pal: Any, rng: random.Random) -> None:
    """Scatter paper-grain dots."""
    for _ in range(int(size * size * 0.0025)):
        x = rng.randrange(size)
        y = rng.randrange(size)
        c = pal.ink if rng.random() < 0.5 else pal.glow
        draw.point((x, y), fill=(*c, rng.randint(6, 22)))


def _draw_celestial(draw: Any, size: int, rng: random.Random, pal: Any, horizon: int) -> None:
    """Draw the celestial disc, halo, and light rays."""
    disc_r = rng.randint(int(size * 0.10), int(size * 0.16))
    cx = rng.randint(int(size * 0.22), int(size * 0.78))
    cy = rng.randint(int(size * 0.14), max(int(size * 0.14) + 1, int(horizon * 0.42)))
    halo = disc_r * 2
    draw.ellipse([cx - halo, cy - halo, cx + halo, cy + halo], fill=(*pal.glow, 26))
    draw.ellipse(
        [cx - disc_r, cy - disc_r, cx + disc_r, cy + disc_r],
        fill=(*pal.glow, 255),
    )
    for _ in range(10):
        a = rng.uniform(0, math.tau)
        ln = rng.randint(int(size * 0.05), int(size * 0.11))
        x1 = int(cx + math.cos(a) * (disc_r + 2))
        y1 = int(cy + math.sin(a) * (disc_r + 2))
        x2 = int(cx + math.cos(a) * (disc_r + ln))
        y2 = int(cy + math.sin(a) * (disc_r + ln))
        if y1 < horizon and y2 < horizon:
            draw.line(
                [(x1, y1), (x2, y2)],
                fill=(*pal.glow, rng.randint(50, 110)),
                width=rng.randint(1, 3),
            )


def _draw_hills(draw: Any, size: int, rng: random.Random, pal: Any, horizon: int) -> None:
    """Paint the layered horizon hills."""
    for layer in range(3):
        base = horizon + layer * 20 + rng.randint(-6, 8)
        pts: list[tuple[int, int]] = []
        wave = rng.uniform(1.2, 3.4)
        for x in range(-8, size + 16, 8):
            y = (
                base
                - int((math.sin(x / (46 + layer * 34) * wave) + 1) * (8 + layer * 7))
                + rng.randint(-3, 3)
            )
            pts.append((x, y))
        pts.extend([(size + 16, size + 16), (-16, size + 16)])
        draw.polygon(pts, fill=(*_mix(pal.land, pal.sky_bottom, layer / 4), 255))


def _draw_stalks(draw: Any, size: int, rng: random.Random, pal: Any) -> None:
    """Draw foreground grass stalks."""
    for _ in range(rng.randint(10, 16)):
        gx = rng.uniform(0, size)
        h = rng.randint(int(size * 0.10), int(size * 0.30))
        for step in range(h):
            y0 = size - step
            gx += rng.uniform(-1.4, 1.4)
            draw.point((int(gx), y0), fill=(*pal.ink, rng.randint(150, 235)))


def _draw_stars(
    draw: Any,
    size: int,
    rng: random.Random,
    pal: Any,
    horizon: int,
    mode: str,
) -> None:
    """Scatter stars above the horizon (skipped for watercolor)."""
    if mode == "watercolor" or rng.random() >= 0.85:
        return
    for _ in range(rng.randint(24, 60)):
        sx = rng.randrange(size)
        sy = rng.randrange(0, horizon)
        sr = rng.choice([1, 1, 2])
        draw.ellipse(
            [sx - sr, sy - sr, sx + sr, sy + sr],
            fill=(*pal.glow, rng.randint(70, 190)),
        )


def _draw_frame(draw: Any, size: int, rng: random.Random, pal: Any, mode: str) -> None:
    """Draw the style-specific border frame."""
    m = rng.randint(14, 22)
    if mode == "woodcut":
        draw.rectangle([m, m, size - m, size - m], outline=(*pal.ink, 255), width=3)
        draw.rectangle(
            [m + 7, m + 7, size - m - 7, size - m - 7],
            outline=(*pal.accent, 200),
            width=1,
        )
        for y in range(size - m - 12, size - m, 5):
            draw.line([(m + 12, y), (size - m - 12, y)], fill=(*pal.ink, 40), width=1)
    elif mode == "nouveau":
        draw.arc(
            [m, m, size - m, size - m],
            start=180,
            end=360,
            fill=(*pal.accent, 255),
            width=4,
        )
        draw.line([(m, size - m), (size - m, size - m)], fill=(*pal.accent, 255), width=4)
        for _ in range(5):
            tx = rng.randint(m + 20, size - m - 20)
            ty = rng.randint(m + 20, size - m - 60)
            draw.ellipse([tx, ty, tx + 10, ty + 16], outline=(*pal.accent, 220), width=1)
    else:  # watercolor: soft translucent washes instead of a hard frame
        for _ in range(4):
            r = rng.randint(int(size * 0.18), int(size * 0.38))
            bx = rng.randint(0, size)
            by = rng.randint(0, size)
            c = pal.accent if rng.random() < 0.5 else pal.glow
            draw.ellipse([bx - r, by - r, bx + r, by + r], fill=(*c, rng.randint(10, 22)))


class ProceduralImageBackend:
    """Deterministic offline generative-art backend (no API key needed).

    Implements the ``ImageBackend`` Protocol. The seed is derived from the
    prompt + style text, so identical inputs always render identical output —
    the README example can be regenerated bit-for-bit on any machine.
    """

    SIZE = 640

    def generate_image(self, prompt: str, style: str | None = None) -> bytes:
        """Return a rendered PNG (Pillow) for a prompt + optional style tag."""
        import importlib.util

        if importlib.util.find_spec("PIL") is None:
            raise RuntimeError("Pillow is not installed. Run: pip install -e '.[illustration]'")
        img = self._render(prompt, style)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _render(self, prompt: str, style: str | None):
        """Render the composition; returns a Pillow RGB image."""
        from PIL import Image, ImageDraw

        seed = hashlib.sha256(f"{prompt}||{style or ''}".encode()).hexdigest()
        rng = random.Random(seed)
        mode = _style_mode(style)
        pal = _select_palette(f"{prompt} {style or ''}")
        size = self.SIZE

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        _draw_sky(draw, size, pal)
        _draw_grain(draw, size, pal, rng)
        horizon = int(size * 0.60) + rng.randint(-24, 24)
        _draw_celestial(draw, size, rng, pal, horizon)
        _draw_hills(draw, size, rng, pal, horizon)
        _draw_stalks(draw, size, rng, pal)
        _draw_stars(draw, size, rng, pal, horizon, mode)
        _draw_frame(draw, size, rng, pal, mode)

        return img.convert("RGB")

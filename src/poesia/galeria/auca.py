"""Auca-style composition: pairing illustration with verse.

An "auca" (Catalan/Spanish) or "aleluya" is a traditional illustrated verse
sheet — one image per stanza (or couplet), captioned with the corresponding
lines. This module composites a generated image with poem text via Pillow.

Font note: use a diacritic-complete typeface (e.g. Noto Serif, EB Garamond)
so Spanish accents and ñ render correctly — a common gotcha with narrow
Latin-1-only fonts.

Phase 0 status: interface only, Pillow not yet a hard dependency.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AucaPanel:
    """One panel of an auca sheet: an image paired with its caption lines."""

    image_bytes: bytes
    caption_lines: list[str]


class AucaComposer:
    """Composites AucaPanel objects into a single illustrated sheet or PDF.

    Backends (lazily imported):
        - Pillow: raster compositing (paste image + stamp text)
        - svgwrite / drawsvg: vector composition for scalable print output
        - WeasyPrint: HTML/CSS -> PDF for a full poetry-book export
    """

    def compose_panel(self, panel: AucaPanel, font_path: str | None = None) -> bytes:
        """Render a single AucaPanel to a PNG with the caption stamped below."""
        try:
            from PIL import Image, ImageDraw, ImageFont  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Pillow is not installed. Run: pip install -e '.[illustration]'"
            ) from exc
        raise NotImplementedError(
            "Panel compositing pending Pillow layout implementation (Phase 2)."
        )

    def compose_sheet(self, panels: list[AucaPanel]) -> bytes:
        """Compose multiple panels into a single auca sheet (grid layout)."""
        raise NotImplementedError("Sheet composition pending Phase 2.")

    def export_pdf(self, panels: list[AucaPanel], output_path: str) -> None:
        """Export a full illustrated poem as a print-ready PDF via WeasyPrint."""
        raise NotImplementedError("PDF export pending WeasyPrint integration (Phase 2).")

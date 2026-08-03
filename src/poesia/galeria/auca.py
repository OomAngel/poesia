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
            import io

            from PIL import Image, ImageDraw, ImageFont  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Pillow is not installed. Run: pip install -e '.[illustration]'"
            ) from exc

        # Load image bytes
        src_img = Image.open(io.BytesIO(panel.image_bytes)).convert("RGB")
        img_w, img_h = src_img.size

        # Layout parameters
        padding = 20
        caption_margin = 15
        font_size = max(14, int(img_w / 25))

        try:
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Prepare caption lines
        lines = panel.caption_lines if panel.caption_lines else [""]
        line_height = font_size + 4
        caption_h = len(lines) * line_height + caption_margin * 2

        card_w = img_w + padding * 2
        card_h = img_h + caption_h + padding * 2

        canvas = Image.new("RGB", (card_w, card_h), color=(255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # Draw subtle outer border
        draw.rectangle([5, 5, card_w - 6, card_h - 6], outline=(180, 180, 180), width=2)

        # Paste illustration
        canvas.paste(src_img, (padding, padding))

        # Draw inner border around image
        draw.rectangle(
            [padding, padding, padding + img_w, padding + img_h], outline=(100, 100, 100), width=1
        )

        # Stamp caption text
        y_cursor = padding + img_h + caption_margin
        for line in lines:
            # Center caption line
            try:
                bbox = font.getbbox(line)
                text_w = bbox[2] - bbox[0]
            except AttributeError:
                text_w = len(line) * (font_size * 0.6)

            x_pos = max(padding, (card_w - text_w) // 2)
            draw.text((x_pos, y_cursor), line, fill=(20, 20, 20), font=font)
            y_cursor += line_height

        output = io.BytesIO()
        canvas.save(output, format="PNG")
        return output.getvalue()

    def compose_sheet(self, panels: list[AucaPanel], title: str = "PoesIA — Auca") -> bytes:
        """Compose multiple panels into a single auca sheet (2-column grid layout)."""
        try:
            import io
            import math

            from PIL import Image, ImageDraw, ImageFont  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Pillow is not installed. Run: pip install -e '.[illustration]'"
            ) from exc

        if not panels:
            raise ValueError("compose_sheet requires at least one AucaPanel.")

        rendered_panels = [Image.open(io.BytesIO(self.compose_panel(p))) for p in panels]
        panel_w, panel_h = rendered_panels[0].size

        cols = 2 if len(rendered_panels) > 1 else 1
        rows = math.ceil(len(rendered_panels) / cols)

        header_h = 80
        margin = 30
        grid_w = cols * panel_w + margin * (cols + 1)
        grid_h = header_h + rows * panel_h + margin * (rows + 1)

        sheet = Image.new("RGB", (grid_w, grid_h), color=(250, 248, 245))
        draw = ImageDraw.Draw(sheet)

        # Header Title
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        draw.text((margin, 25), title, fill=(40, 40, 40), font=font)
        draw.line(
            [(margin, header_h - 10), (grid_w - margin, header_h - 10)],
            fill=(200, 190, 180),
            width=2,
        )

        # Layout grid
        for idx, panel_img in enumerate(rendered_panels):
            r = idx // cols
            c = idx % cols
            x = margin + c * (panel_w + margin)
            y = header_h + margin + r * (panel_h + margin)
            sheet.paste(panel_img, (x, y))

        output = io.BytesIO()
        sheet.save(output, format="PNG")
        return output.getvalue()

    def export_pdf(
        self,
        panels: list[AucaPanel],
        output_path: str,
        title: str = "PoesIA — Auca",
    ) -> None:
        """Export a full illustrated poem as a print-ready PDF via WeasyPrint.

        Requires the ``illustration`` extra (``pip install -e '.[illustration]'``).
        Panels are laid out on a 2-column grid; each image keeps its stanza
        caption beneath it.
        """
        try:
            from weasyprint import HTML
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "WeasyPrint is not installed. Run: pip install -e '.[illustration]'"
            ) from exc

        import base64
        from html import escape

        cards: list[str] = []
        for panel in panels:
            b64 = base64.b64encode(panel.image_bytes).decode("ascii")
            captions = "<br>".join(escape(line) for line in panel.caption_lines)
            cards.append(
                f'<div class="card">'
                f'<img src="data:image/png;base64,{b64}" alt="auca panel"/>'
                f'<div class="caption">{captions}</div>'
                f"</div>"
            )

        html_doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<style>
  body {{ font-family: Georgia, "Times New Roman", serif; margin: 2cm; color: #222; }}
  h1 {{ text-align: center; font-weight: normal; font-size: 1.6em; margin-bottom: 1cm; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1cm; }}
  .card {{ border: 1px solid #ccc; padding: 8px; page-break-inside: avoid; }}
  .card img {{ width: 100%; height: auto; }}
  .caption {{ text-align: center; font-style: italic; margin-top: 6px; line-height: 1.4; }}
</style>
</head>
<body>
<h1>{escape(title)}</h1>
<div class="grid">{"".join(cards)}</div>
</body>
</html>"""
        HTML(string=html_doc).write_pdf(output_path)

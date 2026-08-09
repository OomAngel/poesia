"""Unit tests for GalerIA's AucaComposer (panel/sheet composition).

Backend behaviors (stub/hosted/HTTP contract) live in their own files:
test_galeria_pipeline.py, test_hosted_image_*.py, test_galeria_*.py.
"""

from __future__ import annotations

from poesia.galeria.auca import AucaComposer, AucaPanel
from poesia.galeria.backends import StubImageBackend


def test_auca_composer_compose_panel() -> None:
    stub = StubImageBackend()
    img_bytes = stub.generate_image("test prompt")
    panel = AucaPanel(
        image_bytes=img_bytes, caption_lines=["Lluvia sobre la piedra", "en la noche oscura"]
    )

    composer = AucaComposer()
    panel_png = composer.compose_panel(panel)
    assert panel_png.startswith(b"\x89PNG")


def test_auca_composer_compose_sheet() -> None:
    stub = StubImageBackend()
    img_bytes = stub.generate_image("test prompt")
    panels = [
        AucaPanel(image_bytes=img_bytes, caption_lines=["Estanza una"]),
        AucaPanel(image_bytes=img_bytes, caption_lines=["Estanza dos"]),
    ]

    composer = AucaComposer()
    sheet_png = composer.compose_sheet(panels, title="Test Auca")
    assert sheet_png.startswith(b"\x89PNG")

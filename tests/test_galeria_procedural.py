"""Tests for the deterministic offline ProceduralImageBackend."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from poesia.galeria.procedural import ProceduralImageBackend, _select_palette, _style_mode


def _png_size(png_bytes: bytes) -> tuple[int, int]:
    """Decode PNG header dimensions without a full image load."""
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    w = int.from_bytes(png_bytes[16:20], "big")
    h = int.from_bytes(png_bytes[20:24], "big")
    return w, h


def test_generate_image_returns_valid_png() -> None:
    backend = ProceduralImageBackend()
    img = backend.generate_image("Luna sobre el mar azul", "grabado español")
    assert img[:8] == b"\x89PNG\r\n\x1a\n"
    assert _png_size(img) == (backend.SIZE, backend.SIZE)


def test_generate_image_is_deterministic() -> None:
    backend = ProceduralImageBackend()
    img1 = backend.generate_image("La luna sobre el agua fría", "grabado español")
    img2 = backend.generate_image("La luna sobre el agua fría", "grabado español")
    assert img1 == img2


def test_generate_image_varies_with_prompt() -> None:
    backend = ProceduralImageBackend()
    night = backend.generate_image("La luna sobre el mar", "grabado español")
    ember = backend.generate_image("El sol y el fuego", "grabado español")
    assert night != ember


def test_generate_image_varies_with_style() -> None:
    backend = ProceduralImageBackend()
    woodcut = backend.generate_image("La luna", "grabado español")
    watercolor = backend.generate_image("La luna", "acuarela")
    assert woodcut != watercolor


def test_generate_image_without_style_tag() -> None:
    backend = ProceduralImageBackend()
    img = backend.generate_image("Bosque verde y semilla")
    assert img[:8] == b"\x89PNG\r\n\x1a\n"


def test_missing_pillow_raises_actionable_error() -> None:
    backend = ProceduralImageBackend()
    with patch("importlib.util.find_spec", return_value=None):
        with pytest.raises(RuntimeError, match="Pillow is not installed"):
            backend.generate_image("x")


def test_select_palette_matches_keywords() -> None:
    assert _select_palette("La luna brilla en la noche") == _select_palette("noche")
    assert _select_palette("El mar azul") == _select_palette("agua")
    assert _select_palette("El sol y el fuego") == _select_palette("fuego")
    assert _select_palette("una rosa roja") == _select_palette("rosa")
    assert _select_palette("bosque y flor de primavera") == _select_palette("flor")
    assert _select_palette("palabras abstractas y filosóficas") == _select_palette("paper")


def test_style_mode_detection() -> None:
    assert _style_mode("grabado español") == "woodcut"
    assert _style_mode("acuarela suave") == "watercolor"
    assert _style_mode("art nouveau, jewel tones") == "nouveau"
    assert _style_mode(None) == "woodcut"


def test_rendered_image_decodable_with_pillow() -> None:
    from PIL import Image as PImage

    backend = ProceduralImageBackend()
    img = backend.generate_image("Luna nocturna", "grabado")
    with PImage.open(io.BytesIO(img)) as pil:
        assert pil.size == (backend.SIZE, backend.SIZE)
        assert pil.mode == "RGB"

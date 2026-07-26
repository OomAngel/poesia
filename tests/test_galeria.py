"""Unit tests for GalerIA (ImageBackend and AucaComposer)."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch
import pytest

from poesia.galeria.auca import AucaComposer, AucaPanel
from poesia.galeria.backends import HostedImageBackend, StubImageBackend


def test_stub_image_backend() -> None:
    backend = StubImageBackend()
    img_bytes = backend.generate_image("A cat sitting under rain")
    assert img_bytes.startswith(b"\x89PNG")


def test_hosted_image_backend_missing_key() -> None:
    backend = HostedImageBackend(api_key="", provider="openai")
    with pytest.raises(RuntimeError, match="requires an API key"):
        backend.generate_image("A landscape")


@patch("urllib.request.urlopen")
def test_hosted_image_backend_openai_mock(mock_urlopen: MagicMock) -> None:
    import base64
    minimal_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    b64_str = base64.b64encode(minimal_png).decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = (
        f'{{"data": [{{"b64_json": "{b64_str}"}}]}}'
    ).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    backend = HostedImageBackend(provider="openai", api_key="sk-test", model="dall-e-3")
    img_bytes = backend.generate_image("Lluvia sobre la ciudad")
    assert img_bytes.startswith(b"\x89PNG")


def test_auca_composer_compose_panel() -> None:
    stub = StubImageBackend()
    img_bytes = stub.generate_image("test prompt")
    panel = AucaPanel(image_bytes=img_bytes, caption_lines=["Lluvia sobre la piedra", "en la noche oscura"])

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

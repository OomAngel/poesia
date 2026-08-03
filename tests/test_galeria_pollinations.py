"""Tests for the free, key-less PollinationsImageBackend (mock-based)."""

from __future__ import annotations

import urllib.parse
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from poesia.galeria.pipeline import get_image_backend
from poesia.galeria.pollinations import PollinationsImageBackend


class TestPollinationsImageBackend:
    """Mocked HTTP tests for the pollinations.ai backend."""

    def _mock_urlopen(self, captured, image_bytes: bytes = b"JPEG_IMAGE_BYTES"):
        def _handler(req, timeout=None):
            captured.append(req)
            mock_response = MagicMock()
            mock_response.read.return_value = image_bytes
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        return _handler

    def test_request_url_has_expected_params(self) -> None:
        captured: list = []

        with patch(
            "urllib.request.urlopen", side_effect=self._mock_urlopen(captured)
        ):
            PollinationsImageBackend().generate_image("La luna sobre el mar")

        assert len(captured) == 1
        url = captured[0].full_url
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query)

        assert parsed.netloc == "image.pollinations.ai"
        assert "/prompt/" in parsed.path
        assert query["width"] == ["1024"]
        assert query["height"] == ["1024"]
        assert query["nologo"] == ["true"]
        assert len(query["seed"][0]) > 0
        # the prompt must be in the path, URL-encoded
        assert "La%20luna%20sobre%20el%20mar" in parsed.path

    def test_style_appended_to_prompt(self) -> None:
        captured: list = []
        with patch(
            "urllib.request.urlopen", side_effect=self._mock_urlopen(captured)
        ):
            PollinationsImageBackend().generate_image("La luna", style="acuarela")

        decoded = urllib.parse.unquote(urllib.parse.urlsplit(captured[0].full_url).path)
        assert "La luna" in decoded
        assert "acuarela" in decoded

    def test_default_style_used_when_none(self) -> None:
        captured: list = []
        with patch(
            "urllib.request.urlopen", side_effect=self._mock_urlopen(captured)
        ):
            PollinationsImageBackend().generate_image("La luna")

        decoded = urllib.parse.unquote(urllib.parse.urlsplit(captured[0].full_url).path)
        assert PollinationsImageBackend.DEFAULT_STYLE in decoded

    def test_seed_is_deterministic_and_signed_32bit(self) -> None:
        seeds: list[int] = []

        def _capture(req, timeout=None):
            qs = urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
            seeds.append(int(qs["seed"][0]))
            mock_response = MagicMock()
            mock_response.read.return_value = b"x"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=_capture):
            backend = PollinationsImageBackend()
            backend.generate_image("El umbral de la noche")
            backend.generate_image("El umbral de la noche")

        assert len(seeds) == 2
        assert seeds[0] == seeds[1]
        # Pollinations' Sana pipeline rejects seeds > 2^31-1 with a 400
        # ("Too big: expected number to be <=2147483647") — verified live 2026-08-03.
        assert all(0 < s <= 2147483647 for s in seeds)

    def test_model_param_forwarded_when_given(self) -> None:
        captured: list = []
        with patch(
            "urllib.request.urlopen", side_effect=self._mock_urlopen(captured)
        ):
            PollinationsImageBackend(model="turbo").generate_image("La luna")

        query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(captured[0].full_url).query
        )
        assert query["model"] == ["turbo"]

    def test_returns_image_bytes_as_is(self) -> None:
        fake_image = b"\xff\xd8\xff\xe0JPEG_BYTES"
        captured: list = []
        with patch(
            "urllib.request.urlopen", side_effect=self._mock_urlopen(captured, fake_image)
        ):
            result = PollinationsImageBackend().generate_image("La luna")

        assert result == fake_image

    def test_http_error_raises_runtime_error(self) -> None:
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="https://image.pollinations.ai/prompt/x",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=BytesIO(b"slow down"),
        )
        with patch("urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(RuntimeError, match="Pollinations API HTTP Error 429"):
                PollinationsImageBackend().generate_image("La luna")

    def test_connection_error_mentions_offline_fallback(self) -> None:
        with patch(
            "urllib.request.urlopen",
            side_effect=ConnectionError("network unreachable"),
        ):
            with pytest.raises(RuntimeError, match="procedural"):
                PollinationsImageBackend().generate_image("La luna")

    def test_registered_in_pipeline_registry(self) -> None:
        backend = get_image_backend("pollinations")
        assert isinstance(backend, PollinationsImageBackend)

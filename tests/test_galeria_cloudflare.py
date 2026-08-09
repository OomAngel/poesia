"""Tests for the Cloudflare Workers AI backend (mock-based)."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from poesia.galeria.cloudflare import CloudflareImageBackend
from poesia.galeria.pipeline import get_image_backend

ACCOUNT_ID = "test-account"
API_TOKEN = "test-token"


class TestCloudflareImageBackend:
    """Mocked HTTP tests for the Cloudflare Workers AI backend."""

    def _client(self, **kwargs) -> CloudflareImageBackend:
        return CloudflareImageBackend(account_id=ACCOUNT_ID, api_token=API_TOKEN, **kwargs)

    def _mock_urlopen(self, captured, result_json: dict):
        def _handler(req, timeout=None):
            captured.append(req)
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(result_json).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        return _handler

    def test_request_url_contains_account_and_model(self) -> None:
        captured: list = []
        result = {"result": {"data": [base64.b64encode(b"x").decode()]}, "success": True}
        with patch("urllib.request.urlopen", side_effect=self._mock_urlopen(captured, result)):
            self._client().generate_image("La luna")

        assert len(captured) == 1
        req = captured[0]
        assert req.full_url == (
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/"
            f"{CloudflareImageBackend.DEFAULT_MODEL}"
        )

    def test_authorization_bearer_header(self) -> None:
        captured: list = []
        result = {"result": {"data": [base64.b64encode(b"x").decode()]}, "success": True}
        with patch("urllib.request.urlopen", side_effect=self._mock_urlopen(captured, result)):
            self._client().generate_image("La luna")

        headers = dict(captured[0].headers)
        assert headers.get("Authorization") == f"Bearer {API_TOKEN}"

    def test_request_body_parameters(self) -> None:
        captured: list = []
        result = {"result": {"data": [base64.b64encode(b"x").decode()]}, "success": True}
        with patch("urllib.request.urlopen", side_effect=self._mock_urlopen(captured, result)):
            self._client().generate_image("La luna sobre el mar", style="acuarela")

        body = json.loads(captured[0].data.decode("utf-8"))
        assert "La luna sobre el mar" in body["prompt"]
        assert "acuarela" in body["prompt"]
        assert body["width"] == 1024
        assert body["height"] == 1024
        assert body["num_steps"] == 20
        assert body["guidance"] == 7.5
        assert 0 < body["seed"] <= 2147483647

    def test_request_seed_is_stable_and_signed_32bit(self) -> None:
        # The seed we *send* is stable per prompt; note the served SDXL ignores
        # it in practice (live-verified 2026-08-03) — this test only pins the
        # request shape.
        seeds: list[int] = []

        def _capture(req, timeout=None):
            body = json.loads(req.data.decode("utf-8"))
            seeds.append(body["seed"])
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"result": {"data": [base64.b64encode(b"x").decode()]}, "success": True}
            ).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=_capture):
            client = self._client()
            client.generate_image("El umbral de la noche")
            client.generate_image("El umbral de la noche")

        assert len(seeds) == 2
        assert seeds[0] == seeds[1]
        assert all(0 < s <= 2147483647 for s in seeds)

    def test_decodes_base64_list_response(self) -> None:
        fake_image = b"PNG_BYTES"
        result = {"result": {"data": [base64.b64encode(fake_image).decode()]}, "success": True}
        captured: list = []
        with patch("urllib.request.urlopen", side_effect=self._mock_urlopen(captured, result)):
            out = self._client().generate_image("La luna")

        assert out == fake_image

    def test_decodes_base64_string_response(self) -> None:
        fake_image = b"JPEG_BYTES"
        result = {"result": {"data": base64.b64encode(fake_image).decode()}, "success": True}
        captured: list = []
        with patch("urllib.request.urlopen", side_effect=self._mock_urlopen(captured, result)):
            out = self._client().generate_image("La luna")

        assert out == fake_image

    def test_missing_credentials_raises_actionable_error(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            client = CloudflareImageBackend()
            with pytest.raises(RuntimeError, match="CLOUDFLARE_ACCOUNT_ID"):
                client.generate_image("La luna")

    def test_http_error_raises_runtime_error(self) -> None:
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="https://api.cloudflare.com/client/v4/accounts/x/ai/run/y",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=BytesIO(b'{"errors":["rate limit"]}'),
        )
        with patch("urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(RuntimeError, match="Cloudflare Workers AI HTTP Error 429"):
                self._client().generate_image("La luna")

    def test_api_success_false_raises(self) -> None:
        result = {"success": False, "errors": [{"message": "model unavailable"}]}
        captured: list = []
        with patch("urllib.request.urlopen", side_effect=self._mock_urlopen(captured, result)):
            with pytest.raises(RuntimeError, match="model unavailable"):
                self._client().generate_image("La luna")

    def test_empty_data_raises(self) -> None:
        result = {"result": {"data": []}, "success": True}
        captured: list = []
        with patch("urllib.request.urlopen", side_effect=self._mock_urlopen(captured, result)):
            with pytest.raises(RuntimeError, match="no image data"):
                self._client().generate_image("La luna")

    def test_raw_png_bytes_response_returned_as_is(self) -> None:
        # Live-verified 2026-08-03: the REST endpoint returns raw image bytes
        # (PNG magic), not JSON — must pass through untouched.
        fake_png = b"\x89PNG\r\n\x1a\n" + b"raw-png-body" + b"IEND"
        captured: list = []

        def _handler(req, timeout=None):
            captured.append(req)
            mock_response = MagicMock()
            mock_response.read.return_value = fake_png
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=_handler):
            out = self._client().generate_image("La luna")

        assert out == fake_png

    def test_non_image_non_json_response_raises(self) -> None:
        captured: list = []

        def _handler(req, timeout=None):
            captured.append(req)
            mock_response = MagicMock()
            mock_response.read.return_value = b"<html>some error page</html>"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=_handler):
            with pytest.raises(RuntimeError, match="non-image, non-JSON"):
                self._client().generate_image("La luna")

    def test_registered_in_pipeline_registry(self) -> None:
        assert isinstance(get_image_backend("cloudflare"), CloudflareImageBackend)

    def test_auto_picks_cloudflare_when_configured(self) -> None:
        with patch.dict(
            "os.environ",
            {"CLOUDFLARE_ACCOUNT_ID": "acct", "CLOUDFLARE_API_TOKEN": "tok"},
            clear=True,
        ):
            assert isinstance(get_image_backend("auto"), CloudflareImageBackend)

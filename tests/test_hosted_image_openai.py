"""Mock-based tests for HostedImageBackend OpenAI DALL-E integration."""

import base64
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from poesia.galeria.backends import HostedImageBackend


class TestOpenAIImageBackend:
    """Tests for OpenAI DALL-E API integration."""

    @pytest.fixture
    def client(self) -> HostedImageBackend:
        return HostedImageBackend(provider="openai", api_key="test-key")

    def test_openai_request_payload_shape(self, client: HostedImageBackend) -> None:
        """Verify DALL-E request payload has correct structure."""
        captured_request = None
        fake_image = b"fake_png_data"

        def capture_request(req, timeout=None):
            nonlocal captured_request
            captured_request = req
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"data": [{"b64_json": base64.b64encode(fake_image).decode()}]}
            ).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.generate_image("A moonlit garden")

        assert captured_request is not None
        payload = json.loads(captured_request.data.decode("utf-8"))

        assert payload["model"] == "dall-e-3"
        assert "A moonlit garden" in payload["prompt"]
        assert payload["n"] == 1
        assert payload["size"] == "1024x1024"
        assert payload["response_format"] == "b64_json"

    def test_openai_authorization_header(self, client: HostedImageBackend) -> None:
        """Verify Bearer token in Authorization header."""
        captured_headers = None
        fake_image = b"fake_png_data"

        def capture_request(req, timeout=None):
            nonlocal captured_headers
            captured_headers = dict(req.headers)
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"data": [{"b64_json": base64.b64encode(fake_image).decode()}]}
            ).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.generate_image("prompt")

        assert captured_headers.get("Authorization") == "Bearer test-key"

    def test_openai_appends_style_to_prompt(self, client: HostedImageBackend) -> None:
        """Verify style is appended to prompt."""
        captured_payload = None
        fake_image = b"fake_png_data"

        def capture_request(req, timeout=None):
            nonlocal captured_payload
            captured_payload = json.loads(req.data.decode("utf-8"))
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"data": [{"b64_json": base64.b64encode(fake_image).decode()}]}
            ).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=capture_request):
            client.generate_image("A garden", style="watercolor painting")

        assert "A garden" in captured_payload["prompt"]
        assert "watercolor painting" in captured_payload["prompt"]

    def test_openai_returns_decoded_image_bytes(self, client: HostedImageBackend) -> None:
        """Verify base64 response is decoded to raw bytes."""
        fake_image = b"PNG_IMAGE_BYTES_HERE"
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"data": [{"b64_json": base64.b64encode(fake_image).decode()}]}
        ).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = client.generate_image("prompt")

        assert result == fake_image

    def test_openai_http_error_handling(self, client: HostedImageBackend) -> None:
        """Verify HTTP errors are wrapped with context."""
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="https://api.openai.com/v1/images/generations",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(b'{"error": {"message": "Invalid prompt"}}'),
        )

        with patch("urllib.request.urlopen", side_effect=mock_error):
            with pytest.raises(RuntimeError) as exc_info:
                client.generate_image("prompt")

        assert "OpenAI Image API HTTP Error 400" in str(exc_info.value)

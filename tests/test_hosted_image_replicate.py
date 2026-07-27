"""Mock-based tests for HostedImageBackend Replicate integration."""

import json
from unittest.mock import MagicMock, patch

import pytest

from poesia.galeria.backends import HostedImageBackend


def make_replicate_mock(fake_image: bytes = b"fake_png"):
    """Create a mock that handles the full Replicate request flow."""
    call_count = [0]  # Use list to allow mutation in closure

    def handle_request(req, timeout=None):
        call_count[0] += 1
        mock_response = MagicMock()

        if call_count[0] == 1:  # Initial POST
            mock_response.read.return_value = json.dumps({
                "urls": {"get": "https://api.replicate.com/v1/predictions/123"}
            }).encode("utf-8")
        elif call_count[0] == 2:  # Poll - succeeded
            mock_response.read.return_value = json.dumps({
                "status": "succeeded",
                "output": ["https://example.com/image.png"]
            }).encode("utf-8")
        else:  # Image download
            mock_response.read.return_value = fake_image

        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        return mock_response

    return handle_request


class TestReplicateImageBackend:
    """Tests for Replicate API integration."""

    @pytest.fixture
    def client(self) -> HostedImageBackend:
        return HostedImageBackend(provider="replicate", api_key="test-token")

    def test_replicate_initial_request_shape(self, client: HostedImageBackend) -> None:
        """Verify initial prediction request has correct structure."""
        captured_request = [None]
        mock_handler = make_replicate_mock()

        def capture_first(req, timeout=None):
            if captured_request[0] is None:
                captured_request[0] = req
            return mock_handler(req, timeout)

        with patch("urllib.request.urlopen", side_effect=capture_first):
            client.generate_image("A moonlit garden")

        payload = json.loads(captured_request[0].data.decode("utf-8"))
        assert "version" in payload
        assert "input" in payload
        assert "A moonlit garden" in payload["input"]["prompt"]

    def test_replicate_token_auth_header(self, client: HostedImageBackend) -> None:
        """Verify Token auth header format (different from Bearer)."""
        captured_headers = [None]
        mock_handler = make_replicate_mock()

        def capture_headers(req, timeout=None):
            if captured_headers[0] is None:
                captured_headers[0] = dict(req.headers)
            return mock_handler(req, timeout)

        with patch("urllib.request.urlopen", side_effect=capture_headers):
            client.generate_image("prompt")

        # Replicate uses "Token" not "Bearer"
        assert captured_headers[0].get("Authorization") == "Token test-token"

    def test_replicate_failed_prediction_raises(self, client: HostedImageBackend) -> None:
        """Verify failed prediction raises RuntimeError."""
        def handle_failure(req, timeout=None):
            mock_response = MagicMock()
            if req.data:
                mock_response.read.return_value = json.dumps({
                    "urls": {"get": "https://api.replicate.com/v1/predictions/123"}
                }).encode("utf-8")
            else:
                mock_response.read.return_value = json.dumps({
                    "status": "failed",
                    "error": "NSFW content detected"
                }).encode("utf-8")
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            return mock_response

        with patch("urllib.request.urlopen", side_effect=handle_failure):
            with pytest.raises(RuntimeError) as exc_info:
                client.generate_image("prompt")

        assert "NSFW content detected" in str(exc_info.value)


class TestImageBackendAutoDetection:
    """Tests for provider auto-detection."""

    def test_auto_detects_openai(self) -> None:
        """Auto-detects OpenAI when OPENAI_API_KEY set."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
            client = HostedImageBackend(provider="auto")
        assert client.provider == "openai"

    def test_auto_detects_replicate(self) -> None:
        """Auto-detects Replicate when REPLICATE_API_TOKEN set."""
        with patch.dict("os.environ", {"REPLICATE_API_TOKEN": "r8-test"}, clear=True):
            client = HostedImageBackend(provider="auto")
        assert client.provider == "replicate"

    def test_no_key_raises_on_generate(self) -> None:
        """Generate raises clear error when no API key."""
        with patch.dict("os.environ", {}, clear=True):
            client = HostedImageBackend(provider="auto")
        with pytest.raises(RuntimeError) as exc_info:
            client.generate_image("prompt")
        assert "requires an API key" in str(exc_info.value)

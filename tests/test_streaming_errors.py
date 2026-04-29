# Assistant Runtime SDK - Streaming Error Mapping Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for stream_chat error translation.

The SDK catches network failures during ``stream_chat`` and converts them to
``stream_error`` events with a friendly ``error`` sentence and a stable
``error_code``. The original exception text is preserved under ``_detail`` so
the FACO relay can persist it server-side without leaking it to end users.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from assistant_runtime_sdk import AssistantRuntimeClient


@pytest.fixture
def client():
    return AssistantRuntimeClient(
        tenant_id="t",
        tenant_secret="s",
        ar_url="https://ar.example.com",
    )


def _post_raising(exc):
    """Build a context-manager-compatible mock that raises on iter_lines."""
    response = MagicMock()
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    response.raise_for_status = MagicMock()
    response.iter_lines = MagicMock(side_effect=exc)
    return response


class TestStreamChatErrorMapping:
    """The SDK must surface friendly messages with stable error codes."""

    def test_chunked_encoding_error_yields_connection_interrupted(self, client):
        """ChunkedEncodingError → CONNECTION_INTERRUPTED with original detail."""
        exc = requests.exceptions.ChunkedEncodingError(
            "Connection broken: InvalidChunkLength(got length b'', 0 bytes read)"
        )
        with patch("assistant_runtime_sdk.client.requests.post", return_value=_post_raising(exc)):
            events = list(client.stream_chat("sess", "hello", user_id="u"))

        assert len(events) == 1
        evt = events[0]
        assert evt["event"] == "stream_error"
        assert evt["data"]["error_code"] == "CONNECTION_INTERRUPTED"
        # Friendly message — never the urllib3 string
        assert "interrupted" in evt["data"]["error"].lower()
        assert "InvalidChunkLength" not in evt["data"]["error"]
        # Original detail preserved for server logs
        assert "InvalidChunkLength" in evt["data"]["_detail"]

    def test_connection_error_yields_connection_error(self, client):
        """Generic ConnectionError → CONNECTION_ERROR (not _INTERRUPTED)."""
        exc = requests.exceptions.ConnectionError("Failed to establish a new connection")
        with patch("assistant_runtime_sdk.client.requests.post", return_value=_post_raising(exc)):
            events = list(client.stream_chat("sess", "hello", user_id="u"))

        assert events[0]["data"]["error_code"] == "CONNECTION_ERROR"
        assert "_detail" in events[0]["data"]

    def test_timeout_yields_timeout(self, client):
        """Regression guard: Timeout still maps to TIMEOUT."""
        exc = requests.exceptions.Timeout("Read timed out")
        with patch("assistant_runtime_sdk.client.requests.post", return_value=_post_raising(exc)):
            events = list(client.stream_chat("sess", "hello", user_id="u"))

        assert events[0]["data"]["error_code"] == "TIMEOUT"
        assert "_detail" in events[0]["data"]

    def test_generic_request_exception_yields_request_error(self, client):
        """Anything else under RequestException → REQUEST_ERROR fallback."""
        exc = requests.exceptions.InvalidURL("malformed URL")
        with patch("assistant_runtime_sdk.client.requests.post", return_value=_post_raising(exc)):
            events = list(client.stream_chat("sess", "hello", user_id="u"))

        assert events[0]["data"]["error_code"] == "REQUEST_ERROR"

    def test_friendly_messages_never_leak_internal_detail(self, client):
        """No friendly ``error`` string should contain the original exception text."""
        exc = requests.exceptions.ChunkedEncodingError(
            "internal-only-marker-xyz123"
        )
        with patch("assistant_runtime_sdk.client.requests.post", return_value=_post_raising(exc)):
            events = list(client.stream_chat("sess", "hello", user_id="u"))

        assert "internal-only-marker-xyz123" not in events[0]["data"]["error"]
        assert "internal-only-marker-xyz123" in events[0]["data"]["_detail"]

# Assistant Runtime SDK - session_state Passthrough Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Tests for the zero-retention ``session_state`` passthrough on stream_chat."""

import inspect

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _make_client():
    return AssistantRuntimeClient(
        tenant_id="test-tenant",
        tenant_secret="test-secret",
        ar_url="https://ar.example.com",
    )


class TestSessionStatePayload:
    """_prepare_stream_payload must only include session_state when provided."""

    def test_session_state_present_when_provided(self):
        client = _make_client()
        blob = {"blob": "x", "sig": "y", "format_version": 1}
        payload = client._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
            session_state=blob,
        )
        assert payload["session_state"] == blob

    def test_session_state_absent_when_not_provided(self):
        client = _make_client()
        payload = client._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
        )
        assert "session_state" not in payload

    def test_session_state_absent_when_none(self):
        client = _make_client()
        payload = client._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
            session_state=None,
        )
        assert "session_state" not in payload


class TestSessionStateParity:
    """Both sync and async stream_chat must accept session_state (no drift)."""

    def test_sync_stream_chat_accepts_session_state(self):
        params = inspect.signature(AssistantRuntimeClient.stream_chat).parameters
        assert "session_state" in params
        assert params["session_state"].default is None

    def test_async_stream_chat_accepts_session_state(self):
        params = inspect.signature(AsyncAssistantRuntimeClient.stream_chat).parameters
        assert "session_state" in params
        assert params["session_state"].default is None

    def test_sync_and_async_session_state_param_match(self):
        sync_param = inspect.signature(
            AssistantRuntimeClient.stream_chat
        ).parameters["session_state"]
        async_param = inspect.signature(
            AsyncAssistantRuntimeClient.stream_chat
        ).parameters["session_state"]
        assert sync_param.default == async_param.default
        assert sync_param.kind == async_param.kind

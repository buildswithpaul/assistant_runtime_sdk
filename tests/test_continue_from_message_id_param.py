# Assistant Runtime SDK - continue_from_message_id Passthrough Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Tests for the ``continue_from_message_id`` passthrough on stream_chat."""

import inspect

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _make_client():
    return AssistantRuntimeClient(
        tenant_id="test-tenant",
        tenant_secret="test-secret",
        ar_url="https://ar.example.com",
    )


class TestContinueFromMessageIdPayload:
    """_prepare_stream_payload must only include continue_from_message_id when provided."""

    def test_continue_from_message_id_present_when_provided(self):
        client = _make_client()
        payload = client._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
            continue_from_message_id="X",
        )
        assert payload["continue_from_message_id"] == "X"

    def test_continue_from_message_id_absent_when_not_provided(self):
        client = _make_client()
        payload = client._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
        )
        assert "continue_from_message_id" not in payload

    def test_continue_from_message_id_absent_when_none(self):
        client = _make_client()
        payload = client._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
            continue_from_message_id=None,
        )
        assert "continue_from_message_id" not in payload


class TestContinueFromMessageIdParity:
    """Both sync and async stream_chat must accept continue_from_message_id (no drift)."""

    def test_sync_stream_chat_accepts_continue_from_message_id(self):
        params = inspect.signature(AssistantRuntimeClient.stream_chat).parameters
        assert "continue_from_message_id" in params
        assert params["continue_from_message_id"].default is None

    def test_async_stream_chat_accepts_continue_from_message_id(self):
        params = inspect.signature(AsyncAssistantRuntimeClient.stream_chat).parameters
        assert "continue_from_message_id" in params
        assert params["continue_from_message_id"].default is None

    def test_sync_and_async_continue_from_message_id_param_match(self):
        sync_param = inspect.signature(
            AssistantRuntimeClient.stream_chat
        ).parameters["continue_from_message_id"]
        async_param = inspect.signature(
            AsyncAssistantRuntimeClient.stream_chat
        ).parameters["continue_from_message_id"]
        assert sync_param.default == async_param.default
        assert sync_param.kind == async_param.kind

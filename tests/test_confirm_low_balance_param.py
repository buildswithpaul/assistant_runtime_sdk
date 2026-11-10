# Assistant Runtime SDK - confirm_low_balance Passthrough Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Tests for the ``confirm_low_balance`` passthrough on stream_chat."""

import inspect
from unittest.mock import patch

import pytest

import assistant_runtime_sdk
from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _make_client():
    return AssistantRuntimeClient(
        tenant_id="test-tenant",
        tenant_secret="test-secret",
        ar_url="https://ar.example.com",
    )


class TestConfirmLowBalancePayload:
    """_prepare_stream_payload sends confirm_low_balance=1 only when truthy."""

    def test_present_as_one_when_true(self):
        payload = _make_client()._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
            confirm_low_balance=True,
        )
        assert payload["confirm_low_balance"] == 1

    @pytest.mark.parametrize("value", [None, False])
    def test_absent_when_none_or_false(self, value):
        payload = _make_client()._prepare_stream_payload(
            session_id="session-1",
            message="Hello",
            user_id="user@example.com",
            confirm_low_balance=value,
        )
        assert "confirm_low_balance" not in payload

    def test_absent_when_not_provided(self):
        payload = _make_client()._prepare_stream_payload(
            session_id="session-1", message="Hello", user_id="user@example.com"
        )
        assert "confirm_low_balance" not in payload


class TestConfirmLowBalanceParity:
    """Both sync and async stream_chat accept confirm_low_balance (no drift)."""

    def test_both_clients_accept_parameter(self):
        for cls in (AssistantRuntimeClient, AsyncAssistantRuntimeClient):
            params = inspect.signature(cls.stream_chat).parameters
            assert "confirm_low_balance" in params
            assert params["confirm_low_balance"].default is None

    def test_sync_and_async_param_match(self):
        sync_param = inspect.signature(
            AssistantRuntimeClient.stream_chat
        ).parameters["confirm_low_balance"]
        async_param = inspect.signature(
            AsyncAssistantRuntimeClient.stream_chat
        ).parameters["confirm_low_balance"]
        assert sync_param.default == async_param.default
        assert sync_param.kind == async_param.kind


def test_version_is_1_13_0():
    assert assistant_runtime_sdk.__version__ == "1.13.0"


class _StopStream(Exception):
    """Raised by the patched payload builder to end stream_chat before any HTTP."""


class TestLowBalancePreviewMarker:
    """Clients declare they can render the low-balance preview; opt-out is explicit."""

    def test_marker_present_by_default(self):
        payload = _make_client()._prepare_stream_payload(
            session_id="s", message="m", user_id="u"
        )
        assert payload["low_balance_preview"] == 1

    def test_marker_absent_when_false(self):
        payload = _make_client()._prepare_stream_payload(
            session_id="s", message="m", user_id="u", low_balance_preview=False
        )
        assert "low_balance_preview" not in payload

    def test_confirm_low_balance_unchanged_alongside_marker(self):
        client = _make_client()
        confirmed = client._prepare_stream_payload(
            session_id="s", message="m", user_id="u", confirm_low_balance=True
        )
        assert confirmed["confirm_low_balance"] == 1
        assert confirmed["low_balance_preview"] == 1
        plain = client._prepare_stream_payload(session_id="s", message="m", user_id="u")
        assert "confirm_low_balance" not in plain

    def test_both_clients_default_to_true_keyword_only(self):
        for cls in (AssistantRuntimeClient, AsyncAssistantRuntimeClient):
            param = inspect.signature(cls.stream_chat).parameters["low_balance_preview"]
            assert param.default is True
            assert param.kind is inspect.Parameter.KEYWORD_ONLY

    @pytest.mark.parametrize("value", [True, False])
    def test_sync_stream_chat_passes_it_through(self, value):
        client = _make_client()
        with patch.object(
            client, "_prepare_stream_payload", side_effect=_StopStream
        ) as prepare:
            with pytest.raises(_StopStream):
                next(client.stream_chat("s", "m", "u", low_balance_preview=value))
        assert prepare.call_args.kwargs["low_balance_preview"] is value

    @pytest.mark.parametrize("value", [True, False])
    async def test_async_stream_chat_passes_it_through(self, value):
        async with AsyncAssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        ) as client:
            with patch.object(
                client, "_prepare_stream_payload", side_effect=_StopStream
            ) as prepare:
                with pytest.raises(_StopStream):
                    await client.stream_chat(
                        "s", "m", "u", low_balance_preview=value
                    ).__anext__()
        assert prepare.call_args.kwargs["low_balance_preview"] is value

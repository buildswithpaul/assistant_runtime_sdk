# test_composer_modes_params.py
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

import inspect

import pytest

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _make_client():
    return AssistantRuntimeClient(
        tenant_id="test-tenant", tenant_secret="test-secret", ar_url="https://ar.example.com"
    )


class TestComposerModesPayload:
    def test_flags_are_present_when_provided(self):
        payload = _make_client()._prepare_stream_payload(
            session_id="s", message="m", user_id="u", web_search=True, thinking_enabled=True
        )
        assert payload["web_search"] is True
        assert payload["thinking_enabled"] is True

    def test_flags_are_absent_when_omitted(self):
        payload = _make_client()._prepare_stream_payload(session_id="s", message="m", user_id="u")
        assert "web_search" not in payload
        assert "thinking_enabled" not in payload

    def test_explicit_false_rides_the_wire(self):
        """Absence and False must stay distinguishable — off is a real instruction."""
        payload = _make_client()._prepare_stream_payload(
            session_id="s", message="m", user_id="u", web_search=False
        )
        assert payload["web_search"] is False


class TestComposerModesParity:
    def test_both_clients_declare_the_params_identically(self):
        sync = inspect.signature(AssistantRuntimeClient.stream_chat).parameters
        asyn = inspect.signature(AsyncAssistantRuntimeClient.stream_chat).parameters

        for name in ("web_search", "thinking_enabled"):
            assert sync[name].default is None
            assert sync[name].kind is inspect.Parameter.KEYWORD_ONLY
            assert sync[name].kind is asyn[name].kind
            assert sync[name].default is asyn[name].default

    def test_the_flags_cannot_be_passed_positionally(self):
        """Two production callers pass seven leading args positionally."""
        client = _make_client()
        with pytest.raises(TypeError):
            client.stream_chat(
                "s", "m", "u", None, None, None, None, None, None, None, None, None, True
            )

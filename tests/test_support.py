# Assistant Runtime SDK - Support (Tickets & Feedback) Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for the support _prepare_* helpers (create_ticket / submit_feedback)."""

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _client():
    return AssistantRuntimeClient(
        tenant_id="tid-1",
        tenant_secret="secret",
        ar_url="https://ar.example.com",
    )


def test_client_methods_exist():
    c = _client()
    assert hasattr(c, "create_ticket")
    assert hasattr(c, "submit_feedback")
    a = AsyncAssistantRuntimeClient(
        tenant_id="tid-1", tenant_secret="secret", ar_url="https://ar.example.com",
    )
    assert hasattr(a, "create_ticket")
    assert hasattr(a, "submit_feedback")


def test_prepare_create_ticket():
    c = _client()
    endpoint, payload = c._prepare_create_ticket(
        user_id="user@example.com",
        subject="X",
        description="Y",
        category="Bug",
        conversation_id="conv-1",
        environment={"fac_version": "2.3"},
    )
    assert endpoint == "support.create_ticket"
    assert payload["tenant_id"] == "tid-1"
    assert payload["user_id"] == "user@example.com"
    assert payload["subject"] == "X"
    assert payload["description"] == "Y"
    assert payload["category"] == "Bug"
    assert payload["conversation_id"] == "conv-1"
    assert payload["environment"] == {"fac_version": "2.3"}


def test_prepare_create_ticket_omits_optional_when_none():
    c = _client()
    endpoint, payload = c._prepare_create_ticket(
        user_id="u", subject="X", description="Y",
    )
    assert "conversation_id" not in payload
    assert "environment" not in payload
    assert payload.get("category") is None or "category" not in payload


def test_prepare_submit_feedback():
    c = _client()
    endpoint, payload = c._prepare_submit_feedback(
        user_id="u", rating=5, comment="Great", category="Product",
        conversation_id=None, environment=None,
    )
    assert endpoint == "support.submit_feedback"
    assert payload["tenant_id"] == "tid-1"
    assert payload["user_id"] == "u"
    assert payload["rating"] == 5
    assert payload["comment"] == "Great"
    assert payload["category"] == "Product"
    assert "conversation_id" not in payload
    assert "environment" not in payload

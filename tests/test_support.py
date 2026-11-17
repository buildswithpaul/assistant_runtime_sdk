# Assistant Runtime SDK - Support (Tickets & Feedback) Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for the support _prepare_* helpers (create_ticket / submit_feedback)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

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


def test_prepare_submit_feedback_sends_source_and_contact_ok():
    endpoint, payload = _client()._prepare_submit_feedback(
        user_id="u", rating=4, source="Pulse", contact_ok=True,
    )
    assert endpoint == "support.submit_feedback"
    assert payload["source"] == "Pulse"
    assert payload["contact_ok"] is True


def test_prepare_submit_feedback_keeps_contact_ok_false():
    _, payload = _client()._prepare_submit_feedback(user_id="u", contact_ok=False)
    assert payload["contact_ok"] is False


def test_prepare_submit_feedback_omits_source_and_contact_ok_when_none():
    _, payload = _client()._prepare_submit_feedback(user_id="u", rating=5)
    assert "source" not in payload
    assert "contact_ok" not in payload


def test_prepare_rate_answer():
    endpoint, payload = _client()._prepare_rate_answer(
        user_id="u", message_id="m1", reaction="Down",
        reasons=["wrong", "slow"], comment="nope",
    )
    assert endpoint == "support.rate_answer"
    assert payload == {
        "tenant_id": "tid-1", "user_id": "u", "message_id": "m1",
        "reaction": "Down", "reasons": ["wrong", "slow"], "comment": "nope",
    }


def test_prepare_rate_answer_omits_optional_when_none():
    _, payload = _client()._prepare_rate_answer(
        user_id="u", message_id="m1", reaction="Up",
    )
    assert "reasons" not in payload
    assert "comment" not in payload


def test_prepare_withdraw_answer_feedback():
    endpoint, payload = _client()._prepare_withdraw_answer_feedback("u", "m1")
    assert endpoint == "support.withdraw_answer_feedback"
    assert payload == {"tenant_id": "tid-1", "user_id": "u", "message_id": "m1"}


def test_prepare_get_answer_ratings():
    endpoint, payload = _client()._prepare_get_answer_ratings("u", ["m1", "m2"])
    assert endpoint == "support.get_answer_ratings"
    assert payload == {
        "tenant_id": "tid-1", "user_id": "u", "message_ids": ["m1", "m2"],
    }


_WIRING_CASES = [
    ("rate_answer", {"message_id": "m1", "reaction": "Down", "reasons": ["wrong", "slow"]},
     "support.rate_answer",
     {"tenant_id": "tid-1", "user_id": "u", "message_id": "m1", "reaction": "Down",
      "reasons": ["wrong", "slow"]}),
    ("withdraw_answer_feedback", {"message_id": "m1"},
     "support.withdraw_answer_feedback",
     {"tenant_id": "tid-1", "user_id": "u", "message_id": "m1"}),
    ("get_answer_ratings", {"message_ids": ["m1", "m2"]},
     "support.get_answer_ratings",
     {"tenant_id": "tid-1", "user_id": "u", "message_ids": ["m1", "m2"]}),
    ("submit_feedback", {"source": "Pulse", "contact_ok": True},
     "support.submit_feedback",
     {"tenant_id": "tid-1", "user_id": "u", "source": "Pulse", "contact_ok": True}),
]


@pytest.mark.parametrize("name,kwargs,endpoint,payload", _WIRING_CASES)
def test_sync_method_posts_to_endpoint(name, kwargs, endpoint, payload):
    c = _client()
    with patch.object(c, "_request_post_json", return_value={"ok": 1}) as post:
        result = getattr(c, name)("u", **kwargs)
    post.assert_called_once_with(endpoint, payload)
    assert result == {"ok": 1}


@pytest.mark.parametrize("name,kwargs,endpoint,payload", _WIRING_CASES)
def test_async_method_posts_to_endpoint(name, kwargs, endpoint, payload):
    a = AsyncAssistantRuntimeClient(
        tenant_id="tid-1", tenant_secret="secret", ar_url="https://ar.example.com",
    )
    with patch.object(a, "_request_post_json", new=AsyncMock(return_value={"ok": 1})) as post:
        result = asyncio.run(getattr(a, name)("u", **kwargs))
    post.assert_awaited_once_with(endpoint, payload)
    assert result == {"ok": 1}

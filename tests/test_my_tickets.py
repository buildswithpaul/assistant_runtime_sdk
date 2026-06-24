# Assistant Runtime SDK - My Tickets Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for the My Tickets _prepare_* helpers (list/get_thread/reply)."""

from assistant_runtime_sdk import AssistantRuntimeClient


def _c():
    return AssistantRuntimeClient(tenant_id="t1", tenant_secret="s", ar_url="https://ar.example.com")


def test_prepare_list_tickets():
    endpoint, payload = _c()._prepare_list_tickets(user_id="u", status="Open")
    assert endpoint == "support.list_tickets"
    assert payload == {"tenant_id": "t1", "user_id": "u", "status": "Open"}


def test_prepare_list_tickets_no_status():
    endpoint, payload = _c()._prepare_list_tickets(user_id="u")
    assert endpoint == "support.list_tickets"
    assert "status" not in payload
    assert payload == {"tenant_id": "t1", "user_id": "u"}


def test_prepare_get_ticket_thread():
    endpoint, payload = _c()._prepare_get_ticket_thread(user_id="u", ticket_id="58")
    assert endpoint == "support.get_ticket_thread"
    assert payload == {"tenant_id": "t1", "user_id": "u", "ticket_id": "58"}


def test_prepare_reply_to_ticket():
    endpoint, payload = _c()._prepare_reply_to_ticket(user_id="u", ticket_id="58", message="hi")
    assert endpoint == "support.reply_to_ticket"
    assert payload == {"tenant_id": "t1", "user_id": "u", "ticket_id": "58", "message": "hi"}


def test_client_methods_exist():
    from assistant_runtime_sdk import AssistantRuntimeClient
    for m in ("list_tickets", "get_ticket_thread", "reply_to_ticket"):
        assert hasattr(AssistantRuntimeClient, m)

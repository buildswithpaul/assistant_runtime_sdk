# Assistant Runtime SDK - Seat transport tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Releasing a seat is a write, so it must travel as one.

Frappe rolls back any request whose method is not in UNSAFE_HTTP_METHODS
unless `frappe.local.flags.commit` is set (frappe/app.py:421-424). The seat
endpoints do not set it, so `remove_seat`'s `subscription.save()` was
discarded on every call while the response reported success.
"""

from unittest.mock import patch

import pytest

from assistant_runtime_sdk.client import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _client() -> AssistantRuntimeClient:
    return AssistantRuntimeClient(
        tenant_id="tenant-abc",
        tenant_secret="secret",
        ar_url="https://ar.example.com",
    )


def _async_client() -> AsyncAssistantRuntimeClient:
    return AsyncAssistantRuntimeClient(
        tenant_id="tenant-abc",
        tenant_secret="secret",
        ar_url="https://ar.example.com",
    )


def test_remove_user_seat_uses_post():
    client = _client()
    with patch.object(
        client, "_request_post_json", return_value={"success": True}
    ) as mock_post, patch.object(client, "_request_get") as mock_get:
        client.remove_user_seat()

    mock_post.assert_called_once()
    mock_get.assert_not_called()
    endpoint, payload = mock_post.call_args.args[0], mock_post.call_args.args[1]
    assert endpoint == "remove_user_seat"
    assert payload["tenant_id"] == "tenant-abc"


def test_preview_seat_charge_stays_a_get():
    """A pure read. Changing it would break deployed SDK versions for nothing."""
    client = _client()
    with patch.object(client, "_request_get", return_value={}) as mock_get:
        client.preview_seat_charge()
    mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_async_remove_user_seat_uses_post():
    client = _async_client()

    async def _fake_post(*args, **kwargs):
        return {"success": True}

    with patch.object(
        client, "_request_post_json", side_effect=_fake_post
    ) as mock_post, patch.object(client, "_request_get") as mock_get:
        await client.remove_user_seat()

    mock_post.assert_called_once()
    mock_get.assert_not_called()
    endpoint, payload = mock_post.call_args.args[0], mock_post.call_args.args[1]
    assert endpoint == "remove_user_seat"
    assert payload["tenant_id"] == "tenant-abc"

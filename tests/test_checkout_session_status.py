# Assistant Runtime SDK - Checkout session status tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Request shape for asking whether a hosted checkout's purchase has landed.

The hosted checkout page returns the customer with ``fac_checkout=<session>``;
the site polls this with that session until the purchase is applied.
"""

import asyncio
import inspect
from unittest.mock import AsyncMock, patch

import pytest

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient
from assistant_runtime_sdk.exceptions import ARBillingUnavailableError


def _client(cls=AssistantRuntimeClient):
    return cls(
        ar_url="https://ar.example.com",
        tenant_id="tenant-abc",
        tenant_secret="secret",
    )


class TestPrepareGetCheckoutSessionStatus:
    def test_endpoint_and_payload(self):
        endpoint, payload = _client()._prepare_get_checkout_session_status("CHK-2026-00001")
        assert endpoint == "get_checkout_session_status"
        assert payload == {"tenant_id": "tenant-abc", "session": "CHK-2026-00001"}

    def test_a_blank_session_is_refused_before_any_request(self):
        with pytest.raises(ValueError):
            _client()._prepare_get_checkout_session_status("")

    def test_refused_when_billing_is_known_to_be_absent(self):
        client = _client()
        client._billing_available = False
        with pytest.raises(ARBillingUnavailableError):
            client._prepare_get_checkout_session_status("CHK-2026-00001")


class TestClientMethods:
    def test_sync_posts_to_the_payments_app(self):
        client = _client()
        with patch.object(client, "_request_post_json", return_value={"done": True}) as post:
            result = client.get_checkout_session_status("CHK-2026-00001")

        assert result == {"done": True}
        post.assert_called_once_with(
            "get_checkout_session_status",
            {"tenant_id": "tenant-abc", "session": "CHK-2026-00001"},
            api_base=client.billing_api_base,
        )

    def test_async_posts_to_the_payments_app(self):
        client = _client(AsyncAssistantRuntimeClient)
        post = AsyncMock(return_value={"done": False})
        with patch.object(client, "_request_post_json", post):
            result = asyncio.run(client.get_checkout_session_status("CHK-2026-00001"))

        assert result == {"done": False}
        post.assert_awaited_once_with(
            "get_checkout_session_status",
            {"tenant_id": "tenant-abc", "session": "CHK-2026-00001"},
            api_base=client.billing_api_base,
        )

    def test_the_billing_base_targets_the_payments_api_module(self):
        """AR re-exports the endpoint flat under ``assistant_runtime_payments.api``."""
        assert _client().billing_api_base.endswith("/api/method/assistant_runtime_payments.api")

    def test_signatures_match_across_clients(self):
        sync_sig = inspect.signature(AssistantRuntimeClient.get_checkout_session_status)
        async_sig = inspect.signature(AsyncAssistantRuntimeClient.get_checkout_session_status)
        assert sync_sig.parameters == async_sig.parameters
        assert inspect.iscoroutinefunction(AsyncAssistantRuntimeClient.get_checkout_session_status)

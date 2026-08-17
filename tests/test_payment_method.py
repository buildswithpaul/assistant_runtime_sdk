# Assistant Runtime SDK - Payment method tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Request shapes for the self-serve payment-method endpoints."""

import inspect

import pytest

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _client() -> AssistantRuntimeClient:
    return AssistantRuntimeClient(
        ar_url="https://ar.example.com",
        tenant_id="tenant-abc",
        tenant_secret="secret",
    )


class TestPrepareGetPaymentInstrument:
    def test_endpoint_and_payload(self):
        endpoint, payload = _client()._prepare_get_payment_instrument()
        assert endpoint == "get_payment_instrument"
        assert payload == {"tenant_id": "tenant-abc"}


class TestPrepareUpdatePaymentMethod:
    def test_no_arguments_sends_only_tenant(self):
        endpoint, payload = _client()._prepare_update_payment_method()
        assert endpoint == "update_payment_method"
        assert payload == {"tenant_id": "tenant-abc"}

    def test_payment_method_is_forwarded(self):
        _, payload = _client()._prepare_update_payment_method(payment_method="upi")
        assert payload["payment_method"] == "upi"

    def test_billing_name_is_forwarded(self):
        _, payload = _client()._prepare_update_payment_method(billing_name="Acme Ltd")
        assert payload["billing_name"] == "Acme Ltd"

    def test_none_values_are_omitted_not_sent(self):
        """A null in the payload would reach the endpoint as an explicit
        argument and defeat the server-side default."""
        _, payload = _client()._prepare_update_payment_method(
            payment_method=None, billing_name=None
        )
        assert "payment_method" not in payload
        assert "billing_name" not in payload


class TestClientMethods:
    def test_sync_client_exposes_both_methods(self):
        assert hasattr(AssistantRuntimeClient, "get_payment_instrument")
        assert hasattr(AssistantRuntimeClient, "update_payment_method")

    def test_async_client_exposes_both_methods(self):
        assert hasattr(AsyncAssistantRuntimeClient, "get_payment_instrument")
        assert hasattr(AsyncAssistantRuntimeClient, "update_payment_method")

    @pytest.mark.parametrize(
        "method_name", ["get_payment_instrument", "update_payment_method"]
    )
    def test_signatures_match_across_clients(self, method_name):
        sync_sig = inspect.signature(getattr(AssistantRuntimeClient, method_name))
        async_sig = inspect.signature(
            getattr(AsyncAssistantRuntimeClient, method_name)
        )
        assert sync_sig.parameters == async_sig.parameters

    def test_update_payment_method_stays_callable_with_no_arguments(self):
        """Existing callers pass nothing. That must keep working."""
        sig = inspect.signature(AssistantRuntimeClient.update_payment_method)
        required = [
            name for name, p in sig.parameters.items()
            if name != "self" and p.default is inspect.Parameter.empty
        ]
        assert required == []

    def test_async_methods_are_coroutines(self):
        for name in ("get_payment_instrument", "update_payment_method"):
            assert inspect.iscoroutinefunction(
                getattr(AsyncAssistantRuntimeClient, name)
            )

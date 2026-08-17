# Assistant Runtime SDK - Payment method tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Request shapes for the self-serve payment-method endpoints."""

from assistant_runtime_sdk import AssistantRuntimeClient


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

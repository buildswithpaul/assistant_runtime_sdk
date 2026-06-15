# Assistant Runtime SDK - register_tenant Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for the standalone register_tenant function.

application_id is a required parameter end-to-end: a caller that forgets it
must fail fast at the SDK boundary, and when provided it must be forwarded in
the POST payload to AR.
"""

from unittest.mock import MagicMock, patch

import pytest

from assistant_runtime_sdk import register_tenant


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = {"message": payload}
    resp.raise_for_status.return_value = None
    return resp


class TestRegisterTenantApplicationId:
    def test_application_id_is_required(self):
        """Omitting application_id raises TypeError (required positional arg)."""
        with pytest.raises(TypeError):
            register_tenant(
                ar_url="https://ar.example.com",
                site_url="https://site.example.com",
                owner_email="owner@example.com",
            )

    def test_application_id_forwarded_in_payload(self):
        """application_id must be included in the POST payload sent to AR."""
        with patch("assistant_runtime_sdk.client.requests.post") as mock_post:
            mock_post.return_value = _mock_response({"tenant_id": "t-123"})

            register_tenant(
                ar_url="https://ar.example.com",
                site_url="https://site.example.com",
                owner_email="owner@example.com",
                application_id="faco",
                terms_accepted=True,
                terms_version="1.0",
                accepted_by="admin@example.com",
            )

            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs["json"]
            assert payload["application_id"] == "faco"
            assert payload["site_url"] == "https://site.example.com"
            assert payload["owner_email"] == "owner@example.com"

    def test_returns_ar_message_payload(self):
        """The function unwraps AR's {"message": ...} envelope on success."""
        with patch("assistant_runtime_sdk.client.requests.post") as mock_post:
            mock_post.return_value = _mock_response(
                {"tenant_id": "t-123", "verification_pending": True}
            )

            result = register_tenant(
                ar_url="https://ar.example.com",
                site_url="https://site.example.com",
                owner_email="owner@example.com",
                application_id="faco",
            )

            assert result["tenant_id"] == "t-123"
            assert result["verification_pending"] is True

# Assistant Runtime SDK - resend / change-email Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Request building and error surfacing for the pending-verification calls.

Both calls must carry the pending_token register_tenant returned: AR refuses
them without it. On failure they return AR's own message, not
``str(requests.HTTPError)`` ("417 Client Error: EXPECTATION FAILED for url: ..."),
which names nothing the admin can act on.
"""

import json
from unittest.mock import MagicMock, patch

import requests

from assistant_runtime_sdk import change_pending_owner_email, resend_owner_verification

AR = "https://ar.example.com/"
SITE = "https://site.example.com"


def _ok(payload):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"message": payload}
    return resp


def _frappe_error(status, message, exc_type="ValidationError"):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {
        "exc_type": exc_type,
        "_server_messages": json.dumps([json.dumps({"message": message})]),
    }
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"{status} Client Error: EXPECTATION FAILED for url: {AR}", response=resp
    )
    return resp


class TestResendOwnerVerification:
    def test_posts_site_and_pending_token(self):
        with patch("assistant_runtime_sdk.client.requests.post", return_value=_ok({"success": True})) as post:
            out = resend_owner_verification(AR, SITE, pending_token="tok")

        assert out == {"success": True}
        assert post.call_args.args[0] == (
            "https://ar.example.com/api/method/assistant_runtime.api.resend_owner_verification"
        )
        assert post.call_args.kwargs["json"] == {"site_url": SITE, "pending_token": "tok"}

    def test_returns_ars_message_on_http_error(self):
        resp = _frappe_error(403, "This request could not be confirmed.", "PermissionError")
        with patch("assistant_runtime_sdk.client.requests.post", return_value=resp):
            out = resend_owner_verification(AR, SITE, pending_token="tok")

        assert out["error"] == "This request could not be confirmed."
        assert out["status_code"] == 403
        assert out["exc_type"] == "PermissionError"
        assert "Client Error" not in out["error"]

    def test_network_error_keeps_an_error_string(self):
        with patch(
            "assistant_runtime_sdk.client.requests.post",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            out = resend_owner_verification(AR, SITE, pending_token="tok")

        assert "boom" in out["error"]
        assert out["status_code"] is None


class TestChangePendingOwnerEmail:
    def test_posts_site_address_and_pending_token(self):
        with patch("assistant_runtime_sdk.client.requests.post", return_value=_ok({"success": True})) as post:
            change_pending_owner_email(AR, SITE, "new@example.com", pending_token="tok")

        assert post.call_args.args[0].endswith("assistant_runtime.api.change_pending_owner_email")
        assert post.call_args.kwargs["json"] == {
            "site_url": SITE,
            "owner_email": "new@example.com",
            "pending_token": "tok",
        }

    def test_returns_ars_message_on_http_error(self):
        resp = _frappe_error(417, "A valid email address is required.")
        with patch("assistant_runtime_sdk.client.requests.post", return_value=resp):
            out = change_pending_owner_email(AR, SITE, "x", pending_token="tok")

        assert out == {
            "error": "A valid email address is required.",
            "status_code": 417,
            "exc_type": "ValidationError",
        }

    def test_non_json_error_body_falls_back_to_the_http_string(self):
        resp = _frappe_error(502, "unused")
        resp.json.side_effect = ValueError("not json")
        with patch("assistant_runtime_sdk.client.requests.post", return_value=resp):
            out = change_pending_owner_email(AR, SITE, "a@b.co", pending_token="tok")

        assert "502" in out["error"]
        assert out["status_code"] == 502

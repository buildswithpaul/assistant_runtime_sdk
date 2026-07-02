# Assistant Runtime SDK - get_registration_state Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

from unittest.mock import patch, MagicMock
from assistant_runtime_sdk import get_registration_state


def test_returns_message_payload():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"message": {"exists": True, "status": "Active"}}
    with patch("assistant_runtime_sdk.client.requests.post", return_value=resp):
        out = get_registration_state("https://ar.example.com", "https://site.example.com")
    assert out == {"exists": True, "status": "Active"}


def test_network_error_returns_error_dict():
    import requests
    with patch(
        "assistant_runtime_sdk.client.requests.post",
        side_effect=requests.exceptions.ConnectionError("boom"),
    ):
        out = get_registration_state("https://ar.example.com", "https://site.example.com")
    assert "error" in out

# Assistant Runtime SDK - Ticket Attachment SDK Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for ticket-attachment SDK helpers (multipart upload + attachment_ids threading)."""

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _client():
    return AssistantRuntimeClient(
        tenant_id="tid-1",
        tenant_secret="secret",
        ar_url="https://ar.example.com",
    )


def test_prepare_upload_ticket_attachment_returns_multipart_tuple():
    c = _client()
    result = c._prepare_upload_ticket_attachment(
        user_id="user@example.com",
        file_name="shot.png",
        file_data=b"\x89PNG\r\n\x1a\n",
        content_type="image/png",
    )
    assert len(result) == 6
    endpoint, params, file_field, file_name, file_data, content_type = result
    assert endpoint == "support.upload_ticket_attachment"
    assert params["tenant_id"] == "tid-1"
    assert params["user_id"] == "user@example.com"
    assert file_field == "file"
    assert file_name == "shot.png"
    assert file_data == b"\x89PNG\r\n\x1a\n"
    assert content_type == "image/png"


def test_prepare_upload_ticket_attachment_guesses_content_type_from_name():
    c = _client()
    _, _, _, _, _, content_type = c._prepare_upload_ticket_attachment(
        user_id="u", file_name="scan.pdf", file_data=b"%PDF-1.4",
    )
    assert content_type == "application/pdf"


def test_prepare_upload_ticket_attachment_defaults_octet_stream():
    c = _client()
    _, _, _, _, _, content_type = c._prepare_upload_ticket_attachment(
        user_id="u", file_name="weirdname", file_data=b"...",
    )
    assert content_type == "application/octet-stream"

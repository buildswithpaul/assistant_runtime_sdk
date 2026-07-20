# Assistant Runtime SDK - Ticket Attachment SDK Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for ticket-attachment SDK helpers (multipart upload + attachment_ids threading)."""

import asyncio
from unittest.mock import AsyncMock, patch as _patch

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _client():
    return AssistantRuntimeClient(
        tenant_id="tid-1",
        tenant_secret="secret",
        ar_url="https://ar.example.com",
    )


def _async_client():
    return AsyncAssistantRuntimeClient(
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


def test_upload_ticket_attachment_calls_multipart_on_core_base():
    from unittest.mock import patch

    c = _client()
    captured = {}

    def _fake_multipart(endpoint, params, file_field, file_name, file_data, content_type, timeout=None, api_base=None):
        captured.update(
            endpoint=endpoint, params=params, file_field=file_field,
            file_name=file_name, file_data=file_data, content_type=content_type,
            timeout=timeout, api_base=api_base,
        )
        return {"file_id": "file-1", "file_url": "/private/files/shot.png",
                "file_name": "shot.png", "is_image": True}

    with patch.object(c, "_request_post_multipart", side_effect=_fake_multipart):
        result = c.upload_ticket_attachment(
            user_id="user@example.com", file_name="shot.png",
            file_data=b"\x89PNG", content_type="image/png",
        )

    assert result["file_id"] == "file-1"
    assert result["is_image"] is True
    assert captured["endpoint"] == "support.upload_ticket_attachment"
    assert captured["file_field"] == "file"
    assert captured["file_name"] == "shot.png"
    assert captured["content_type"] == "image/png"
    assert captured["params"]["user_id"] == "user@example.com"
    # Support endpoints live on the CORE api_base, never the memory base.
    assert captured["api_base"] in (None, c.api_base)
    assert captured["api_base"] != c.memory_api_base


def test_async_upload_ticket_attachment_awaits_multipart():
    a = _async_client()

    async def _run():
        fake = AsyncMock(return_value={
            "file_id": "file-9", "file_url": "/private/files/scan.pdf",
            "file_name": "scan.pdf", "is_image": False,
        })
        with _patch.object(a, "_request_post_multipart", fake):
            result = await a.upload_ticket_attachment(
                user_id="u", file_name="scan.pdf", file_data=b"%PDF-1.4",
            )
        fake.assert_awaited_once()
        kwargs = fake.await_args.kwargs
        assert fake.await_args.args[0] == "support.upload_ticket_attachment"
        assert kwargs["file_field"] == "file"
        assert kwargs["content_type"] == "application/pdf"
        assert result["is_image"] is False

    asyncio.run(_run())

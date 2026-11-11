# Assistant Runtime SDK - AR_BUSY mapping tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""An HTTP 503 from AR means the admission gate refused the request.

It must surface as AR_BUSY with the server's Retry-After, never as a generic
REQUEST_ERROR / ARAPIError, so callers can back off instead of failing.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from assistant_runtime_sdk import (
    ARAPIError,
    ARRateLimitError,
    AssistantRuntimeClient,
)
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient
from assistant_runtime_sdk.base import _retry_after_from

BUSY = {
    "error": "The assistant is busy right now. Retrying shortly.",
    "error_code": "AR_BUSY",
    "retryable": True,
}


@pytest.fixture
def client():
    return AssistantRuntimeClient("t", "s", "https://ar.example.com")


def _sync_response(status_code, headers=None, body=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = body if body is not None else {}
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    response.iter_lines = MagicMock(return_value=iter([]))
    error = requests.exceptions.HTTPError(f"{status_code} error", response=response)
    response.raise_for_status = MagicMock(side_effect=error)
    return response


def test_stream_503_yields_ar_busy_with_retry_after(client):
    resp = _sync_response(503, {"Retry-After": "7"})
    with patch("assistant_runtime_sdk.client.requests.post", return_value=resp):
        events = list(client.stream_chat("s", "hi", "u@x"))
    assert events == [{"event": "stream_error", "data": {**BUSY, "retry_after": 7.0}}]
    resp.raise_for_status.assert_not_called()


def test_stream_503_without_header_defaults_to_5(client):
    resp = _sync_response(503)
    with patch("assistant_runtime_sdk.client.requests.post", return_value=resp):
        events = list(client.stream_chat("s", "hi", "u@x"))
    assert events[0]["data"]["retry_after"] == 5.0


def test_get_503_raises_rate_limit_with_retry_after(client):
    resp = _sync_response(503, {"Retry-After": "7"})
    with patch("assistant_runtime_sdk.client.requests.get", return_value=resp):
        with pytest.raises(ARRateLimitError) as e:
            client.list_available_models()
    assert e.value.retry_after == 7.0
    assert e.value.error_code == "AR_BUSY"
    assert isinstance(e.value.__cause__, requests.exceptions.HTTPError)


def test_post_503_raises_rate_limit(client):
    resp = _sync_response(503, {"Retry-After": "2"})
    with patch("assistant_runtime_sdk.client.requests.post", return_value=resp):
        with pytest.raises(ARRateLimitError) as e:
            client.accept_terms("v1", "u@x")
    assert e.value.retry_after == 2.0


def test_500_still_maps_to_api_error(client):
    resp = _sync_response(500)
    with patch("assistant_runtime_sdk.client.requests.get", return_value=resp):
        with pytest.raises(ARAPIError) as e:
            client.list_available_models()
    assert e.value.status_code == 500


def test_rate_limit_error_default_code_unchanged():
    assert ARRateLimitError("x").error_code == "RATE_LIMITED"


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"Retry-After": "7"}, 7.0),
        ({"Retry-After": "abc"}, 5.0),
        ({"Retry-After": "nan"}, 5.0),
        ({"Retry-After": "inf"}, 5.0),
        ({"Retry-After": "-3"}, 5.0),
        ({"Retry-After": "0"}, 0.0),
        ({}, 5.0),
    ],
)
def test_retry_after_from(headers, expected):
    assert _retry_after_from(headers) == expected


def _async_response(status, headers=None):
    response = MagicMock()
    response.status = status
    response.headers = headers or {}
    response.json = AsyncMock(return_value={})
    response.raise_for_status = MagicMock(side_effect=AssertionError("must not be called"))
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def _async_client(response, method):
    async_client = AsyncAssistantRuntimeClient("t", "s", "https://ar.example.com")
    session = MagicMock()
    setattr(session, method, MagicMock(return_value=response))
    async_client._session = session
    return async_client


def test_async_stream_503_yields_ar_busy():
    async_client = _async_client(_async_response(503, {"Retry-After": "7"}), "post")

    async def run():
        return [e async for e in async_client.stream_chat("s", "hi", "u@x")]

    events = asyncio.run(run())
    assert events == [{"event": "stream_error", "data": {**BUSY, "retry_after": 7.0}}]


def test_async_get_503_raises_rate_limit():
    async_client = _async_client(_async_response(503, {"Retry-After": "7"}), "get")
    with pytest.raises(ARRateLimitError) as e:
        asyncio.run(async_client.list_available_models())
    assert e.value.retry_after == 7.0
    assert e.value.error_code == "AR_BUSY"

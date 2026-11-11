# Assistant Runtime SDK - HTTP error log level tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""A 404 from AR is an expected answer (e.g. user not found): WARNING, not ERROR."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from assistant_runtime_sdk import ARAPIError, AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


@pytest.fixture
def client():
    return AssistantRuntimeClient("t", "s", "https://ar.example.com")


def _response(status_code):
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    response.json.return_value = {}
    response.raise_for_status = MagicMock(
        side_effect=requests.exceptions.HTTPError(f"{status_code} error", response=response)
    )
    return response


def _levels(caplog):
    return {r.levelno for r in caplog.records if r.name.startswith("assistant_runtime_sdk")}


def test_sync_get_404_logs_warning_not_error(client, caplog):
    with patch("assistant_runtime_sdk.client.requests.get", return_value=_response(404)):
        with caplog.at_level(logging.DEBUG), pytest.raises(ARAPIError):
            client.list_available_models()
    assert _levels(caplog) == {logging.WARNING}


def test_sync_post_404_logs_warning_not_error(client, caplog):
    with patch("assistant_runtime_sdk.client.requests.post", return_value=_response(404)):
        with caplog.at_level(logging.DEBUG), pytest.raises(ARAPIError):
            client.accept_terms("v1", "u@x")
    assert _levels(caplog) == {logging.WARNING}


@pytest.mark.parametrize("status", [400, 500])
def test_sync_other_http_errors_stay_at_error(client, caplog, status):
    with patch("assistant_runtime_sdk.client.requests.get", return_value=_response(status)):
        with caplog.at_level(logging.DEBUG), pytest.raises(ARAPIError):
            client.list_available_models()
    assert logging.ERROR in _levels(caplog)


def test_async_404_is_not_logged_at_error(caplog):
    response = MagicMock()
    response.status = 404
    response.headers = {}
    response.json = AsyncMock(return_value={})
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    async_client = AsyncAssistantRuntimeClient("t", "s", "https://ar.example.com")
    session = MagicMock()
    session.get = MagicMock(return_value=response)
    async_client._session = session

    async def run():
        await async_client.list_available_models()

    with caplog.at_level(logging.DEBUG), pytest.raises(ARAPIError):
        asyncio.run(run())
    assert logging.ERROR not in _levels(caplog)

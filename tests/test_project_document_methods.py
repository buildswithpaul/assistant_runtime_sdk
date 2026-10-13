# Assistant Runtime SDK - Project Document Method Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Project-document parameters on the document methods, in both clients."""

import asyncio
import inspect
from unittest.mock import patch

import pytest

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.exceptions import ARConfigurationError
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


def _client():
    return AssistantRuntimeClient(
        tenant_id="t1", tenant_secret="s", ar_url="http://ar.test"
    )


def test_upload_sends_project_id_and_no_visibility():
    endpoint, params, *_ = _client()._prepare_upload_document(
        file_data=b"x", file_name="a.txt", user_id="u1",
        visibility="public", project_id="p1",
    )
    assert endpoint == "documents.upload_document"
    assert params["project_id"] == "p1"
    # The server forces private for project documents.
    assert "visibility" not in params


def test_upload_without_project_is_unchanged():
    _, params, *_ = _client()._prepare_upload_document(
        file_data=b"x", file_name="a.txt", user_id="u1"
    )
    assert "project_id" not in params


def test_list_documents_project_params():
    endpoint, params = _client()._prepare_list_documents(user_id="u1", project_id="p1")
    assert endpoint == "documents.list_documents"
    assert params["project_id"] == "p1"

    _, params = _client()._prepare_list_documents(user_id="u1", include_project_docs=True)
    assert params["include_project_docs"] == "1"

    _, params = _client()._prepare_list_documents(user_id="u1")
    assert "project_id" not in params and "include_project_docs" not in params


def test_unlink_payload():
    endpoint, payload = _client()._prepare_unlink_project_documents(
        user_id="u1", project_id="p1"
    )
    assert endpoint == "documents.unlink_project_documents"
    assert payload == {"tenant_id": "t1", "user_id": "u1", "project_id": "p1"}


@pytest.mark.parametrize(
    "name", ["upload_document", "list_documents", "unlink_project_documents"]
)
def test_sync_and_async_signatures_match(name):
    sync = inspect.signature(getattr(AssistantRuntimeClient, name))
    asyn = inspect.signature(getattr(AsyncAssistantRuntimeClient, name))
    assert list(sync.parameters) == list(asyn.parameters)
    assert inspect.iscoroutinefunction(getattr(AsyncAssistantRuntimeClient, name))


def test_upload_with_project_requires_user():
    with pytest.raises(ARConfigurationError, match="user_id is required with project_id"):
        _client()._prepare_upload_document(
            file_data=b"x", file_name="a.txt", project_id="p1"
        )


def test_list_with_project_requires_user():
    with pytest.raises(ARConfigurationError, match="user_id is required with project_id"):
        _client()._prepare_list_documents(project_id="p1")


def test_sync_unlink_posts_to_the_memory_api():
    client = _client()
    with patch.object(
        AssistantRuntimeClient, "_request_post_json", autospec=True
    ) as post:
        client.unlink_project_documents("u1", "p1")
    post.assert_called_once_with(
        client,
        "documents.unlink_project_documents",
        {"tenant_id": "t1", "user_id": "u1", "project_id": "p1"},
        api_base=client.memory_api_base,
    )


def test_async_unlink_posts_to_the_memory_api():
    client = AsyncAssistantRuntimeClient(
        tenant_id="t1", tenant_secret="s", ar_url="http://ar.test"
    )
    with patch.object(
        AsyncAssistantRuntimeClient, "_request_post_json", autospec=True
    ) as post:
        asyncio.run(client.unlink_project_documents("u1", "p1"))
    post.assert_called_once_with(
        client,
        "documents.unlink_project_documents",
        {"tenant_id": "t1", "user_id": "u1", "project_id": "p1"},
        api_base=client.memory_api_base,
    )

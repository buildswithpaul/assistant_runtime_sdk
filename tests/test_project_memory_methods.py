# Assistant Runtime SDK - Project Memory Method Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Project-memory parameters and delete_project_memories, in both clients."""

import asyncio
import inspect
from unittest.mock import patch

import pytest

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient
from assistant_runtime_sdk.exceptions import ARConfigurationError

_KWARGS = {"tenant_id": "t1", "tenant_secret": "s", "ar_url": "http://ar.test"}
_DELETE_PAYLOAD = {"tenant_id": "t1", "user_id": "u1", "project_id": "p1"}


def _client():
    return AssistantRuntimeClient(**_KWARGS)


def _async_client():
    return AsyncAssistantRuntimeClient(**_KWARGS)


def test_list_memories_sends_project_id_when_set():
    endpoint, params = _client()._prepare_list_memories(user_id="u1", project_id="p1")
    assert endpoint == "memories.list_memories"
    assert params == {
        "tenant_id": "t1", "limit": "50", "offset": "0",
        "user_id": "u1", "project_id": "p1",
    }


def test_list_memories_omits_project_id_when_not_given():
    _, params = _client()._prepare_list_memories(user_id="u1")
    assert "project_id" not in params


def test_list_memories_project_requires_user():
    with pytest.raises(ARConfigurationError, match="user_id is required with project_id"):
        _client()._prepare_list_memories(project_id="p1")


def test_delete_project_memories_payload():
    endpoint, payload = _client()._prepare_delete_project_memories("u1", "p1")
    assert endpoint == "memories.delete_project_memories"
    assert payload == _DELETE_PAYLOAD


def test_delete_project_memories_sends_project_deleted_only_when_true():
    _, cleared = _client()._prepare_delete_project_memories("u1", "p1", project_deleted=False)
    _, deleted = _client()._prepare_delete_project_memories("u1", "p1", project_deleted=True)
    assert cleared == _DELETE_PAYLOAD
    assert deleted == {**_DELETE_PAYLOAD, "project_deleted": "1"}


def test_sync_delete_project_memories_forwards_project_deleted():
    client = _client()
    with patch.object(AssistantRuntimeClient, "_request_post_json", autospec=True) as post:
        client.delete_project_memories("u1", "p1", project_deleted=True)
    post.assert_called_once_with(
        client,
        "memories.delete_project_memories",
        {**_DELETE_PAYLOAD, "project_deleted": "1"},
        api_base=client.memory_api_base,
    )


def test_async_delete_project_memories_forwards_project_deleted():
    client = _async_client()
    with patch.object(AsyncAssistantRuntimeClient, "_request_post_json", autospec=True) as post:
        asyncio.run(client.delete_project_memories("u1", "p1", project_deleted=True))
    post.assert_called_once_with(
        client,
        "memories.delete_project_memories",
        {**_DELETE_PAYLOAD, "project_deleted": "1"},
        api_base=client.memory_api_base,
    )


@pytest.mark.parametrize("user_id,project_id", [("", "p1"), ("u1", ""), ("", ""), (None, "p1")])
def test_delete_project_memories_requires_both_ids_before_any_request(user_id, project_id):
    client = _client()
    with patch.object(AssistantRuntimeClient, "_request_post_json", autospec=True) as post:
        with pytest.raises(ARConfigurationError):
            client.delete_project_memories(user_id, project_id)
    post.assert_not_called()


def test_async_delete_project_memories_requires_both_ids_before_any_request():
    client = _async_client()
    with patch.object(AsyncAssistantRuntimeClient, "_request_post_json", autospec=True) as post:
        with pytest.raises(ARConfigurationError):
            asyncio.run(client.delete_project_memories("", "p1"))
    post.assert_not_called()


def test_sync_list_memories_gets_from_the_memory_api():
    client = _client()
    with patch.object(AssistantRuntimeClient, "_request_get", autospec=True) as get:
        client.list_memories(user_id="u1", project_id="p1", limit=10, offset=20)
    get.assert_called_once_with(
        client,
        "memories.list_memories",
        {"tenant_id": "t1", "limit": "10", "offset": "20", "user_id": "u1", "project_id": "p1"},
        api_base=client.memory_api_base,
    )


def test_sync_list_memories_without_project_sends_no_project_id():
    client = _client()
    with patch.object(AssistantRuntimeClient, "_request_get", autospec=True) as get:
        client.list_memories(user_id="u1")
    assert "project_id" not in get.call_args.args[2]


def test_async_list_memories_gets_from_the_memory_api():
    client = _async_client()
    with patch.object(AsyncAssistantRuntimeClient, "_request_get", autospec=True) as get:
        asyncio.run(client.list_memories(user_id="u1", project_id="p1"))
    get.assert_called_once_with(
        client,
        "memories.list_memories",
        {"tenant_id": "t1", "limit": "50", "offset": "0", "user_id": "u1", "project_id": "p1"},
        api_base=client.memory_api_base,
    )


def test_async_list_memories_without_project_sends_no_project_id():
    client = _async_client()
    with patch.object(AsyncAssistantRuntimeClient, "_request_get", autospec=True) as get:
        asyncio.run(client.list_memories(user_id="u1"))
    assert "project_id" not in get.call_args.args[2]


def test_sync_delete_project_memories_posts_to_the_memory_api():
    client = _client()
    with patch.object(AssistantRuntimeClient, "_request_post_json", autospec=True) as post:
        client.delete_project_memories("u1", "p1")
    post.assert_called_once_with(
        client,
        "memories.delete_project_memories",
        _DELETE_PAYLOAD,
        api_base=client.memory_api_base,
    )


def test_async_delete_project_memories_posts_to_the_memory_api():
    client = _async_client()
    with patch.object(AsyncAssistantRuntimeClient, "_request_post_json", autospec=True) as post:
        asyncio.run(client.delete_project_memories("u1", "p1"))
    post.assert_called_once_with(
        client,
        "memories.delete_project_memories",
        _DELETE_PAYLOAD,
        api_base=client.memory_api_base,
    )


@pytest.mark.parametrize("name", ["list_memories", "delete_project_memories"])
def test_sync_and_async_signatures_match(name):
    sync = inspect.signature(getattr(AssistantRuntimeClient, name))
    asyn = inspect.signature(getattr(AsyncAssistantRuntimeClient, name))
    assert list(sync.parameters) == list(asyn.parameters)
    assert inspect.iscoroutinefunction(getattr(AsyncAssistantRuntimeClient, name))

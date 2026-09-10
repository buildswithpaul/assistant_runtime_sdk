# Assistant Runtime SDK - MCP server method tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Regression tests for three latent bugs in the user MCP server methods:

1. ``_prepare_add_user_mcp_server`` defaulted ``transport_type`` to "SSE",
   but AR's doctype Select field only permits "HTTP" — the default itself
   would raise a Frappe ValidationError if a caller ever omitted it. The
   public ``add_user_mcp_server`` wrappers on ``client.py``/``async_client.py``
   independently redeclare the same default in their own signatures and pass
   it down positionally, so both layers need the fix — the internal helper
   default alone is shadowed for every real caller of the public API.
2. ``allowed_tools``/``blocked_tools`` were JSON-encoded to strings, but
   AR's endpoint annotates them as ``list`` and Frappe's lax pydantic
   validation does not parse a JSON string into a list.
3. ``get_user_mcp_servers`` collapsed every exception into
   ``{"mcp_servers": [], "error": str(e)}``, indistinguishable from a user
   who genuinely has no servers. It now adds the same ``_ar_unreachable``
   marker ``get_user_auth_status`` uses.
"""

import unittest
from unittest.mock import patch

from assistant_runtime_sdk.base import BaseAssistantRuntimeClient
from assistant_runtime_sdk.client import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


class TestAddUserMCPServerParams(unittest.TestCase):
    def setUp(self):
        self.client = BaseAssistantRuntimeClient(ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s")

    def test_transport_type_defaults_to_http(self):
        # The AR User MCP Server Select permits only "HTTP"; the old "SSE"
        # default would raise a Frappe ValidationError at AR.
        _, params = self.client._prepare_add_user_mcp_server(
            user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp"
        )
        self.assertEqual(params["transport_type"], "HTTP")

    def test_tool_lists_are_not_json_encoded(self):
        # AR annotates these params as `list`; Frappe's lax pydantic validation
        # does not parse a JSON string into a list, so a str raises
        # FrappeTypeError.
        _, params = self.client._prepare_add_user_mcp_server(
            user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp",
            allowed_tools=["a"], blocked_tools=["b"],
        )
        self.assertEqual(params["allowed_tools"], ["a"])
        self.assertEqual(params["blocked_tools"], ["b"])

    def test_tool_lists_omitted_when_empty(self):
        _, params = self.client._prepare_add_user_mcp_server(
            user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp"
        )
        self.assertNotIn("allowed_tools", params)
        self.assertNotIn("blocked_tools", params)


class TestPublicAddUserMCPServerDefaults(unittest.TestCase):
    """Exercises the PUBLIC add_user_mcp_server wrappers, not the internal
    _prepare_* helper — the wrappers redeclare transport_type's default in
    their own signatures, so fixing base.py alone does not fix this for a
    real caller who omits transport_type when calling client.add_user_mcp_server(...).
    """

    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_omitted_transport_type_sends_http(self):
        with patch.object(self.client, "_request_post_form", return_value={}) as mock_post:
            self.client.add_user_mcp_server(
                user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp"
            )

        _, params = mock_post.call_args.args
        self.assertEqual(params["transport_type"], "HTTP")


class TestAsyncPublicAddUserMCPServerDefaults(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    async def test_omitted_transport_type_sends_http(self):
        async def _ok(*args, **kwargs):
            return {}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            await self.client.add_user_mcp_server(
                user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp"
            )

        _, params = mock_post.call_args.args
        self.assertEqual(params["transport_type"], "HTTP")


class TestGetUserMCPServersUnreachableMarker(unittest.TestCase):
    """Mirrors get_user_auth_status's _ar_unreachable contract (client.py:1975-1995)."""

    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_transport_failure_sets_ar_unreachable(self):
        with patch.object(self.client, "_request_get", side_effect=ConnectionError("boom")):
            result = self.client.get_user_mcp_servers("u@example.com")

        self.assertTrue(result["_ar_unreachable"])
        self.assertEqual(result["error"], "boom")
        self.assertEqual(result["mcp_servers"], [])

    def test_success_has_no_unreachable_marker(self):
        with patch.object(self.client, "_request_get", return_value={"user_id": "u@example.com", "mcp_servers": []}):
            result = self.client.get_user_mcp_servers("u@example.com")

        self.assertNotIn("_ar_unreachable", result)


class TestAsyncGetUserMCPServersUnreachableMarker(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    async def test_transport_failure_sets_ar_unreachable(self):
        async def _raise(*args, **kwargs):
            raise ConnectionError("boom")

        with patch.object(self.client, "_request_get", side_effect=_raise):
            result = await self.client.get_user_mcp_servers("u@example.com")

        self.assertTrue(result["_ar_unreachable"])
        self.assertEqual(result["error"], "boom")
        self.assertEqual(result["mcp_servers"], [])


if __name__ == "__main__":
    unittest.main()

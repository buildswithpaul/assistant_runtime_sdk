# Assistant Runtime SDK - MCP server method tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Regression tests for three latent bugs in the user MCP server methods, plus
one new capability (4):

1. ``_prepare_add_user_mcp_server`` defaulted ``transport_type`` to "SSE",
   but AR's doctype Select field only permits "HTTP" — the default itself
   would raise a Frappe ValidationError if a caller ever omitted it. The
   public ``add_user_mcp_server`` wrappers on ``client.py``/``async_client.py``
   independently redeclare the same default in their own signatures and pass
   it down positionally, so both layers need the fix — the internal helper
   default alone is shadowed for every real caller of the public API.
2. ``allowed_tools``/``blocked_tools`` must be sent JSON-encoded, matching
   this SDK's own established convention for every other list-shaped param
   on this signed-form transport (``shared_with``, ``add_users``,
   ``remove_users`` in base.py). A real Python list survives neither
   ``requests``' form encoding (becomes repeated keys) nor the SDK's own
   HMAC signing (which stringifies a list with ``str(v)``) intact, so the
   signature AR reconstructs from the wire never matches what was signed —
   an ``AuthenticationError``, before AR's own type validation ever runs.
   AR's receiving side was the actual bug: it annotated the param ``list``
   and expected one to arrive, which this transport can never deliver.
3. ``get_user_mcp_servers`` collapsed every exception into
   ``{"mcp_servers": [], "error": str(e)}``, indistinguishable from a user
   who genuinely has no servers. It now adds the same ``_ar_unreachable``
   marker ``get_user_auth_status`` uses.
4. ``add_user_mcp_server`` now carries a ``managed`` flag (bool -> "1"/"0"),
   matching this SDK's stringify-all-scalars convention. AR's endpoint still
   accepts the param but derives the authoritative value server-side, so
   this is API completeness, not a trust decision made by the SDK.
5. ``enable_mcp_server`` is new: AR's endpoint has zero callers today, so the
   only way to turn a server off was to delete it. Its path is the same
   short suffix every other ``_prepare_*`` here uses (see
   ``_prepare_remove_user_mcp_server``'s ``"users.remove_user_mcp_server"``,
   or ``test_routing_preference_methods.py``'s ``"routing_preferences.*"``)
   — ``_build_endpoint_url`` already prepends ``assistant_runtime.api``, so
   a path repeating that prefix would double it into an endpoint AR never
   registers.
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

    def test_tool_lists_are_json_encoded(self):
        # A real list would arrive at AR with a signature AR can never
        # reconstruct (requests form-encodes a list as repeated keys, which
        # collapse to one value; the SDK signs str(list) instead). JSON
        # strings survive form encoding and signing unchanged, matching this
        # SDK's own convention for every other list-shaped param on this
        # transport (shared_with, add_users, remove_users).
        _, params = self.client._prepare_add_user_mcp_server(
            user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp",
            allowed_tools=["a"], blocked_tools=["b"],
        )
        self.assertEqual(params["allowed_tools"], '["a"]')
        self.assertEqual(params["blocked_tools"], '["b"]')

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


class TestManagedFlag(unittest.TestCase):
    def setUp(self):
        self.client = BaseAssistantRuntimeClient(ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s")

    def test_managed_defaults_to_zero(self):
        _, params = self.client._prepare_add_user_mcp_server(
            user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp"
        )
        self.assertEqual(params["managed"], "0")

    def test_managed_true_is_sent_as_one(self):
        _, params = self.client._prepare_add_user_mcp_server(
            user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp",
            managed=True,
        )
        self.assertEqual(params["managed"], "1")


class TestPublicAddUserMCPServerManagedFlag(unittest.TestCase):
    """The public wrapper must forward managed through to AR — a real caller
    only ever reaches this via client.add_user_mcp_server(...), never the
    internal _prepare_* helper.
    """

    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_managed_true_is_forwarded(self):
        with patch.object(self.client, "_request_post_form", return_value={}) as mock_post:
            self.client.add_user_mcp_server(
                user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp",
                managed=True,
            )

        _, params = mock_post.call_args.args
        self.assertEqual(params["managed"], "1")


class TestAsyncPublicAddUserMCPServerManagedFlag(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    async def test_managed_true_is_forwarded(self):
        async def _ok(*args, **kwargs):
            return {}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            await self.client.add_user_mcp_server(
                user_id="u@example.com", server_name="S", endpoint_url="https://x/mcp",
                managed=True,
            )

        _, params = mock_post.call_args.args
        self.assertEqual(params["managed"], "1")


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


class TestEnableMCPServer(unittest.TestCase):
    def setUp(self):
        self.client = BaseAssistantRuntimeClient(ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s")

    def test_targets_the_right_endpoint(self):
        path, params = self.client._prepare_enable_mcp_server(
            user_id="u@example.com", server_name="Acme", enabled=False
        )
        self.assertEqual(path, "users.enable_mcp_server")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(params["enabled"], "0")

    def test_enabled_defaults_true(self):
        _, params = self.client._prepare_enable_mcp_server(
            user_id="u@example.com", server_name="Acme"
        )
        self.assertEqual(params["enabled"], "1")


class TestPublicEnableMCPServer(unittest.TestCase):
    """Exercises the PUBLIC enable_mcp_server wrapper, not the internal
    _prepare_* helper directly — a real caller only ever reaches this via
    client.enable_mcp_server(...). An internal-helper-only test would have
    missed a wrapper that forgot to forward its arguments or called the
    wrong transport method.
    """

    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_disable_is_forwarded(self):
        with patch.object(self.client, "_request_post_form", return_value={}) as mock_post:
            self.client.enable_mcp_server(
                user_id="u@example.com", server_name="Acme", enabled=False
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "users.enable_mcp_server")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(params["enabled"], "0")


class TestAsyncPublicEnableMCPServer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    async def test_disable_is_forwarded(self):
        async def _ok(*args, **kwargs):
            return {}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            await self.client.enable_mcp_server(
                user_id="u@example.com", server_name="Acme", enabled=False
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "users.enable_mcp_server")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(params["enabled"], "0")


class TestTestMCPServer(unittest.TestCase):
    """``test_mcp_server`` opens a real MCP session at AR and reports what the
    server exposes — same short-suffix path precedent as every other
    ``_prepare_*`` here (see ``_prepare_remove_user_mcp_server``'s
    ``"users.remove_user_mcp_server"``); ``_build_endpoint_url`` already
    prepends ``assistant_runtime.api``.
    """

    def setUp(self):
        self.client = BaseAssistantRuntimeClient(ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s")

    def test_targets_the_right_endpoint(self):
        path, params = self.client._prepare_test_mcp_server(
            user_id="u@example.com", server_name="Acme"
        )
        self.assertEqual(path, "users.test_mcp_server")
        self.assertEqual(params["tenant_id"], "t")
        self.assertEqual(params["user_id"], "u@example.com")
        self.assertEqual(params["server_name"], "Acme")


class TestPublicTestMCPServer(unittest.TestCase):
    """Exercises the PUBLIC test_mcp_server wrapper, not the internal
    _prepare_* helper directly — a real caller only ever reaches this via
    client.test_mcp_server(...).
    """

    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_forwards_to_post_form_and_returns_result(self):
        with patch.object(
            self.client, "_request_post_form",
            return_value={"success": True, "tool_count": 2, "tools": ["send", "search"], "error": None},
        ) as mock_post:
            result = self.client.test_mcp_server(user_id="u@example.com", server_name="Acme")

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "users.test_mcp_server")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(result["tool_count"], 2)
        self.assertEqual(result["tools"], ["send", "search"])


class TestAsyncPublicTestMCPServer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    async def test_forwards_to_post_form_and_returns_result(self):
        async def _ok(*args, **kwargs):
            return {"success": False, "tool_count": 0, "tools": [], "error": "connection refused"}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            result = await self.client.test_mcp_server(user_id="u@example.com", server_name="Acme")

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "users.test_mcp_server")
        self.assertEqual(params["server_name"], "Acme")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "connection refused")


class TestSetMCPServerTools(unittest.TestCase):
    """``set_mcp_server_tools`` is a targeted tool-visibility write, distinct
    from ``add_user_mcp_server``'s upsert — it must not touch enabled,
    status, or credentials. Tool lists share the same JSON-encoding
    requirement as every other list-shaped param on this signed-form
    transport (see TestAddUserMCPServerParams above).
    """

    def setUp(self):
        self.client = BaseAssistantRuntimeClient(ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s")

    def test_targets_the_right_endpoint(self):
        path, params = self.client._prepare_set_mcp_server_tools(
            user_id="u@example.com", server_name="Acme", blocked_tools=["delete_all"],
        )
        self.assertEqual(path, "users.set_mcp_server_tools")
        self.assertEqual(params["tenant_id"], "t")
        self.assertEqual(params["user_id"], "u@example.com")
        self.assertEqual(params["server_name"], "Acme")

    def test_tool_lists_are_json_encoded(self):
        _, params = self.client._prepare_set_mcp_server_tools(
            user_id="u@example.com", server_name="Acme",
            allowed_tools=["a"], blocked_tools=["b"],
        )
        self.assertEqual(params["allowed_tools"], '["a"]')
        self.assertEqual(params["blocked_tools"], '["b"]')

    def test_tool_lists_omitted_when_empty(self):
        _, params = self.client._prepare_set_mcp_server_tools(
            user_id="u@example.com", server_name="Acme",
        )
        self.assertNotIn("allowed_tools", params)
        self.assertNotIn("blocked_tools", params)


class TestPublicSetMCPServerTools(unittest.TestCase):
    """Exercises the PUBLIC set_mcp_server_tools wrapper, not the internal
    _prepare_* helper directly — a real caller only ever reaches this via
    client.set_mcp_server_tools(...).
    """

    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_forwards_to_post_form_and_returns_result(self):
        with patch.object(
            self.client, "_request_post_form", return_value={"success": True},
        ) as mock_post:
            result = self.client.set_mcp_server_tools(
                user_id="u@example.com", server_name="Acme", blocked_tools=["delete_all"],
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "users.set_mcp_server_tools")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(params["blocked_tools"], '["delete_all"]')
        self.assertTrue(result["success"])


class TestAsyncPublicSetMCPServerTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    async def test_forwards_to_post_form_and_returns_result(self):
        async def _ok(*args, **kwargs):
            return {"success": True}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            result = await self.client.set_mcp_server_tools(
                user_id="u@example.com", server_name="Acme", blocked_tools=["delete_all"],
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "users.set_mcp_server_tools")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(params["blocked_tools"], '["delete_all"]')
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()

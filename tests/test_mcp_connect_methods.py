# Assistant Runtime SDK - MCP Connect wizard method tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Request builders for AR's MCP Connect endpoints (assistant_runtime.api.mcp_oauth).

Path convention: ``_build_endpoint_url`` (base.py:223-233) already prepends
``assistant_runtime.api``, so the suffix here is ``mcp_oauth.<method>``. A path
that repeated the prefix would double it into an endpoint AR never registers —
the same trap documented in test_mcp_methods.py for ``users.*``.

Every scalar is stringified before signing, matching this transport's
established convention (see ``_prepare_enable_mcp_server``'s "1"/"0").
"""

import unittest

from assistant_runtime_sdk.base import BaseAssistantRuntimeClient


class TestBeginMCPConnectParams(unittest.TestCase):
    def setUp(self):
        self.client = BaseAssistantRuntimeClient(
            ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s"
        )

    def test_targets_the_mcp_oauth_module(self):
        path, params = self.client._prepare_begin_mcp_connect(
            user_id="u@example.com", endpoint_url="https://acme.example/mcp"
        )
        self.assertEqual(path, "mcp_oauth.begin_mcp_connect")
        self.assertEqual(params["tenant_id"], "t")
        self.assertEqual(params["user_id"], "u@example.com")
        self.assertEqual(params["endpoint_url"], "https://acme.example/mcp")

    def test_manual_credentials_are_omitted_when_absent(self):
        # The DCR path sends neither. A blank string on the wire would make AR
        # persist an empty client_id and set registration_kind="manual".
        _, params = self.client._prepare_begin_mcp_connect(
            user_id="u@example.com", endpoint_url="https://acme.example/mcp"
        )
        self.assertNotIn("client_id", params)
        self.assertNotIn("client_secret", params)

    def test_manual_credentials_are_forwarded_when_supplied(self):
        _, params = self.client._prepare_begin_mcp_connect(
            user_id="u@example.com",
            endpoint_url="https://acme.example/mcp",
            client_id="cid-123",
            client_secret="shh",
        )
        self.assertEqual(params["client_id"], "cid-123")
        self.assertEqual(params["client_secret"], "shh")


class TestGetMCPConnectSessionParams(unittest.TestCase):
    def setUp(self):
        self.client = BaseAssistantRuntimeClient(
            ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s"
        )

    def test_targets_the_right_endpoint(self):
        path, params = self.client._prepare_get_mcp_connect_session(
            user_id="u@example.com", handle="h-abc"
        )
        self.assertEqual(path, "mcp_oauth.get_mcp_connect_session")
        self.assertEqual(params["handle"], "h-abc")


class TestCommitMCPConnectParams(unittest.TestCase):
    def setUp(self):
        self.client = BaseAssistantRuntimeClient(
            ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s"
        )

    def test_targets_the_right_endpoint(self):
        path, params = self.client._prepare_commit_mcp_connect(
            user_id="u@example.com", handle="h-abc", server_name="Acme"
        )
        self.assertEqual(path, "mcp_oauth.commit_mcp_connect")
        self.assertEqual(params["handle"], "h-abc")
        self.assertEqual(params["server_name"], "Acme")


class TestAbandonMCPConnectParams(unittest.TestCase):
    def setUp(self):
        self.client = BaseAssistantRuntimeClient(
            ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s"
        )

    def test_targets_the_right_endpoint(self):
        path, params = self.client._prepare_abandon_mcp_connect(
            user_id="u@example.com", handle="h-abc"
        )
        self.assertEqual(path, "mcp_oauth.abandon_mcp_connect")
        self.assertEqual(params["handle"], "h-abc")


class TestBeginMCPReauthParams(unittest.TestCase):
    """Re-authorization is its own endpoint, not begin_mcp_connect with a name.

    AR opens the session with reauth_target set to the existing row, so commit
    updates that row's credentials in place instead of inserting a second row
    and tripping the duplicate-name guard.
    """

    def setUp(self):
        self.client = BaseAssistantRuntimeClient(
            ar_url="https://ar.example.com", tenant_id="t", tenant_secret="s"
        )

    def test_targets_the_reauth_endpoint_and_carries_the_server_name(self):
        path, params = self.client._prepare_begin_mcp_reauth(
            user_id="u@example.com", server_name="Acme"
        )
        self.assertEqual(path, "mcp_oauth.begin_mcp_reauth")
        self.assertEqual(params["tenant_id"], "t")
        self.assertEqual(params["user_id"], "u@example.com")
        self.assertEqual(params["server_name"], "Acme")

    def test_it_sends_no_endpoint_url(self):
        # AR already knows the URL — it is on the row being re-authorized.
        # Sending one would invite a silent retarget of an existing connection.
        _, params = self.client._prepare_begin_mcp_reauth(
            user_id="u@example.com", server_name="Acme"
        )
        self.assertNotIn("endpoint_url", params)


import inspect
from unittest.mock import patch

from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient
from assistant_runtime_sdk.client import AssistantRuntimeClient

CONNECT_METHODS = (
    "begin_mcp_connect",
    "get_mcp_connect_session",
    "commit_mcp_connect",
    "abandon_mcp_connect",
    "begin_mcp_reauth",
)


class TestPublicBeginMCPConnect(unittest.TestCase):
    """Exercises the PUBLIC wrapper, not the internal _prepare_* helper — a real
    caller only ever reaches this via client.begin_mcp_connect(...). A wrapper
    that forgot to forward an argument, or called the wrong transport, would
    survive a helper-only test.
    """

    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_posts_the_form_and_returns_the_payload(self):
        with patch.object(
            self.client, "_request_post_form",
            return_value={"handle": "h-1", "session": "S-1", "preflight": {}, "authorize_url": None},
        ) as mock_post:
            result = self.client.begin_mcp_connect(
                endpoint_url="https://acme.example/mcp", user_id="u@example.com"
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.begin_mcp_connect")
        self.assertEqual(params["endpoint_url"], "https://acme.example/mcp")
        self.assertEqual(result["handle"], "h-1")

    def test_manual_credentials_reach_the_wire(self):
        with patch.object(self.client, "_request_post_form", return_value={}) as mock_post:
            self.client.begin_mcp_connect(
                endpoint_url="https://acme.example/mcp",
                user_id="u@example.com",
                client_id="cid-123",
                client_secret="shh",
            )

        _, params = mock_post.call_args.args
        self.assertEqual(params["client_id"], "cid-123")
        self.assertEqual(params["client_secret"], "shh")


class TestPublicGetMCPConnectSession(unittest.TestCase):
    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_reads_over_get_not_post(self):
        # AR declares this endpoint GET-only. A POST would 404 at Frappe's
        # method router; a write sent over the wrong verb is silently rolled back.
        with patch.object(
            self.client, "_request_get", return_value={"status": "Authorized"}
        ) as mock_get:
            result = self.client.get_mcp_connect_session(
                handle="h-1", user_id="u@example.com"
            )

        endpoint, params = mock_get.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.get_mcp_connect_session")
        self.assertEqual(params["handle"], "h-1")
        self.assertEqual(result["status"], "Authorized")


class TestPublicCommitAndAbandon(unittest.TestCase):
    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_commit_forwards_the_server_name(self):
        with patch.object(
            self.client, "_request_post_form", return_value={"success": True, "server_name": "Acme"}
        ) as mock_post:
            result = self.client.commit_mcp_connect(
                handle="h-1", server_name="Acme", user_id="u@example.com"
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.commit_mcp_connect")
        self.assertEqual(params["server_name"], "Acme")
        self.assertTrue(result["success"])

    def test_abandon_forwards_the_handle(self):
        with patch.object(self.client, "_request_post_form", return_value={"success": True}) as mock_post:
            self.client.abandon_mcp_connect(handle="h-1", user_id="u@example.com")

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.abandon_mcp_connect")
        self.assertEqual(params["handle"], "h-1")


class TestPublicBeginMCPReauth(unittest.TestCase):
    def setUp(self):
        self.client = AssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    def test_reauth_targets_its_own_endpoint(self):
        # Not begin_mcp_connect with a name attached: AR needs reauth_target on
        # the session so commit updates the existing row instead of inserting
        # a second one and failing the duplicate-name guard.
        with patch.object(
            self.client,
            "_request_post_form",
            return_value={"handle": "h-9", "preflight": {}, "authorize_url": "https://as/az"},
        ) as mock_post:
            result = self.client.begin_mcp_reauth(
                server_name="Acme", user_id="u@example.com"
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.begin_mcp_reauth")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(result["handle"], "h-9")


class TestAsyncPublicConnectMethods(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAssistantRuntimeClient(tenant_id="t", tenant_secret="s")

    async def test_begin_is_forwarded(self):
        async def _ok(*args, **kwargs):
            return {"handle": "h-1"}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            result = await self.client.begin_mcp_connect(
                endpoint_url="https://acme.example/mcp", user_id="u@example.com"
            )

        endpoint, _ = mock_post.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.begin_mcp_connect")
        self.assertEqual(result["handle"], "h-1")

    async def test_get_session_is_forwarded_over_get(self):
        async def _ok(*args, **kwargs):
            # AR's Select values are Title Case WITH SPACES, matching
            # AR User MCP Server.status. There is no "AwaitingAuth" spelling.
            return {"status": "Awaiting Auth"}

        with patch.object(self.client, "_request_get", side_effect=_ok) as mock_get:
            result = await self.client.get_mcp_connect_session(
                handle="h-1", user_id="u@example.com"
            )

        endpoint, _ = mock_get.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.get_mcp_connect_session")
        self.assertEqual(result["status"], "Awaiting Auth")

    async def test_commit_and_abandon_are_forwarded(self):
        async def _ok(*args, **kwargs):
            return {"success": True}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            await self.client.commit_mcp_connect(
                handle="h-1", server_name="Acme", user_id="u@example.com"
            )
            self.assertEqual(mock_post.call_args.args[0], "mcp_oauth.commit_mcp_connect")
            await self.client.abandon_mcp_connect(handle="h-1", user_id="u@example.com")
            self.assertEqual(mock_post.call_args.args[0], "mcp_oauth.abandon_mcp_connect")

    async def test_reauth_is_forwarded(self):
        async def _ok(*args, **kwargs):
            return {"handle": "h-9"}

        with patch.object(self.client, "_request_post_form", side_effect=_ok) as mock_post:
            result = await self.client.begin_mcp_reauth(
                server_name="Acme", user_id="u@example.com"
            )

        endpoint, params = mock_post.call_args.args
        self.assertEqual(endpoint, "mcp_oauth.begin_mcp_reauth")
        self.assertEqual(params["server_name"], "Acme")
        self.assertEqual(result["handle"], "h-9")


class TestConnectMethodParity(unittest.TestCase):
    """test_parity.py's SYNC_ONLY is an empty frozenset — a sync method with no
    async twin fails the whole suite. Asserting it here too keeps the failure
    local and readable instead of surfacing as one opaque meta-test diff.
    """

    def test_every_connect_method_exists_on_both_clients(self):
        for name in CONNECT_METHODS:
            self.assertTrue(hasattr(AssistantRuntimeClient, name), f"sync missing {name}")
            self.assertTrue(hasattr(AsyncAssistantRuntimeClient, name), f"async missing {name}")

    def test_signatures_match_between_sync_and_async(self):
        for name in CONNECT_METHODS:
            sync_params = [
                (p.name, p.default, p.kind)
                for p in inspect.signature(getattr(AssistantRuntimeClient, name)).parameters.values()
                if p.name != "self"
            ]
            async_params = [
                (p.name, p.default, p.kind)
                for p in inspect.signature(getattr(AsyncAssistantRuntimeClient, name)).parameters.values()
                if p.name != "self"
            ]
            self.assertEqual(sync_params, async_params, f"{name} signature drift")

    def test_the_async_versions_are_actually_async(self):
        for name in CONNECT_METHODS:
            self.assertTrue(
                inspect.iscoroutinefunction(getattr(AsyncAssistantRuntimeClient, name)),
                f"{name} is not a coroutine on the async client",
            )


if __name__ == "__main__":
    unittest.main()

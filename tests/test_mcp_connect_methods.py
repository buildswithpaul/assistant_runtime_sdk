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


if __name__ == "__main__":
    unittest.main()

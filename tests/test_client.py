# Assistant Runtime SDK - Client Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for AssistantRuntimeClient."""

import pytest
from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.exceptions import ARConfigurationError


class TestClientInitialization:
    """Tests for client initialization."""

    def test_basic_initialization(self):
        """Test basic client initialization."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

        assert client.tenant_id == "test-tenant"
        assert client.tenant_secret == "test-secret"
        assert client.ar_url == "https://ar.example.com"

    def test_default_url(self):
        """Test that default AR URL is used."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        assert client.ar_url == "https://ar.example.com"

    def test_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from URL."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com/",
        )

        assert client.ar_url == "https://ar.example.com"

    def test_missing_tenant_id_raises(self):
        """Test that missing tenant_id raises ARConfigurationError."""
        with pytest.raises(ARConfigurationError):
            AssistantRuntimeClient(tenant_id="", tenant_secret="test-secret")

    def test_missing_tenant_secret_raises(self):
        """Test that missing tenant_secret raises ARConfigurationError."""
        with pytest.raises(ARConfigurationError):
            AssistantRuntimeClient(tenant_id="test-tenant", tenant_secret="")

    def test_custom_timeout(self):
        """Test custom timeout setting."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            timeout=60.0,
        )

        assert client.timeout == 60.0

    def test_custom_logger(self):
        """Test custom logger injection."""
        import logging

        logger = logging.getLogger("test")
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            logger=logger,
        )

        assert client.logger is logger


class TestAPIBaseResolution:
    """Tests for API base URL resolution."""

    def test_default_api_bases(self):
        """Test that default API bases use standard module paths."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

        assert client.api_base == "https://ar.example.com/api/method/assistant_runtime.api"
        assert client.billing_api_base == "https://ar.example.com/api/method/assistant_runtime_payments.api"
        assert client.memory_api_base == "https://ar.example.com/api/method/assistant_runtime_memory.api"
        assert client.workflows_api_base == "https://ar.example.com/api/method/assistant_runtime_workflows.api"

    def test_full_url_override(self):
        """Test overriding API base with a full URL."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            billing_api_base="https://billing.example.com/api",
        )

        assert client.billing_api_base == "https://billing.example.com/api"

    def test_full_url_override_trailing_slash(self):
        """Test that trailing slash is stripped from URL overrides."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            memory_api_base="https://memory.example.com/api/",
        )

        assert client.memory_api_base == "https://memory.example.com/api"

    def test_module_path_override(self):
        """Test overriding API base with a dotted module path."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            workflows_api_base="my_custom_app.api",
        )

        assert client.workflows_api_base == "https://ar.example.com/api/method/my_custom_app.api"


class TestSignatureGeneration:
    """Tests for client signature generation."""

    def test_signature_in_headers(self):
        """Test that headers include AR signature."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        params = {"message": "test"}
        headers = client._get_headers(params, for_query_string=True)

        assert "X-AR-Signature" in headers
        sig = headers["X-AR-Signature"]
        assert ":" in sig
        parts = sig.split(":", 1)
        assert parts[0].isdigit()


class TestStreamPayloadPreparation:
    """Tests for stream payload preparation."""

    def test_basic_stream_payload(self):
        """Test basic stream payload."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        payload = client._prepare_stream_payload(
            session_id="session-123",
            message="Hello",
            user_id="user@example.com",
        )

        assert payload["tenant_id"] == "test-tenant"
        assert payload["session_id"] == "session-123"
        assert payload["message"] == "Hello"
        assert payload["user_id"] == "user@example.com"
        assert "context" not in payload
        assert "model_id" not in payload

    def test_stream_payload_with_context(self):
        """Test stream payload with context (native dict, not JSON string)."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        context = {"page": "home", "doctype": "User"}
        payload = client._prepare_stream_payload(
            session_id="session-123",
            message="Hello",
            user_id="user@example.com",
            context=context,
        )

        assert payload["context"] == context
        assert isinstance(payload["context"], dict)

    def test_stream_payload_with_model(self):
        """Test stream payload with model_id."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        payload = client._prepare_stream_payload(
            session_id="session-123",
            message="Hello",
            user_id="user@example.com",
            model_id="auto",
        )

        assert payload["model_id"] == "auto"

    def test_stream_payload_with_attachments(self):
        """Test stream payload with attachments."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        attachments = [{"type": "image", "format": "png", "data": "base64data"}]
        payload = client._prepare_stream_payload(
            session_id="session-123",
            message="What's in this image?",
            user_id="user@example.com",
            attachments=attachments,
        )

        assert payload["attachments"] == attachments

    def test_stream_payload_with_system_prompt_addendum(self):
        """Test stream payload with system_prompt_addendum."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        payload = client._prepare_stream_payload(
            session_id="session-123",
            message="Hello",
            user_id="user@example.com",
            system_prompt_addendum="Be concise.",
        )

        assert payload["system_prompt_addendum"] == "Be concise."

    def test_stream_payload_missing_user_id_raises(self):
        """Test that missing user_id raises ARConfigurationError."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        with pytest.raises(ARConfigurationError, match="user_id"):
            client._prepare_stream_payload(
                session_id="session-123",
                message="Hello",
                user_id="",
            )


class TestEndpointURLBuilding:
    """Tests for endpoint URL building."""

    def test_build_core_endpoint_url(self):
        """Test core endpoint URL construction."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

        url = client._build_endpoint_url("streaming.stream_chat")
        assert url == "https://ar.example.com/api/method/assistant_runtime.api.streaming.stream_chat"

    def test_build_billing_endpoint_url(self):
        """Test billing endpoint URL construction."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

        url = client._build_billing_endpoint_url("get_usage_dashboard")
        assert url == "https://ar.example.com/api/method/assistant_runtime_payments.api.get_usage_dashboard"

    def test_build_memory_endpoint_url(self):
        """Test memory endpoint URL construction."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

        url = client._build_memory_endpoint_url("onboarding.get_onboarding_status")
        assert url == "https://ar.example.com/api/method/assistant_runtime_memory.api.onboarding.get_onboarding_status"

    def test_build_workflows_endpoint_url(self):
        """Test workflows endpoint URL construction."""
        client = AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

        url = client._build_workflows_endpoint_url("workflows.create_workflow")
        assert url == "https://ar.example.com/api/method/assistant_runtime_workflows.api.workflows.create_workflow"


class TestInviteUser:
    def _client(self):
        from assistant_runtime_sdk import AssistantRuntimeClient
        return AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

    def test_prepare_invite_user_minimal(self):
        client = self._client()
        endpoint, params = client._prepare_invite_user("invitee@example.com")
        assert endpoint == "users.invite_user"
        assert params["tenant_id"] == "test-tenant"
        assert params["user_id"] == "invitee@example.com"
        assert "user_role" not in params
        assert "invited_by" not in params

    def test_prepare_invite_user_full(self):
        client = self._client()
        endpoint, params = client._prepare_invite_user(
            "invitee@example.com", user_role="Admin", invited_by="owner@example.com"
        )
        assert params["user_role"] == "Admin"
        assert params["invited_by"] == "owner@example.com"


class TestRevokeInvite:
    def _client(self):
        from assistant_runtime_sdk import AssistantRuntimeClient
        return AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

    def test_prepare_revoke_invite(self):
        client = self._client()
        endpoint, params = client._prepare_revoke_invite(
            "invitee@example.com", revoked_by="owner@example.com"
        )
        assert endpoint == "users.revoke_invite"
        assert params["tenant_id"] == "test-tenant"
        assert params["user_id"] == "invitee@example.com"
        assert params["revoked_by"] == "owner@example.com"

    def test_prepare_revoke_invite_no_actor(self):
        client = self._client()
        endpoint, params = client._prepare_revoke_invite("invitee@example.com")
        assert "revoked_by" not in params


class TestResendInvite:
    def _client(self):
        from assistant_runtime_sdk import AssistantRuntimeClient
        return AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

    def test_prepare_resend_invite(self):
        client = self._client()
        endpoint, params = client._prepare_resend_invite(
            "invitee@example.com", resent_by="owner@example.com"
        )
        assert endpoint == "users.resend_invite"
        assert params["tenant_id"] == "test-tenant"
        assert params["user_id"] == "invitee@example.com"
        assert params["resent_by"] == "owner@example.com"

    def test_prepare_resend_invite_no_actor(self):
        client = self._client()
        endpoint, params = client._prepare_resend_invite("invitee@example.com")
        assert "resent_by" not in params


class TestListInvites:
    def _client(self):
        from assistant_runtime_sdk import AssistantRuntimeClient
        return AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

    def test_prepare_list_invites(self):
        client = self._client()
        endpoint, params = client._prepare_list_invites()
        assert endpoint == "users.list_invites"
        assert params["tenant_id"] == "test-tenant"
        assert set(params.keys()) == {"tenant_id"}


class TestGetMemberAuditLog:
    def _client(self):
        from assistant_runtime_sdk import AssistantRuntimeClient
        return AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

    def test_prepare_get_member_audit_log_defaults(self):
        client = self._client()
        endpoint, params = client._prepare_get_member_audit_log()
        assert endpoint == "users.get_member_audit_log"
        assert params["tenant_id"] == "test-tenant"
        assert params["limit"] == "100"
        assert params["offset"] == "0"

    def test_prepare_get_member_audit_log_paginated(self):
        client = self._client()
        endpoint, params = client._prepare_get_member_audit_log(limit=50, offset=100)
        assert params["limit"] == "50"
        assert params["offset"] == "100"


class TestCancelSession:
    def _client(self):
        from assistant_runtime_sdk import AssistantRuntimeClient
        return AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

    def test_prepare_cancel_session(self):
        client = self._client()
        endpoint, payload = client._prepare_cancel_session("session-123")
        assert endpoint == "cancel.cancel_session"
        assert payload["tenant_id"] == "test-tenant"
        assert payload["session_id"] == "session-123"
        assert set(payload.keys()) == {"tenant_id", "session_id"}

    def test_prepare_cancel_session_requires_session_id(self):
        client = self._client()
        with pytest.raises(ValueError):
            client._prepare_cancel_session("")


class TestNotifications:
    def _client(self):
        from assistant_runtime_sdk import AssistantRuntimeClient
        return AssistantRuntimeClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            ar_url="https://ar.example.com",
        )

    def test_prepare_get_notifications(self):
        client = self._client()
        endpoint, payload = client._prepare_get_notifications(user_id="u@example.com")
        assert endpoint == "notifications.get_notifications"
        assert payload["tenant_id"] == client.tenant_id
        assert payload["user_id"] == "u@example.com"

    def test_prepare_dismiss_notification_points_at_notifications_module(self):
        client = self._client()
        endpoint, payload = client._prepare_dismiss_notification("NID-1", "u@example.com")
        assert endpoint == "notifications.dismiss_notification"
        assert payload == {
            "tenant_id": client.tenant_id,
            "notification_id": "NID-1",
            "user_id": "u@example.com",
        }

    def test_prepare_heartbeat_accepts_copilot_version(self):
        client = self._client()
        endpoint, payload = client._prepare_heartbeat(copilot_version="1.2.3")
        assert endpoint == "heartbeat.heartbeat"
        assert payload["copilot_version"] == "1.2.3"

    def test_prepare_heartbeat_still_accepts_faco_version(self):
        client = self._client()
        _, payload = client._prepare_heartbeat(faco_version="0.9.0")
        assert payload["faco_version"] == "0.9.0"

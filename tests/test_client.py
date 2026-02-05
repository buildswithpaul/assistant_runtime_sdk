# FACL SDK - Client Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for FACLClient."""

import pytest
from facl import FACLClient
from facl.exceptions import FACLConfigurationError


class TestClientInitialization:
    """Tests for client initialization."""

    def test_basic_initialization(self):
        """Test basic client initialization."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            facl_url="https://facl.example.com",
        )

        assert client.tenant_id == "test-tenant"
        assert client.tenant_secret == "test-secret"
        assert client.facl_url == "https://facl.example.com"

    def test_default_url(self):
        """Test that default FACL URL is used."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        assert client.facl_url == "https://facl.frappe.cloud"

    def test_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from URL."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            facl_url="https://facl.example.com/",
        )

        assert client.facl_url == "https://facl.example.com"

    def test_custom_timeout(self):
        """Test custom timeout setting."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            timeout=60.0,
        )

        assert client.timeout == 60.0

    def test_custom_logger(self):
        """Test custom logger injection."""
        import logging

        logger = logging.getLogger("test")
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            logger=logger,
        )

        assert client.logger is logger


class TestSignatureGeneration:
    """Tests for client signature generation."""

    def test_signature_in_headers(self):
        """Test that headers include FACL signature."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        params = {"message": "test"}
        headers = client._get_headers(params, for_query_string=True)

        assert "X-FACL-Signature" in headers
        # Signature format: timestamp:hex
        sig = headers["X-FACL-Signature"]
        assert ":" in sig
        parts = sig.split(":", 1)
        assert parts[0].isdigit()


class TestStreamParamsPreparation:
    """Tests for stream parameter preparation."""

    def test_basic_stream_params(self):
        """Test basic stream parameters."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        params = client._prepare_stream_params(
            session_id="session-123",
            message="Hello",
            user_id="user@example.com",
            context=None,
            model_id=None,
        )

        assert params["tenant_id"] == "test-tenant"
        assert params["session_id"] == "session-123"
        assert params["message"] == "Hello"
        assert params["user_id"] == "user@example.com"
        assert "context" not in params
        assert "model_id" not in params

    def test_stream_params_with_context(self):
        """Test stream parameters with context."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        context = {"page": "home", "doctype": "User"}
        params = client._prepare_stream_params(
            session_id="session-123",
            message="Hello",
            user_id="user@example.com",
            context=context,
            model_id=None,
        )

        assert "context" in params
        # Context should be JSON-encoded string
        import json

        assert json.loads(params["context"]) == context

    def test_stream_params_with_model(self):
        """Test stream parameters with model_id."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
        )

        params = client._prepare_stream_params(
            session_id="session-123",
            message="Hello",
            user_id="user@example.com",
            context=None,
            model_id="auto",
        )

        assert params["model_id"] == "auto"


class TestEndpointURLBuilding:
    """Tests for endpoint URL building."""

    def test_build_endpoint_url(self):
        """Test endpoint URL construction."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            facl_url="https://facl.example.com",
        )

        url = client._build_endpoint_url("streaming.stream_chat")
        expected = "https://facl.example.com/api/method/frappe_assistant_cloud.api.streaming.stream_chat"

        assert url == expected

    def test_build_endpoint_url_simple(self):
        """Test endpoint URL for simple endpoint."""
        client = FACLClient(
            tenant_id="test-tenant",
            tenant_secret="test-secret",
            facl_url="https://facl.example.com",
        )

        url = client._build_endpoint_url("get_tenant_info")
        expected = "https://facl.example.com/api/method/frappe_assistant_cloud.api.get_tenant_info"

        assert url == expected

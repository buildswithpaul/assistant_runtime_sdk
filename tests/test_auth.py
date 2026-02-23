# Assistant Runtime SDK - Auth Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for HMAC authentication module."""

import pytest
import time
from assistant_runtime_sdk.auth import generate_signature, verify_signature, get_signature_header


class TestGenerateSignature:
    """Tests for generate_signature function."""

    def test_basic_signature_generation(self):
        """Test that signature is generated in correct format."""
        params = {"tenant_id": "test-tenant", "message": "Hello"}
        signature = generate_signature("test-tenant", "test-secret", params)

        # Should be in format "timestamp:hex_signature"
        assert ":" in signature
        parts = signature.split(":", 1)
        assert len(parts) == 2
        assert parts[0].isdigit()  # timestamp
        assert len(parts[1]) == 64  # SHA256 hex digest

    def test_deterministic_with_timestamp(self):
        """Test that same inputs with same timestamp produce same signature."""
        params = {"key": "value"}
        timestamp = 1704067200

        sig1 = generate_signature("tenant", "secret", params, timestamp=timestamp)
        sig2 = generate_signature("tenant", "secret", params, timestamp=timestamp)

        assert sig1 == sig2

    def test_different_params_different_signature(self):
        """Test that different params produce different signatures."""
        timestamp = 1704067200

        sig1 = generate_signature("tenant", "secret", {"a": "1"}, timestamp=timestamp)
        sig2 = generate_signature("tenant", "secret", {"a": "2"}, timestamp=timestamp)

        assert sig1 != sig2

    def test_different_secrets_different_signature(self):
        """Test that different secrets produce different signatures."""
        params = {"key": "value"}
        timestamp = 1704067200

        sig1 = generate_signature("tenant", "secret1", params, timestamp=timestamp)
        sig2 = generate_signature("tenant", "secret2", params, timestamp=timestamp)

        assert sig1 != sig2

    def test_query_string_mode_converts_values(self):
        """Test that query string mode converts values to strings."""
        params = {"count": 42, "active": True}
        timestamp = 1704067200

        # Query string mode should convert 42 -> "42"
        sig_query = generate_signature("t", "s", params, for_query_string=True, timestamp=timestamp)

        # JSON mode keeps original types
        sig_json = generate_signature("t", "s", params, for_query_string=False, timestamp=timestamp)

        assert sig_query != sig_json


class TestVerifySignature:
    """Tests for verify_signature function."""

    def test_valid_signature_verification(self):
        """Test that valid signature passes verification."""
        params = {"message": "test"}
        secret = "my-secret"

        signature = generate_signature("tenant", secret, params, for_query_string=True)
        is_valid = verify_signature(signature, "tenant", secret, params, for_query_string=True)

        assert is_valid is True

    def test_invalid_signature_rejected(self):
        """Test that invalid signature is rejected."""
        params = {"message": "test"}

        is_valid = verify_signature("invalid:signature", "tenant", "secret", params)

        assert is_valid is False

    def test_wrong_secret_rejected(self):
        """Test that signature with wrong secret is rejected."""
        params = {"message": "test"}

        signature = generate_signature("tenant", "correct-secret", params)
        is_valid = verify_signature(signature, "tenant", "wrong-secret", params)

        assert is_valid is False

    def test_expired_signature_rejected(self):
        """Test that expired signature is rejected."""
        params = {"message": "test"}
        old_timestamp = int(time.time()) - 600  # 10 minutes ago

        signature = generate_signature("tenant", "secret", params, timestamp=old_timestamp)
        is_valid = verify_signature(signature, "tenant", "secret", params, max_age_seconds=300)

        assert is_valid is False

    def test_malformed_signature_rejected(self):
        """Test that malformed signatures are rejected."""
        params = {"message": "test"}

        # Missing colon
        assert verify_signature("noseparator", "t", "s", params) is False

        # Empty parts
        assert verify_signature(":empty", "t", "s", params) is False

        # Non-numeric timestamp
        assert verify_signature("abc:signature", "t", "s", params) is False


class TestGetSignatureHeader:
    """Tests for get_signature_header function."""

    def test_returns_dict_with_correct_key(self):
        """Test that function returns dict with X-AR-Signature key."""
        headers = get_signature_header("tenant", "secret", {"a": "b"})

        assert isinstance(headers, dict)
        assert "X-AR-Signature" in headers
        assert ":" in headers["X-AR-Signature"]

    def test_signature_can_be_verified(self):
        """Test that signature from header can be verified."""
        params = {"test": "data"}
        headers = get_signature_header("tenant", "secret", params, for_query_string=True)

        is_valid = verify_signature(
            headers["X-AR-Signature"],
            "tenant",
            "secret",
            params,
            for_query_string=True,
        )

        assert is_valid is True

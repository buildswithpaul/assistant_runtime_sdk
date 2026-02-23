# Assistant Runtime SDK - Exceptions
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Custom exceptions for the Assistant Runtime SDK.

All exceptions inherit from ARError for easy catching.
"""

from typing import Optional, List


class ARError(Exception):
    """Base exception for all Assistant Runtime SDK errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ARAuthenticationError(ARError):
    """
    HMAC signature validation failed.

    This typically indicates:
    - Invalid tenant_secret
    - Clock skew between client and server
    - Tampered request parameters
    """

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTH_FAILED")


class ARRateLimitError(ARError):
    """
    Rate limit exceeded.

    Contains retry_after indicating seconds until retry is possible.
    May include models_checked if using auto-model selection.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        models_checked: Optional[List[str]] = None,
    ):
        super().__init__(message, error_code="RATE_LIMITED")
        self.retry_after = retry_after
        self.models_checked = models_checked or []

    def __str__(self) -> str:
        base = super().__str__()
        if self.retry_after:
            return f"{base} (retry after {self.retry_after:.1f}s)"
        return base


class ARStreamError(ARError):
    """
    SSE streaming error.

    Raised when:
    - Connection drops during streaming
    - Malformed SSE data received
    - Server sends error event
    """

    def __init__(self, message: str = "Streaming error", error_code: Optional[str] = None):
        super().__init__(message, error_code=error_code or "STREAM_ERROR")


class ARConfigurationError(ARError):
    """
    Invalid configuration.

    Raised when:
    - Missing required parameters (tenant_id, tenant_secret)
    - Invalid AR URL format
    - Missing user_id where required
    """

    def __init__(self, message: str = "Configuration error"):
        super().__init__(message, error_code="CONFIG_ERROR")


class ARAPIError(ARError):
    """
    API request failed.

    Contains HTTP status code and response details.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[dict] = None,
    ):
        error_code = f"HTTP_{status_code}" if status_code else "API_ERROR"
        super().__init__(message, error_code=error_code)
        self.status_code = status_code
        self.response_data = response_data or {}


class ARTimeoutError(ARError):
    """
    Request timed out.

    Raised when connection or read timeout is exceeded.
    """

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, error_code="TIMEOUT")


class ARConnectionError(ARError):
    """
    Connection failed.

    Raised when unable to connect to Assistant Runtime server.
    """

    def __init__(self, message: str = "Connection failed"):
        super().__init__(message, error_code="CONNECTION_ERROR")


class ARBillingUnavailableError(ARError):
    """
    Billing features are not available on this server.

    Raised when:
    - The payments app is not installed on the target server
    - check_billing_available() returned False and a billing method was called
    """

    def __init__(self, message: str = "Billing is not available"):
        super().__init__(message, error_code="BILLING_UNAVAILABLE")

# Assistant Runtime SDK - Base Client
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Base client class with shared authentication and configuration logic.

Both AssistantRuntimeClient (sync) and AsyncAssistantRuntimeClient (async) inherit from this.
"""

import json
import logging
from typing import Dict, Any, Optional, Protocol, runtime_checkable

from .auth import generate_signature
from .streaming import parse_sse_line
from .exceptions import ARConfigurationError


@runtime_checkable
class Logger(Protocol):
    """Protocol for logger interface."""

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class BaseAssistantRuntimeClient:
    """
    Base class with shared authentication and configuration logic.

    This class provides:
    - HMAC signature generation for API requests
    - SSE line parsing for streaming responses
    - Common configuration and validation

    Both AssistantRuntimeClient (sync) and AsyncAssistantRuntimeClient (async) inherit from this class.

    Args:
        tenant_id: Unique tenant identifier from Assistant Runtime
        tenant_secret: HMAC secret for request signing
        ar_url: Base URL of Assistant Runtime server (default: https://ar.example.com)
        logger: Optional logger instance (uses stdlib logging if None)
        timeout: Default request timeout in seconds (default: 30.0)

    Example:
        >>> # Don't instantiate directly - use AssistantRuntimeClient or AsyncAssistantRuntimeClient
        >>> from assistant_runtime_sdk import AssistantRuntimeClient
        >>> client = AssistantRuntimeClient("tenant-id", "secret")
    """

    DEFAULT_AR_URL = "https://ar.example.com"
    DEFAULT_TIMEOUT = 30.0
    STREAM_CONNECT_TIMEOUT = 10.0
    STREAM_READ_TIMEOUT = 300.0  # 5 minutes for long responses

    def __init__(
        self,
        tenant_id: str,
        tenant_secret: str,
        ar_url: str = DEFAULT_AR_URL,
        logger: Optional[Logger] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        # Validate required parameters
        if not tenant_id:
            raise ARConfigurationError("tenant_id is required")
        if not tenant_secret:
            raise ARConfigurationError("tenant_secret is required")

        self.tenant_id = tenant_id
        self.tenant_secret = tenant_secret
        self.ar_url = ar_url.rstrip("/")
        self.api_base = f"{self.ar_url}/api/method/assistant_runtime.api"
        self.timeout = timeout

        # Setup logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def _generate_signature(self, params: Dict[str, Any], for_query_string: bool = False) -> str:
        """
        Generate HMAC-SHA256 signature for Assistant Runtime API request.

        Args:
            params: Request parameters (will be sorted by key)
            for_query_string: If True, convert values to strings (for GET requests)

        Returns:
            Signature header value in format "timestamp:signature"
        """
        return generate_signature(
            self.tenant_id,
            self.tenant_secret,
            params,
            for_query_string=for_query_string,
        )

    def _get_headers(self, params: Dict[str, Any], for_query_string: bool = True) -> Dict[str, str]:
        """
        Get request headers with HMAC signature.

        Args:
            params: Request parameters for signature
            for_query_string: True for GET requests, False for POST JSON

        Returns:
            Headers dict with X-AR-Signature
        """
        return {"X-AR-Signature": self._generate_signature(params, for_query_string)}

    def _get_stream_headers(
        self,
        params: Dict[str, Any],
        for_json_body: bool = False,
    ) -> Dict[str, str]:
        """
        Get headers for SSE streaming requests.

        Args:
            params: Request parameters for signature
            for_json_body: If True, signature is computed for JSON body (POST).
                          If False, signature is computed for query string (GET).

        Returns:
            Headers dict with X-AR-Signature and SSE headers
        """
        headers = {
            "X-AR-Signature": self._generate_signature(params, for_query_string=not for_json_body),
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }
        if for_json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _parse_sse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single SSE line.

        Args:
            line: Raw SSE line

        Returns:
            Parsed event dict or None
        """
        return parse_sse_line(line)

    def _build_endpoint_url(self, endpoint: str) -> str:
        """
        Build full URL for an API endpoint.

        Args:
            endpoint: Endpoint path (e.g., 'streaming.stream_chat')

        Returns:
            Full URL
        """
        return f"{self.api_base}.{endpoint}"

    def _prepare_stream_params(
        self,
        session_id: str,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Prepare parameters for stream_chat request (legacy GET format).

        DEPRECATED: Use _prepare_stream_payload for POST requests.

        Args:
            session_id: Conversation session identifier
            message: User's message
            user_id: User identifier (required)
            context: Optional page context
            model_id: Optional model ID

        Returns:
            Parameters dict ready for request

        Raises:
            ARConfigurationError: If user_id is missing
        """
        if not user_id:
            raise ARConfigurationError("user_id is required for stream_chat")

        params = {
            "tenant_id": self.tenant_id,
            "session_id": session_id,
            "message": message,
            "user_id": user_id,
        }

        if context:
            params["context"] = json.dumps(context)

        if model_id:
            params["model_id"] = model_id

        return params

    def _prepare_stream_payload(
        self,
        session_id: str,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Prepare JSON payload for stream_chat POST request.

        Args:
            session_id: Conversation session identifier
            message: User's message
            user_id: User identifier (required)
            context: Optional page context (sent as native dict, not JSON string)
            model_id: Optional model ID

        Returns:
            Payload dict ready for JSON body

        Raises:
            ARConfigurationError: If user_id is missing
        """
        if not user_id:
            raise ARConfigurationError("user_id is required for stream_chat")

        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "session_id": session_id,
            "message": message,
            "user_id": user_id,
        }

        if context:
            # Context is sent as a native dict in JSON body, not a JSON string
            payload["context"] = context

        if model_id:
            payload["model_id"] = model_id

        return payload

    def _prepare_resource_params(
        self,
        user_id: str,
        uri: Optional[str] = None,
        server: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Prepare parameters for resource requests.

        Args:
            user_id: User identifier (required)
            uri: Optional resource URI (for read_resource)
            server: Optional server name filter (for list_resources)

        Returns:
            Parameters dict ready for request
        """
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        if uri:
            params["uri"] = uri
        if server:
            params["server"] = server
        return params

    def _log_error(self, message: str, category: str = "AR") -> None:
        """Log an error message."""
        self.logger.error(message, extra={"category": category})

    def _log_warning(self, message: str, category: str = "AR") -> None:
        """Log a warning message."""
        self.logger.warning(message, extra={"category": category})

    def _log_debug(self, message: str, category: str = "AR") -> None:
        """Log a debug message."""
        self.logger.debug(message, extra={"category": category})


# Backwards compatibility alias
BaseFACLClient = BaseAssistantRuntimeClient

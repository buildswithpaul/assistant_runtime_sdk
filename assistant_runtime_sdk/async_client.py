# Assistant Runtime SDK - Asynchronous Client
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Asynchronous FACL client using aiohttp.

Requires the 'async' extra: pip install facl[async]
"""

import json
import mimetypes
import os
from typing import AsyncGenerator, List, Optional, Dict, Any

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore

from .base import BaseAssistantRuntimeClient
from .exceptions import (
    ARAPIError,
    ARTimeoutError,
    ARConnectionError,
    ARConfigurationError,
)


class AsyncAssistantRuntimeClient(BaseAssistantRuntimeClient):
    """
    Asynchronous FACL client using aiohttp.

    Use as an async context manager for proper resource management.

    Example:
        >>> async with AsyncAssistantRuntimeClient("tenant-id", "secret") as client:
        ...     models = await client.list_available_models()
        ...     async for event in client.stream_chat("session-1", "Hello", "user@example.com"):
        ...         print(event)
    """

    def __init__(
        self,
        tenant_id: str,
        tenant_secret: str,
        ar_url: str = BaseAssistantRuntimeClient.DEFAULT_AR_URL,
        logger=None,
        timeout: float = BaseAssistantRuntimeClient.DEFAULT_TIMEOUT,
        session: Optional["aiohttp.ClientSession"] = None,
        billing_api_base: Optional[str] = None,
        memory_api_base: Optional[str] = None,
        workflows_api_base: Optional[str] = None,
    ):
        """
        Initialize async Assistant Runtime client.

        Args:
            tenant_id: Unique tenant identifier from Assistant Runtime
            tenant_secret: HMAC secret for request signing
            ar_url: Base URL of Assistant Runtime server
            logger: Optional logger instance
            timeout: Default request timeout in seconds
            session: Optional aiohttp.ClientSession to reuse
            billing_api_base: Override URL for billing API endpoints
            memory_api_base: Override URL for memory/onboarding/document API endpoints
            workflows_api_base: Override URL for workflow API endpoints
        """
        if aiohttp is None:
            raise ImportError(
                "aiohttp is required for AsyncAssistantRuntimeClient. "
                "Install it with: pip install facl[async]"
            )

        super().__init__(tenant_id, tenant_secret, ar_url, logger, timeout, billing_api_base, memory_api_base, workflows_api_base)
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "AsyncAssistantRuntimeClient":
        """Enter async context - create session if needed."""
        if self._owns_session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context - close session if we own it."""
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    def _ensure_session(self) -> "aiohttp.ClientSession":
        """Ensure we have an active session."""
        if self._session is None:
            raise ARConfigurationError(
                "No active session. Use AsyncAssistantRuntimeClient as a context manager: "
                "async with AsyncAssistantRuntimeClient(...) as client:"
            )
        return self._session

    # =========================================================================
    # Internal Request Methods
    # =========================================================================

    async def _request_get(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated async GET request."""
        session = self._ensure_session()
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        headers = self._get_headers(params, for_query_string=True)

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.get(url, params=params, headers=headers, timeout=timeout_obj) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("message", data)
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"GET {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"GET {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientResponseError as e:
            self._log_error(f"GET {endpoint} HTTP error: {e}")
            raise ARAPIError(str(e), status_code=e.status) from e
        except aiohttp.ClientError as e:
            self._log_error(f"GET {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    async def _request_post_json(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated async POST request with JSON body."""
        session = self._ensure_session()
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        headers = {
            **self._get_headers(payload, for_query_string=False),
            "Content-Type": "application/json",
        }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.post(url, json=payload, headers=headers, timeout=timeout_obj) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("message", data)
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"POST {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"POST {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientResponseError as e:
            self._log_error(f"POST {endpoint} HTTP error: {e}")
            raise ARAPIError(str(e), status_code=e.status) from e
        except aiohttp.ClientError as e:
            self._log_error(f"POST {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    async def _request_post_form(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated async POST request with form-urlencoded body."""
        session = self._ensure_session()
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        headers = {
            **self._get_headers(params, for_query_string=True),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.post(url, data=params, headers=headers, timeout=timeout_obj) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("message", data)
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"POST form {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"POST form {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientResponseError as e:
            self._log_error(f"POST form {endpoint} HTTP error: {e}")
            raise ARAPIError(str(e), status_code=e.status) from e
        except aiohttp.ClientError as e:
            self._log_error(f"POST form {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    async def _request_post_multipart(
        self,
        endpoint: str,
        params: Dict[str, Any],
        file_field: str,
        file_name: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated async POST request with multipart form data including a file."""
        session = self._ensure_session()
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        # Sign only non-file form fields — Frappe's form_dict excludes file parts
        headers = self._get_headers(params, for_query_string=True)
        # Do NOT set Content-Type — aiohttp sets multipart boundary automatically

        form_data = aiohttp.FormData()
        for key, value in params.items():
            form_data.add_field(key, str(value))
        form_data.add_field(
            file_field, file_data,
            filename=file_name,
            content_type=content_type,
        )

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.post(url, data=form_data, headers=headers, timeout=timeout_obj) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("message", data)
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"POST multipart {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"POST multipart {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientResponseError as e:
            self._log_error(f"POST multipart {endpoint} HTTP error: {e}")
            raise ARAPIError(str(e), status_code=e.status) from e
        except aiohttp.ClientError as e:
            self._log_error(f"POST multipart {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    async def _request_delete(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated async DELETE request."""
        session = self._ensure_session()
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        headers = self._get_headers(params, for_query_string=True)

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.delete(url, params=params, headers=headers, timeout=timeout_obj) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("message", data)
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"DELETE {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"DELETE {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientResponseError as e:
            self._log_error(f"DELETE {endpoint} HTTP error: {e}")
            raise ARAPIError(str(e), status_code=e.status) from e
        except aiohttp.ClientError as e:
            self._log_error(f"DELETE {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    # =========================================================================
    # Streaming API
    # =========================================================================

    async def stream_chat(
        self,
        session_id: str,
        message: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        system_prompt_addendum: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat response from Assistant Runtime asynchronously.

        Args:
            session_id: Conversation session identifier
            message: User's message to send
            user_id: User identifier (required)
            context: Optional page context
            model_id: Optional model ID (use "auto" for auto-selection)
            attachments: Optional list of attachments (images/documents)
                Each attachment: {
                    "type": "image" | "document",
                    "format": "png" | "jpeg" | "gif" | "webp" | "pdf" | "txt",
                    "data": "<base64-encoded-data>",
                    "name": "optional-filename.png",  # Optional
                    "file_url": "/files/..."  # Optional, for storage reference
                }

        Yields:
            Parsed SSE events

        Example:
            >>> async for event in client.stream_chat("session-1", "Hello", "user@example.com"):
            ...     if event["event"] == "stream_chunk":
            ...         print(event["data"].get("content", ""), end="")
        """
        session = self._ensure_session()
        payload = self._prepare_stream_payload(session_id, message, user_id, context, model_id, attachments, system_prompt_addendum)
        url = self._build_endpoint_url("streaming.stream_chat")
        headers = self._get_stream_headers(payload, for_json_body=True)

        try:
            timeout = aiohttp.ClientTimeout(
                connect=self.STREAM_CONNECT_TIMEOUT,
                total=self.STREAM_READ_TIMEOUT,
            )
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                response.raise_for_status()

                current_event = None

                async for line in response.content:
                    if not line:
                        continue

                    # Decode bytes to string
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue

                    parsed = self._parse_sse_line(line_str)
                    if not parsed:
                        continue

                    if parsed["type"] == "event_name":
                        current_event = parsed["value"]
                    elif parsed["type"] == "data":
                        yield {"event": current_event or "unknown", "data": parsed["value"]}
                        current_event = None

        except aiohttp.ServerTimeoutError:
            yield {
                "event": "stream_error",
                "data": {"error": "Connection timeout", "error_code": "TIMEOUT"},
            }
        except aiohttp.ClientError as e:
            yield {
                "event": "stream_error",
                "data": {"error": str(e), "error_code": "REQUEST_ERROR"},
            }

    # =========================================================================
    # Tenant APIs
    # =========================================================================

    async def get_tenant_info(self) -> Optional[Dict[str, Any]]:
        """Get tenant information including subscription status."""
        return await self._request_get("get_tenant_info", {"tenant_id": self.tenant_id})

    async def accept_terms(self, terms_version: str, accepted_by: str) -> Dict[str, Any]:
        """Accept or re-accept Terms and Conditions for this tenant."""
        payload = {
            "tenant_id": self.tenant_id,
            "terms_version": terms_version,
            "accepted_by": accepted_by,
        }
        return await self._request_post_json("accept_terms", payload)

    # =========================================================================
    # Model APIs
    # =========================================================================

    async def list_available_models(self) -> Optional[Dict[str, Any]]:
        """List available AI models for this tenant's subscription tier."""
        return await self._request_get("streaming.list_available_models", {"tenant_id": self.tenant_id})

    async def get_available_models(self) -> Optional[Dict[str, Any]]:
        """Get available AI models (deprecated). Use list_available_models() instead."""
        return await self._request_get("get_available_models", {"tenant_id": self.tenant_id})

    async def set_preferred_model(self, model_id: str) -> bool:
        """Set the preferred AI model for this tenant."""
        payload = {"tenant_id": self.tenant_id, "model_id": model_id}
        result = await self._request_post_json("set_preferred_model", payload)
        return result.get("success", False) if result else False

    # =========================================================================
    # Prompt APIs
    # =========================================================================

    async def list_prompts(self, user_id: str, cursor: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """List available prompt templates from user's configured MCP servers."""
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        if cursor:
            params["cursor"] = cursor
        return await self._request_get("prompts.list_prompts", params)

    async def get_prompt(
        self,
        prompt_name: str,
        user_id: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific prompt rendered with provided arguments."""
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "prompt_name": prompt_name,
        }
        if arguments:
            payload["arguments"] = arguments
        return await self._request_post_json("prompts.get_prompt", payload)

    # =========================================================================
    # Suggestion APIs
    # =========================================================================

    async def get_suggestions(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 8,
    ) -> Optional[Dict[str, Any]]:
        """Get personalized prompt suggestions based on user conversation history."""
        params = {"tenant_id": self.tenant_id, "user_id": user_id, "limit": str(limit)}
        if context:
            params["context"] = json.dumps(context)
        return await self._request_get("suggestions.get_suggestions", params)

    # =========================================================================
    # Onboarding APIs
    # =========================================================================
    # These methods route through memory_api_base → assistant_runtime_memory.api

    async def get_onboarding_status(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Check if a user has completed onboarding."""
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        return await self._request_get(
            "onboarding.get_onboarding_status", params,
            api_base=self.memory_api_base,
        )

    async def complete_onboarding(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Mark onboarding complete and trigger immediate memory extraction."""
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        return await self._request_post_json(
            "onboarding.complete_onboarding", payload,
            api_base=self.memory_api_base,
        )

    # =========================================================================
    # Document APIs (RAG)
    # =========================================================================
    # These methods route through memory_api_base → assistant_runtime_memory.api

    async def upload_document(
        self,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a document for RAG processing.

        Accepts either a file path or raw bytes. Supported formats: PDF,
        Markdown (.md), and plain text (.txt).

        Args:
            file_path: Path to the file to upload. Mutually exclusive with file_data.
            file_data: Raw file bytes. Requires file_name.
            file_name: Filename (required with file_data, optional with file_path).
            content_type: MIME type override. Auto-detected from extension if omitted.

        Returns:
            {"status": "queued", "document_id": str, "file_name": str,
             "file_size_mb": float, "message": str}
        """
        if file_path and file_data:
            raise ARConfigurationError("Provide either file_path or file_data, not both")
        if not file_path and not file_data:
            raise ARConfigurationError("Either file_path or file_data is required")
        if file_data and not file_name:
            raise ARConfigurationError("file_name is required when using file_data")

        if file_path:
            with open(file_path, "rb") as f:
                data = f.read()
            if not file_name:
                file_name = os.path.basename(file_path)
        else:
            data = file_data

        if not content_type:
            guessed, _ = mimetypes.guess_type(file_name)
            content_type = guessed or "application/octet-stream"

        return await self._request_post_multipart(
            "documents.upload_document",
            params={"tenant_id": self.tenant_id},
            file_field="file",
            file_name=file_name,
            file_data=data,
            content_type=content_type,
            timeout=120.0,
            api_base=self.memory_api_base,
        )

    async def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        List all RAG documents for this tenant.

        Args:
            limit: Maximum number of documents to return (default 50).
            offset: Pagination offset (default 0).

        Returns:
            {"documents": [...], "pagination": {...}, "storage": {...}}
        """
        params = {
            "tenant_id": self.tenant_id,
            "limit": str(limit),
            "offset": str(offset),
        }
        return await self._request_get(
            "documents.list_documents", params,
            api_base=self.memory_api_base,
        )

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific RAG document.

        Args:
            document_id: The document identifier.

        Returns:
            Document details including embedding_status, total_chunks,
            and processing_error (if status is Failed).
        """
        params = {"tenant_id": self.tenant_id, "document_id": document_id}
        return await self._request_get(
            "documents.get_document", params,
            api_base=self.memory_api_base,
        )

    async def delete_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete a RAG document and remove its embeddings.

        Performs a soft delete — the document is marked as deleted and its
        vector embeddings are removed from the search index.

        Args:
            document_id: The document identifier to delete.

        Returns:
            {"status": "deleted", "document_id": str, "file_size_mb": float}
        """
        payload = {"tenant_id": self.tenant_id, "document_id": document_id}
        return await self._request_post_json(
            "documents.delete_document", payload,
            api_base=self.memory_api_base,
        )

    async def get_storage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get storage quota and usage information for this tenant's RAG documents.

        Returns:
            {"quota_mb": float, "used_mb": float, "available_mb": float,
             "usage_percentage": float, "document_count": int}
        """
        params = {"tenant_id": self.tenant_id}
        return await self._request_get(
            "documents.get_storage_info", params,
            api_base=self.memory_api_base,
        )

    # =========================================================================
    # Resource APIs (Skills/Documentation)
    # =========================================================================

    async def list_resources(
        self,
        user_id: str,
        server: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        List available resources (skills/documentation) from user's MCP servers.

        Resources are typically tool documentation that can be fetched on-demand
        to reduce LLM context usage. When the MCP server has resources enabled,
        tools have minimal descriptions and detailed docs are served as resources.

        Args:
            user_id: User identifier (required)
            server: Optional - filter to specific MCP server

        Returns:
            Dict with resources list, servers_queried, and any errors

        Example:
            >>> resources = await client.list_resources("user@example.com")
            >>> for r in resources.get("resources", []):
            ...     print(f"{r['name']}: {r['uri']}")
        """
        params = self._prepare_resource_params(user_id, server=server)
        return await self._request_get("resources.list_resources", params)

    async def read_resource(
        self,
        user_id: str,
        uri: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Read a specific resource's content from user's MCP server.

        Fetches detailed documentation for a tool or other resource.

        Args:
            user_id: User identifier (required)
            uri: Resource URI to read (e.g., "fac://tools/create_document")

        Returns:
            Dict with resource content:
            {
                "uri": "fac://tools/create_document",
                "content": "# create_document\\n\\n## Description\\n...",
                "mimeType": "text/markdown",
                "server": "server_name"
            }

        Example:
            >>> result = await client.read_resource("user@example.com", "fac://tools/create_document")
            >>> print(result.get("content"))
        """
        params = self._prepare_resource_params(user_id, uri=uri)
        return await self._request_post_json("resources.read_resource", params)

    # =========================================================================
    # Tool APIs
    # =========================================================================

    async def list_tools(
        self,
        user_id: str,
        server: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        List available tools from user's configured MCP servers.

        Returns tools with their names, descriptions, and input schemas.
        Useful for building workflow tool directives in the UI.

        Args:
            user_id: User identifier (required)
            server: Optional - filter to specific MCP server

        Returns:
            Dict with tools list, servers_queried, and any errors:
            {
                "tools": [
                    {
                        "name": "server_name:tool_name",
                        "original_name": "tool_name",
                        "description": "...",
                        "inputSchema": {...},
                        "server": "server_name"
                    }
                ],
                "servers_queried": ["server_name"],
                "errors": null
            }

        Example:
            >>> tools = await client.list_tools("user@example.com")
            >>> for t in tools.get("tools", []):
            ...     print(f"{t['name']}: {t['description']}")
        """
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        if server:
            params["server"] = server
        return await self._request_get("tools.list_tools", params)

    # =========================================================================
    # Billing & Subscription APIs
    # =========================================================================
    # These methods route through billing_api_base → assistant_runtime_payments.api

    async def check_billing_available(self) -> bool:
        """
        Probe the server to check if billing features are available.

        Calls ``get_capabilities`` on the core API and checks the
        ``billing_enabled`` flag. The result is cached in ``_billing_available``.

        Returns:
            True if billing is available, False otherwise.
        """
        session = self._ensure_session()
        try:
            url = f"{self.api_base}.get_capabilities"
            timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
            async with session.get(url, timeout=timeout_obj) as response:
                response.raise_for_status()
                data = await response.json()
                result = data.get("message", data)
                self._billing_available = result.get("billing_enabled", False)
        except (aiohttp.ClientError, Exception):
            self._billing_available = False
        return self._billing_available

    async def get_plan_comparison(self) -> Optional[Dict[str, Any]]:
        """Get comparison of all available subscription plans (no auth required)."""
        self._require_billing()
        session = self._ensure_session()
        url = self._build_billing_endpoint_url("get_plan_comparison")
        try:
            timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
            async with session.get(url, timeout=timeout_obj) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("message", data)
        except (aiohttp.ClientError, Exception) as e:
            self._log_error(f"get_plan_comparison error: {e}")
            return None

    async def get_recommended_gateway(self) -> Optional[Dict[str, Any]]:
        """Get the recommended payment gateway for this tenant."""
        self._require_billing()
        return await self._request_get(
            "get_recommended_gateway", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def get_available_gateways(self) -> Optional[Dict[str, Any]]:
        """
        Get all enabled payment gateways with pricing for each plan.

        Returns:
            Dict with gateways list, recommended_gateway, and tenant_country.
            Each gateway includes name, display_name, currency, description,
            is_recommended flag, and plans pricing dict.
        """
        self._require_billing()
        return await self._request_get(
            "get_available_gateways", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def initiate_checkout(
        self,
        plan: str,
        billing_cycle: str = "monthly",
        gateway: Optional[str] = None,
        billing_name: Optional[str] = None,
        billing_email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a checkout session for subscription upgrade.

        Args:
            plan: Plan name (Starter, Pro, Enterprise)
            billing_cycle: "monthly" or "annual" (default: monthly)
            gateway: "stripe" or "razorpay" (optional - user's choice).
                     If not provided, auto-selects based on geography/saved preference.
            billing_name: Customer/company name for billing (required for first checkout)
            billing_email: Email for billing notifications (required for first checkout)

        Returns:
            Dict with checkout_url, session_id, and gateway used.
        """
        self._require_billing()
        payload = {
            "tenant_id": self.tenant_id,
            "plan": plan,
            "billing_cycle": billing_cycle,
        }
        if gateway:
            payload["gateway"] = gateway
        if billing_name:
            payload["billing_name"] = billing_name
        if billing_email:
            payload["billing_email"] = billing_email
        return await self._request_post_json("initiate_checkout", payload, api_base=self.billing_api_base)

    async def verify_checkout(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Verify payment completion after checkout."""
        self._require_billing()
        payload = {"tenant_id": self.tenant_id}
        if session_id:
            payload["session_id"] = session_id
        return await self._request_post_json("verify_checkout", payload, api_base=self.billing_api_base)

    async def verify_razorpay_payment(
        self,
        razorpay_payment_id: str,
        razorpay_subscription_id: str,
        razorpay_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Verify Razorpay embedded checkout payment signature.

        Args:
            razorpay_payment_id: Payment ID from Razorpay widget response
            razorpay_subscription_id: Subscription ID from Razorpay widget response
            razorpay_signature: Signature from Razorpay widget response

        Returns:
            {"success": True, "message": str, "subscription_status": str, "plan": str, "monthly_quota": int}
        """
        self._require_billing()
        payload = {
            "tenant_id": self.tenant_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_subscription_id": razorpay_subscription_id,
            "razorpay_signature": razorpay_signature,
        }
        return await self._request_post_json("verify_razorpay_payment", payload, api_base=self.billing_api_base)

    async def get_usage_dashboard(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive usage and billing data for dashboard."""
        self._require_billing()
        return await self._request_post_json(
            "get_usage_dashboard", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def get_usage_history(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """Get historical usage data for charts."""
        self._require_billing()
        payload = {"tenant_id": self.tenant_id, "days": days}
        return await self._request_post_json("get_usage_history", payload, api_base=self.billing_api_base)

    async def get_invoices(self, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Get invoice history."""
        self._require_billing()
        payload = {"tenant_id": self.tenant_id, "limit": limit}
        return await self._request_post_json("get_invoices", payload, api_base=self.billing_api_base)

    async def get_upcoming_invoice(self) -> Optional[Dict[str, Any]]:
        """Get upcoming invoice preview (Stripe only)."""
        self._require_billing()
        return await self._request_post_json(
            "get_upcoming_invoice", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def get_payment_methods(self) -> Optional[Dict[str, Any]]:
        """Get saved payment methods."""
        self._require_billing()
        return await self._request_post_json(
            "get_payment_methods", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def upgrade_plan(
        self,
        new_plan: str,
        billing_cycle: str = "monthly",
        gateway: Optional[str] = None,
        billing_name: Optional[str] = None,
        billing_email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Change subscription plan (upgrade or downgrade).

        The API automatically detects whether this is an upgrade or downgrade
        based on plan hierarchy: Free < Starter < Pro < Enterprise

        **Upgrades** (e.g., Starter → Pro):
            - Applied immediately with proration
            - New quota available instantly

        **Downgrades** (e.g., Pro → Starter):
            - Scheduled for end of billing period
            - User keeps current plan benefits until effective_date
            - Response includes `effective_date` field

        **Downgrade to Free**:
            - Cancels subscription at period end
            - Switches to Free tier when period ends

        Args:
            new_plan: Plan name ("Free", "Starter", "Pro", "Enterprise")
            billing_cycle: "monthly" or "annual" (default: monthly)
            gateway: "stripe" or "razorpay" (optional - user's choice).
                     If not provided, uses saved gateway or auto-selects.
            billing_name: Customer/company name for billing (required for first payment)
            billing_email: Email for billing notifications (required for first payment)

        Returns:
            For upgrades:
                {"success": True, "message": "Subscription upgraded to Pro", "subscription_id": "..."}

            For downgrades:
                {"success": True, "message": "Your plan will change to Starter on 2025-02-28...",
                 "effective_date": "2025-02-28"}

            If checkout required (new subscription):
                {"checkout_url": "https://...", "session_id": "...", "gateway": "stripe"}

        Example:
            >>> # Upgrade (immediate)
            >>> result = await client.upgrade_plan("Pro")
            >>> print(result["message"])

            >>> # Downgrade (scheduled)
            >>> result = await client.upgrade_plan("Starter")
            >>> if result.get("effective_date"):
            ...     print(f"Change scheduled for {result['effective_date']}")
        """
        self._require_billing()
        payload = {
            "tenant_id": self.tenant_id,
            "new_plan": new_plan,
            "billing_cycle": billing_cycle,
        }
        if gateway:
            payload["gateway"] = gateway
        if billing_name:
            payload["billing_name"] = billing_name
        if billing_email:
            payload["billing_email"] = billing_email
        return await self._request_post_json("upgrade_plan", payload, api_base=self.billing_api_base)

    async def downgrade_to_free(self) -> Optional[Dict[str, Any]]:
        """
        Schedule downgrade to the Free plan at end of billing period.

        This cancels the active subscription at the end of the current billing
        period and switches to the Free tier. User retains current plan benefits
        until the effective date.

        Returns:
            Dict with success status and effective date:
            {
                "success": True,
                "message": "Your plan will change to Free on 2025-02-28...",
                "effective_date": "2025-02-28"
            }

        Example:
            >>> result = await client.downgrade_to_free()
            >>> if result["success"]:
            ...     print(f"Downgrade scheduled for {result['effective_date']}")
        """
        self._require_billing()
        return await self._request_post_json(
            "downgrade_to_free", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def cancel_scheduled_change(self) -> Optional[Dict[str, Any]]:
        """
        Cancel a pending downgrade that was scheduled for end of billing period.

        Use this to undo a scheduled downgrade before it takes effect.
        Also clears any scheduled plan changes when reactivating.

        Returns:
            Dict with success status:
            {
                "success": True,
                "message": "Scheduled plan change cancelled. You will remain on Pro plan."
            }

            Or if no scheduled change:
            {
                "success": False,
                "message": "No scheduled plan change to cancel"
            }

        Example:
            >>> # Check if there's a scheduled change first
            >>> info = await client.get_tenant_info()
            >>> if info["subscription"].get("scheduled_plan_change"):
            ...     result = await client.cancel_scheduled_change()
            ...     print(result["message"])
        """
        self._require_billing()
        return await self._request_post_json(
            "cancel_scheduled_change", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def cancel_subscription(self, cancel_immediately: bool = False) -> Optional[Dict[str, Any]]:
        """Cancel subscription."""
        self._require_billing()
        payload = {
            "tenant_id": self.tenant_id,
            "cancel_immediately": cancel_immediately,
        }
        return await self._request_post_json("cancel_subscription", payload, api_base=self.billing_api_base)

    async def reactivate_subscription(self) -> Optional[Dict[str, Any]]:
        """Reactivate a subscription that was set to cancel at period end."""
        self._require_billing()
        return await self._request_post_json(
            "reactivate_subscription", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def pause_subscription(self) -> Optional[Dict[str, Any]]:
        """Pause subscription (Razorpay only)."""
        self._require_billing()
        return await self._request_post_json(
            "pause_subscription", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def resume_subscription(self) -> Optional[Dict[str, Any]]:
        """Resume a paused subscription (Razorpay only)."""
        self._require_billing()
        return await self._request_post_json(
            "resume_subscription", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def update_payment_method(self) -> Optional[Dict[str, Any]]:
        """Get URL to update payment method."""
        self._require_billing()
        return await self._request_post_json(
            "update_payment_method", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def get_subscription_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current subscription status including any scheduled changes.

        Returns detailed subscription info including:
        - Current plan and status
        - Token quota and usage
        - Billing cycle dates
        - Scheduled plan changes (if any downgrade is pending)

        Returns:
            Dict with subscription status:
            {
                "success": True,
                "subscription": {
                    "plan": "Pro",
                    "status": "Active",
                    "payment_status": "active",
                    "quota": 2000000,
                    "used": 500000,
                    "remaining": 1500000,
                    "billing_cycle_start": "2025-02-01",
                    "billing_cycle_end": "2025-02-28",
                    "cancel_at_period_end": False,
                    "payment_gateway": "stripe",
                    "scheduled_change": {
                        "new_plan": "Starter",
                        "effective_date": "2025-02-28"
                    } or None
                }
            }

        Example:
            >>> status = await client.get_subscription_status()
            >>> if status["subscription"]["scheduled_change"]:
            ...     print(f"Downgrade scheduled for {status['subscription']['scheduled_change']['effective_date']}")
        """
        self._require_billing()
        return await self._request_get(
            "get_subscription_status", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def get_billing_history(self, limit: int = 20) -> Optional[Dict[str, Any]]:
        """
        Get payment/billing history for this tenant.

        Returns a list of payment events (charges, failures, subscription changes)
        and optionally a portal URL for downloading invoices (Stripe only).

        Args:
            limit: Maximum number of records to return (default: 20)

        Returns:
            Dict with billing history:
            {
                "success": True,
                "history": [
                    {
                        "date": "2025-02-01",
                        "datetime": "2025-02-01 10:30:00",
                        "event": "Payment Successful",
                        "event_type": "invoice.payment_succeeded",
                        "amount": 19.00,
                        "currency": "USD",
                        "status": "success",
                        "gateway": "stripe"
                    },
                    ...
                ],
                "portal_url": "https://billing.stripe.com/session/xxx"  # Stripe only
            }

        Example:
            >>> history = await client.get_billing_history(limit=10)
            >>> for item in history["history"]:
            ...     print(f"{item['date']}: {item['event']} - ${item['amount']}")
        """
        self._require_billing()
        return await self._request_get(
            "get_billing_history", {"tenant_id": self.tenant_id, "limit": limit},
            api_base=self.billing_api_base,
        )

    # =========================================================================
    # Prepaid Credit APIs
    # =========================================================================

    async def get_credit_balance(self) -> Optional[Dict[str, Any]]:
        """
        Get prepaid credit balance and recent transaction history.

        Returns:
            Dict with ``balance`` (int) and ``transactions`` (list).

        Example:
            >>> balance = await client.get_credit_balance()
            >>> print(f"Credit balance: {balance['balance']:,} tokens")
        """
        self._require_billing()
        return await self._request_post_json(
            "get_credit_balance", {"tenant_id": self.tenant_id},
            api_base=self.billing_api_base,
        )

    async def purchase_credits(
        self, token_amount: int, gateway: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a one-time checkout session for purchasing prepaid credits.

        Args:
            token_amount: Number of tokens to purchase
            gateway: "stripe" or "razorpay" (optional, auto-selects)

        Returns:
            Gateway-specific checkout data (checkout URL or order ID).

        Example:
            >>> result = await client.purchase_credits(100000, gateway="stripe")
            >>> print(f"Checkout URL: {result['checkout_url']}")
        """
        self._require_billing()
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "token_amount": token_amount,
        }
        if gateway:
            payload["gateway"] = gateway
        return await self._request_post_json(
            "purchase_credits", payload,
            api_base=self.billing_api_base,
        )

    # =========================================================================
    # Conversation APIs
    # =========================================================================

    async def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """List conversations for tenant."""
        params = {
            "tenant_id": self.tenant_id,
            "limit": limit,
            "offset": offset,
            "include_deleted": include_deleted,
        }
        if user_id:
            params["user_id"] = user_id
        return await self._request_get("conversations.list_conversations", params)

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific conversation."""
        params = {"tenant_id": self.tenant_id, "conversation_id": conversation_id}
        return await self._request_get("conversations.get_conversation", params)

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Get messages for a specific conversation."""
        params = {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
            "limit": limit,
            "offset": offset,
        }
        return await self._request_get("conversations.get_messages", params)

    # =========================================================================
    # User & MCP Server APIs
    # =========================================================================

    async def register_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a user with Assistant Runtime."""
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        if display_name:
            params["display_name"] = display_name
        if custom_instructions:
            params["custom_instructions"] = custom_instructions
        return await self._request_post_form("users.register_user", params)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details including MCP server count."""
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        return await self._request_get("users.get_user", params)

    async def get_user_auth_status(self, user_id: str) -> Dict[str, Any]:
        """Check user authentication status and MCP server readiness."""
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        try:
            return await self._request_get("users.get_user_auth_status", params)
        except Exception as e:
            return {
                "user_exists": False,
                "ready_for_streaming": False,
                "error": str(e),
            }

    async def add_user_mcp_server(
        self,
        user_id: str,
        server_name: str,
        endpoint_url: str,
        transport_type: str = "SSE",
        auth_type: str = "OAuth",
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_in: int = 3600,
    ) -> Dict[str, Any]:
        """Add or update an MCP server for a user."""
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "server_name": server_name,
            "endpoint_url": endpoint_url,
            "transport_type": transport_type,
            "auth_type": auth_type,
        }
        if access_token:
            params["access_token"] = access_token
        if refresh_token:
            params["refresh_token"] = refresh_token
        if token_expires_in:
            params["token_expires_in"] = str(token_expires_in)
        return await self._request_post_form("users.add_user_mcp_server", params)

    async def get_user_mcp_servers(self, user_id: str) -> Dict[str, Any]:
        """Get all MCP servers configured for a user."""
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        try:
            return await self._request_get("users.get_user_mcp_servers", params)
        except Exception as e:
            return {"user_id": user_id, "mcp_servers": [], "error": str(e)}

    async def remove_user_mcp_server(self, user_id: str, server_name: str) -> Dict[str, Any]:
        """Remove an MCP server from a user."""
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "server_name": server_name,
        }
        return await self._request_delete("users.remove_user_mcp_server", params)

    async def list_users(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_mcp_count: bool = True,
    ) -> Dict[str, Any]:
        """
        List all users for this tenant with pagination and filtering.

        Args:
            status: Filter by status (Active, Suspended, Revoked) - optional
            limit: Max results per page (default 50, max 100)
            offset: Pagination offset
            include_mcp_count: Include MCP server count per user (default True)

        Returns:
            Dict with users list and pagination info
        """
        params = {
            "tenant_id": self.tenant_id,
            "limit": str(limit),
            "offset": str(offset),
            "include_mcp_count": str(include_mcp_count).lower(),
        }
        if status:
            params["status"] = status
        return await self._request_get("users.list_users", params)

    async def update_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update user display name and/or custom instructions.

        Args:
            user_id: User identifier
            display_name: New display name (optional)
            custom_instructions: New custom instructions (optional)

        Returns:
            Dict with success status and message
        """
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        if display_name is not None:
            params["display_name"] = display_name
        if custom_instructions is not None:
            params["custom_instructions"] = custom_instructions
        return await self._request_post_form("users.update_user", params)

    async def deregister_user(self, user_id: str) -> Dict[str, Any]:
        """
        Permanently delete a user and all their MCP servers.

        This action is irreversible. Conversations are retained for audit.

        Args:
            user_id: User identifier

        Returns:
            Dict with success status and deleted MCP server count
        """
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        return await self._request_post_form("users.deregister_user", params)

    async def get_user_limit_status(self) -> Dict[str, Any]:
        """
        Get user count and limit for this tenant.

        Returns:
            Dict with plan, max_users, active_users, remaining, is_unlimited
        """
        params = {"tenant_id": self.tenant_id}
        return await self._request_get("users.get_user_limit_status", params)

    async def suspend_user(self, user_id: str) -> Dict[str, Any]:
        """
        Suspend a user (disable their access).

        Args:
            user_id: User identifier

        Returns:
            Dict with success status and message
        """
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        return await self._request_post_form("users.suspend_user", params)

    async def revoke_user(self, user_id: str) -> Dict[str, Any]:
        """
        Revoke a user (permanently disable, also disables their MCP servers).

        Args:
            user_id: User identifier

        Returns:
            Dict with success status and message
        """
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        return await self._request_post_form("users.revoke_user", params)

    # =========================================================================
    # Workflow APIs
    # =========================================================================
    # These methods route through workflows_api_base → assistant_runtime_workflows.api

    async def create_workflow(
        self,
        workflow_name: str,
        graph_json: Optional[str] = None,
        description: str = "",
        default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
        error_strategy: str = "fail_fast",
        timeout_seconds: int = 600,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new workflow.

        Args:
            workflow_name: Human-readable workflow name (must be unique per tenant)
            graph_json: Workflow graph JSON string (optional, can be set later)
            description: Optional description
            default_model_id: Default LLM model for agent nodes
            default_user_id: Default user whose MCP tools are used
            error_strategy: "fail_fast", "continue", or "retry" (default: fail_fast)
            timeout_seconds: Max execution time in seconds (default: 600)

        Returns:
            {"name": str, "workflow_name": str, "status": str, "version": int}

        Example:
            >>> wf = await client.create_workflow("Daily Report Generator")
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "workflow_name": workflow_name,
            "description": description,
            "error_strategy": error_strategy,
            "timeout_seconds": timeout_seconds,
        }
        if graph_json:
            payload["graph_json"] = graph_json
        if default_model_id:
            payload["default_model_id"] = default_model_id
        if default_user_id:
            payload["default_user_id"] = default_user_id
        return await self._request_post_json(
            "workflows.create_workflow", payload,
            api_base=self.workflows_api_base,
        )

    async def get_workflow(
        self,
        name: Optional[str] = None,
        workflow_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a workflow definition by document name or human-readable name.

        Args:
            name: Document name (e.g., "WF-00001")
            workflow_name: Human-readable name

        Returns:
            Full workflow definition including graph_json, schedule, and stats.
        """
        params: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if name:
            params["name"] = name
        if workflow_name:
            params["workflow_name"] = workflow_name
        return await self._request_get(
            "workflows.get_workflow", params,
            api_base=self.workflows_api_base,
        )

    async def update_workflow(
        self,
        name: str,
        graph_json: Optional[str] = None,
        workflow_name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
        error_strategy: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_node_executions: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a workflow. Increments version when graph_json changes.

        Args:
            name: Document name (e.g., "WF-00001")
            graph_json: Updated workflow graph (triggers version increment)
            workflow_name: New human-readable name
            description: New description
            status: New status ("Draft", "Active", "Paused", "Archived")
            default_model_id: New default model
            default_user_id: New default user
            error_strategy: New error strategy
            timeout_seconds: New timeout
            max_node_executions: New max executions (loop safety)
            max_retries: New max retries

        Returns:
            {"name": str, "workflow_name": str, "status": str, "version": int}
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
        }
        if graph_json is not None:
            payload["graph_json"] = graph_json
        if workflow_name is not None:
            payload["workflow_name"] = workflow_name
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        if default_model_id is not None:
            payload["default_model_id"] = default_model_id
        if default_user_id is not None:
            payload["default_user_id"] = default_user_id
        if error_strategy is not None:
            payload["error_strategy"] = error_strategy
        if timeout_seconds is not None:
            payload["timeout_seconds"] = timeout_seconds
        if max_node_executions is not None:
            payload["max_node_executions"] = max_node_executions
        if max_retries is not None:
            payload["max_retries"] = max_retries
        return await self._request_post_json(
            "workflows.update_workflow", payload,
            api_base=self.workflows_api_base,
        )

    async def delete_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Soft-delete a workflow (sets status to Archived).

        Args:
            name: Document name (e.g., "WF-00001")

        Returns:
            {"status": "archived", "name": str}
        """
        payload = {"tenant_id": self.tenant_id, "name": name}
        return await self._request_post_json(
            "workflows.delete_workflow", payload,
            api_base=self.workflows_api_base,
        )

    async def list_workflows(
        self,
        status: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        List workflows for this tenant.

        Args:
            status: Filter by status (optional, excludes Archived by default)
            page: Page number, 0-indexed (default: 0)
            page_size: Items per page, max 100 (default: 20)

        Returns:
            {"workflows": [...], "total": int, "page": int, "page_size": int}
        """
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "page": str(page),
            "page_size": str(page_size),
        }
        if status:
            params["status"] = status
        return await self._request_get(
            "workflows.list_workflows", params,
            api_base=self.workflows_api_base,
        )

    async def execute_workflow(
        self,
        name: str,
        input_data: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Manually trigger workflow execution.

        The workflow is enqueued as a background job. Use ``get_workflow_run``
        to poll for completion.

        Args:
            name: AR Workflow document name (e.g., "WF-00001")
            input_data: Input data (JSON string or plain text)
            user_id: User triggering the execution

        Returns:
            {"status": "queued", "workflow": str, "workflow_name": str, "message": str}
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
        }
        if input_data:
            payload["input_data"] = input_data
        if user_id:
            payload["user_id"] = user_id
        return await self._request_post_json(
            "workflows.execute_workflow", payload,
            api_base=self.workflows_api_base,
        )

    async def cancel_workflow_run(self, run_name: str) -> Optional[Dict[str, Any]]:
        """
        Cancel a queued or running workflow execution.

        Args:
            run_name: AR Workflow Run document name

        Returns:
            {"status": "cancelled", "run_name": str}
        """
        payload = {"tenant_id": self.tenant_id, "run_name": run_name}
        return await self._request_post_json(
            "workflows.cancel_run", payload,
            api_base=self.workflows_api_base,
        )

    async def get_workflow_run(self, run_name: str) -> Optional[Dict[str, Any]]:
        """
        Get execution run details including per-node results.

        Args:
            run_name: AR Workflow Run document name

        Returns:
            Run details with nested ``node_runs`` list.
        """
        params = {"tenant_id": self.tenant_id, "run_name": run_name}
        return await self._request_get(
            "workflows.get_run", params,
            api_base=self.workflows_api_base,
        )

    async def list_workflow_runs(
        self,
        workflow_name: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        List workflow execution runs.

        Args:
            workflow_name: Filter by workflow document name (optional)
            status: Filter by status (optional)
            page: Page number, 0-indexed (default: 0)
            page_size: Items per page, max 100 (default: 20)

        Returns:
            {"runs": [...], "total": int, "page": int, "page_size": int}
        """
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "page": str(page),
            "page_size": str(page_size),
        }
        if workflow_name:
            params["workflow_name"] = workflow_name
        if status:
            params["status"] = status
        return await self._request_get(
            "workflows.list_runs", params,
            api_base=self.workflows_api_base,
        )

    async def set_workflow_schedule(
        self,
        name: str,
        cron_expression: str,
        timezone: str = "UTC",
        enabled: bool = True,
        default_input: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Set or update cron schedule for a workflow.

        Args:
            name: AR Workflow document name
            cron_expression: Standard cron expression (e.g., "0 9 * * 1-5")
            timezone: IANA timezone (default: "UTC")
            enabled: Whether schedule is active (default: True)
            default_input: Input data for scheduled runs (JSON string)

        Returns:
            {"name": str, "schedule_enabled": bool, "cron_expression": str,
             "timezone": str, "next_run_at": str}
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
            "cron_expression": cron_expression,
            "timezone": timezone,
            "enabled": enabled,
        }
        if default_input is not None:
            payload["default_input"] = default_input
        return await self._request_post_json(
            "workflows.set_schedule", payload,
            api_base=self.workflows_api_base,
        )

    async def validate_workflow_graph(self, graph_json: str) -> Optional[Dict[str, Any]]:
        """
        Validate a workflow graph JSON without saving.

        Args:
            graph_json: Graph JSON string to validate

        Returns:
            If valid: {"valid": True, "stats": {"total_nodes": int, "agent_count": int, ...}}
            If invalid: {"valid": False, "error": str}
        """
        payload = {"tenant_id": self.tenant_id, "graph_json": graph_json}
        return await self._request_post_json(
            "workflows.validate_graph", payload,
            api_base=self.workflows_api_base,
        )

    async def test_workflow_node(
        self,
        node_json: str,
        input_text: str = "Test input",
        default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a single node in isolation for testing.

        Creates a temporary workflow with input -> node -> output,
        executes it, and returns the result.

        Args:
            node_json: Single node definition as JSON string
            input_text: Test input text (default: "Test input")
            default_model_id: LLM model to use for agent nodes
            default_user_id: User whose MCP tools to use

        Returns:
            {"status": str, "node_result": {...}, "duration_ms": int, "tokens_used": int}
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "node_json": node_json,
            "input_text": input_text,
        }
        if default_model_id:
            payload["default_model_id"] = default_model_id
        if default_user_id:
            payload["default_user_id"] = default_user_id
        return await self._request_post_json(
            "workflows.test_node", payload,
            timeout=120.0,
            api_base=self.workflows_api_base,
        )

    async def resolve_workflow_tools(
        self,
        user_id: str,
        tool_directives: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Preview how tool directives resolve against a user's MCP tools.

        Checks each tool directive against the user's available MCP tools
        and returns resolution status. Used by the workflow builder to show
        availability indicators on tool directives.

        Args:
            user_id: User whose MCP tools to check against
            tool_directives: List of directive dicts with at least
                ``tool_name`` and ``capability``

        Returns:
            {
                "resolved": [
                    {
                        "capability": "web_search",
                        "tool_name": "web_search",
                        "status": "resolved" | "missing",
                        "prefixed_name": "brave:web_search" | null,
                        "server_name": "brave" | null,
                        "inputSchema": {...} | null,
                        "description": "..."
                    }
                ],
                "all_tools_available": true | false,
                "missing_tools": ["tool_name_x"]
            }

        Example:
            >>> result = await client.resolve_workflow_tools(
            ...     "user@example.com",
            ...     [{"capability": "web_search", "tool_name": "web_search"}]
            ... )
            >>> print(result["all_tools_available"])
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "tool_directives": json.dumps(tool_directives),
        }
        return await self._request_post_json(
            "workflows.resolve_workflow_tools", payload,
            api_base=self.workflows_api_base,
        )

    # --- Workflow Templates ---

    async def export_workflow(
        self,
        name: str,
        template_name: Optional[str] = None,
        category: str = "General",
        save_as_template: bool = False,
        is_public: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Export a workflow as a portable template JSON.

        Strips tenant-specific data, extracts variables, detects required tools.
        Optionally saves as a registered template owned by the tenant.

        Args:
            name: AR Workflow document name
            template_name: Override template name (defaults to workflow_name)
            category: Template category
            save_as_template: If True, also creates an AR Workflow Template record
            is_public: If True, the saved template is visible to all tenants

        Returns:
            {"template": {...}, "template_record": str (if saved)}
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
            "category": category,
            "save_as_template": save_as_template,
            "is_public": is_public,
        }
        if template_name:
            payload["template_name"] = template_name
        return await self._request_post_json(
            "workflows.export_workflow", payload,
            api_base=self.workflows_api_base,
        )

    async def list_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        List published workflow templates.

        When ``user_id`` is provided, templates requiring MCP capabilities
        the user lacks are excluded (matched against the user's MCP server
        ``capabilities`` tags).

        Args:
            category: Filter by category (optional)
            search: Text search on name, description, tags (optional)
            user_id: User identifier for capability-based filtering (optional)
            page: Page number (0-indexed)
            page_size: Items per page (max 100)

        Returns:
            {"templates": [...], "total": int, "page": int, "page_size": int}
        """
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "page": page,
            "page_size": page_size,
        }
        if category:
            params["category"] = category
        if search:
            params["search"] = search
        if user_id:
            params["user_id"] = user_id
        return await self._request_get(
            "workflows.list_templates", params,
            api_base=self.workflows_api_base,
        )

    async def get_template(
        self,
        template_name: Optional[str] = None,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get full template details including graph_json and variables_schema.

        When ``user_id`` is provided, the response includes
        ``user_has_capabilities`` (bool) and ``missing_capabilities`` (list)
        indicating whether the user's MCP servers satisfy the template's
        ``tool_hints``.

        Args:
            template_name: Template name (or)
            name: Document name
            user_id: User identifier for capability checking (optional)

        Returns:
            Full template details dict
        """
        params: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if name:
            params["name"] = name
        elif template_name:
            params["template_name"] = template_name
        if user_id:
            params["user_id"] = user_id
        return await self._request_get(
            "workflows.get_template", params,
            api_base=self.workflows_api_base,
        )

    async def import_template(
        self,
        user_id: str,
        template_name: Optional[str] = None,
        template_json: Optional[str] = None,
        workflow_name: Optional[str] = None,
        variables: Optional[str] = None,
        default_user_id: Optional[str] = None,
        default_model_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Import a template as a new workflow.

        Accepts either a registered template (by name) or inline template JSON.

        Args:
            user_id: User who will own the workflow
            template_name: Registered template name (or)
            template_json: Inline template JSON
            workflow_name: Custom workflow name (defaults to template name)
            variables: JSON string of variable overrides
            default_user_id: User whose MCP tools will be used
            default_model_id: Override LLM model

        Returns:
            {"workflow": {...}, "warnings": [...], "variables_applied": {...}}
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        if template_name:
            payload["template_name"] = template_name
        if template_json:
            payload["template_json"] = template_json
        if workflow_name:
            payload["workflow_name"] = workflow_name
        if variables:
            payload["variables"] = variables
        if default_user_id:
            payload["default_user_id"] = default_user_id
        if default_model_id:
            payload["default_model_id"] = default_model_id
        return await self._request_post_json(
            "workflows.import_template", payload,
            api_base=self.workflows_api_base,
        )

    async def update_template(
        self,
        name: str,
        template_name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_published: Optional[bool] = None,
        graph_json: Optional[str] = None,
        variables_schema: Optional[str] = None,
        default_variables: Optional[str] = None,
        default_model_id: Optional[str] = None,
        error_strategy: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        tags: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a tenant's own template.

        Cannot modify official templates. Only the owning tenant can update.

        Args:
            name: AR Workflow Template document name
            (all other fields are optional updates)

        Returns:
            {"name": str, "template_name": str, "is_public": bool, "is_published": bool}
        """
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
        }
        if template_name is not None:
            payload["template_name"] = template_name
        if description is not None:
            payload["description"] = description
        if category is not None:
            payload["category"] = category
        if is_public is not None:
            payload["is_public"] = is_public
        if is_published is not None:
            payload["is_published"] = is_published
        if graph_json is not None:
            payload["graph_json"] = graph_json
        if variables_schema is not None:
            payload["variables_schema"] = variables_schema
        if default_variables is not None:
            payload["default_variables"] = default_variables
        if default_model_id is not None:
            payload["default_model_id"] = default_model_id
        if error_strategy is not None:
            payload["error_strategy"] = error_strategy
        if timeout_seconds is not None:
            payload["timeout_seconds"] = timeout_seconds
        if tags is not None:
            payload["tags"] = tags
        return await self._request_post_json(
            "workflows.update_template", payload,
            api_base=self.workflows_api_base,
        )

    async def delete_template(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Delete a tenant's own template.

        Cannot delete official templates. Only the owning tenant can delete.

        Args:
            name: AR Workflow Template document name

        Returns:
            {"status": "deleted", "name": str}
        """
        return await self._request_post_json(
            "workflows.delete_template",
            {"tenant_id": self.tenant_id, "name": name},
            api_base=self.workflows_api_base,
        )

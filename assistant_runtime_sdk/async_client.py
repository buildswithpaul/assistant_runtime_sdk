# Assistant Runtime SDK - Asynchronous Client
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Asynchronous Assistant Runtime client using aiohttp.

Requires the 'async' extra: pip install assistant_runtime_sdk[async]
"""

import os
from typing import AsyncGenerator, List, Optional, Dict, Any

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore

from .base import BaseAssistantRuntimeClient
from .exceptions import (
    ARAPIError,
    ARAuthenticationError,
    ARTimeoutError,
    ARConnectionError,
    ARConfigurationError,
)


class AsyncAssistantRuntimeClient(BaseAssistantRuntimeClient):
    """
    Asynchronous Assistant Runtime client using aiohttp.

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
        marketplace_api_base: Optional[str] = None,
        voice_api_base: Optional[str] = None,
        site_url: Optional[str] = None,
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
            marketplace_api_base: Override URL for marketplace API endpoints
            voice_api_base: Override URL for voice/transcription API endpoints
            site_url: This installation's canonical URL (e.g. ``"https://mysite.example.com"``).
                Automatically included in signed payloads for origin binding (Phase 2).
        """
        if aiohttp is None:
            raise ImportError(
                "aiohttp is required for AsyncAssistantRuntimeClient. "
                "Install it with: pip install assistant_runtime_sdk[async]"
            )

        super().__init__(
            tenant_id, tenant_secret, ar_url, logger, timeout,
            billing_api_base, memory_api_base, workflows_api_base,
            marketplace_api_base, voice_api_base, site_url,
        )
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

    async def _handle_error_response(
        self, response: "aiohttp.ClientResponse", endpoint: str, method: str,
    ) -> None:
        """Check response status and raise appropriate exceptions.

        Must be called BEFORE raise_for_status() so we can read the body
        and raise specific exception types (e.g. ARAuthenticationError for 401).
        """
        if response.status < 400:
            return

        # Read error body for better messages. The full payload is
        # forwarded to ARAPIError.response_data so callers can read
        # any extra keys AR set (e.g. tenant_owner_user_id).
        msg = None
        data: Optional[Dict[str, Any]] = None
        try:
            data = await response.json()
            msg = self._extract_error_from_data(data)
        except Exception:
            pass

        if response.status == 401:
            raise ARAuthenticationError(msg or "Authentication failed")

        raise ARAPIError(
            msg or f"{method} {endpoint} failed with status {response.status}",
            status_code=response.status,
            response_data=data,
        )

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
        params = self._with_site_url(params)
        headers = self._get_headers(params, for_query_string=True)

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.get(url, params=params, headers=headers, timeout=timeout_obj) as response:
                await self._handle_error_response(response, endpoint, "GET")
                data = await response.json()
                return data.get("message", data)
        except (ARAuthenticationError, ARAPIError):
            raise
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"GET {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"GET {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientError as e:
            self._log_error(f"GET {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    async def _request_get_raw(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> tuple:
        """Make authenticated async GET request expecting raw binary response.

        Returns:
            (content_bytes, content_type, filename) tuple
        """
        session = self._ensure_session()
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        params = self._with_site_url(params)
        headers = self._get_headers(params, for_query_string=True)

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.get(url, params=params, headers=headers, timeout=timeout_obj) as response:
                await self._handle_error_response(response, endpoint, "GET raw")
                content = await response.read()

                content_type = response.headers.get("Content-Type", "application/octet-stream")
                filename = ""
                cd = response.headers.get("Content-Disposition", "")
                if "filename=" in cd:
                    parts = cd.split("filename=")
                    if len(parts) > 1:
                        filename = parts[1].strip().strip('"')

                return content, content_type, filename
        except (ARAuthenticationError, ARAPIError):
            raise
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"GET raw {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"GET raw {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientError as e:
            self._log_error(f"GET raw {endpoint} error: {e}")
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
        payload = self._with_site_url(payload)
        headers = {
            **self._get_headers(payload, for_query_string=False),
            "Content-Type": "application/json",
        }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.post(url, json=payload, headers=headers, timeout=timeout_obj) as response:
                await self._handle_error_response(response, endpoint, "POST")
                data = await response.json()
                return data.get("message", data)
        except (ARAuthenticationError, ARAPIError):
            raise
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"POST {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"POST {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
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
        params = self._with_site_url(params)
        headers = {
            **self._get_headers(params, for_query_string=True),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.post(url, data=params, headers=headers, timeout=timeout_obj) as response:
                await self._handle_error_response(response, endpoint, "POST form")
                data = await response.json()
                return data.get("message", data)
        except (ARAuthenticationError, ARAPIError):
            raise
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"POST form {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"POST form {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
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
        params = self._with_site_url(params)
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
                await self._handle_error_response(response, endpoint, "POST multipart")
                data = await response.json()
                return data.get("message", data)
        except (ARAuthenticationError, ARAPIError):
            raise
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"POST multipart {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"POST multipart {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
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
        params = self._with_site_url(params)
        headers = self._get_headers(params, for_query_string=True)

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout or self.timeout)
            async with session.delete(url, params=params, headers=headers, timeout=timeout_obj) as response:
                await self._handle_error_response(response, endpoint, "DELETE")
                data = await response.json()
                return data.get("message", data)
        except (ARAuthenticationError, ARAPIError):
            raise
        except aiohttp.ServerTimeoutError as e:
            self._log_error(f"DELETE {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except aiohttp.ClientConnectorError as e:
            self._log_error(f"DELETE {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except aiohttp.ClientError as e:
            self._log_error(f"DELETE {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    # =========================================================================
    # Streaming API
    # =========================================================================

    async def stream_chat(
        self,
        session_id: str,
        message: Optional[str],
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        system_prompt_addendum: Optional[str] = None,
        client_type: Optional[str] = None,
        interrupt_response: Optional[List[Dict[str, str]]] = None,
        message_id: Optional[str] = None,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async version of AssistantRuntimeClient.stream_chat.

        On ``stream_complete``, ``event['session_state']`` is the updated signed
        blob — store it and pass it as ``session_state`` on the next turn.
        """
        session = self._ensure_session()
        payload = self._prepare_stream_payload(
            session_id, message, user_id, context, model_id, attachments,
            system_prompt_addendum, client_type=client_type,
            interrupt_response=interrupt_response,
            message_id=message_id,
            session_state=session_state,
        )
        url = self._build_endpoint_url("streaming.stream_chat")
        payload = self._with_site_url(payload)
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

                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue

                    parsed = self._parse_sse_line(line_str)
                    if not parsed:
                        continue

                    if parsed["type"] == "heartbeat":
                        yield {"event": "heartbeat", "data": {}}
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
        """Async version of AssistantRuntimeClient.get_tenant_info."""
        endpoint, params = self._prepare_get_tenant_info()
        return await self._request_get(endpoint, params)

    async def accept_terms(self, terms_version: str, accepted_by: str) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.accept_terms."""
        endpoint, payload = self._prepare_accept_terms(terms_version, accepted_by)
        return await self._request_post_json(endpoint, payload)

    # =========================================================================
    # Model APIs
    # =========================================================================

    async def list_available_models(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_available_models."""
        endpoint, params = self._prepare_list_available_models()
        return await self._request_get(endpoint, params, timeout=timeout)

    async def get_available_models(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_available_models."""
        endpoint, params = self._prepare_get_available_models()
        return await self._request_get(endpoint, params)

    async def set_preferred_model(self, model_id: str) -> bool:
        """Async version of AssistantRuntimeClient.set_preferred_model."""
        endpoint, payload = self._prepare_set_preferred_model(model_id)
        result = await self._request_post_json(endpoint, payload)
        return result.get("success", False) if result else False

    # =========================================================================
    # Origin Binding APIs (Phase 2)
    # =========================================================================

    async def request_rebind(self, new_site_url: str) -> Dict[str, Any]:
        """Initiate a tenant rebind. Returns {"rebind_token": str, "expires_at": str}.

        When the site URL of an installation changes, call this to begin the
        rebind flow. AR sends a confirmation email to the tenant owner. After
        the owner clicks the link, call the module-level helper
        ``get_rotated_secret(ar_url, rebind_token)`` in the sync client with
        the token from the link to retrieve the new ``tenant_secret``.
        """
        return await self._request_post_json(
            "request_rebind",
            {"tenant_id": self.tenant_id, "new_site_url": new_site_url},
        )

    async def claim_tenant_email(self, owner_email: str) -> Dict[str, Any]:
        """Bootstrap an owner_email on a legacy tenant (one without a verified
        owner_email on file). AR sends a verification email; the email is only
        persisted to the tenant record after the owner clicks the link.
        """
        return await self._request_post_json(
            "claim_tenant_email",
            {"tenant_id": self.tenant_id, "owner_email": owner_email},
        )

    async def diagnose_registration(self) -> Dict[str, Any]:
        """Diagnose registration issues. Returns one of:

        - ``{"status": "ok", "bound_host": ..., "last_verification": ...}``
        - ``{"status": "origin_mismatch", "bound_host": ..., "claimed_host": ...,
          "remediation": "rebind", "rebind_url": ...}``
        """
        return await self._request_post_json(
            "diagnose_registration",
            {"tenant_id": self.tenant_id},
        )

    # =========================================================================
    # Prompt APIs
    # =========================================================================

    async def list_prompts(self, user_id: str, cursor: Optional[str] = None, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_prompts."""
        endpoint, params = self._prepare_list_prompts(user_id, cursor)
        return await self._request_get(endpoint, params, timeout=timeout)

    async def get_prompt(
        self,
        prompt_name: str,
        user_id: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_prompt."""
        endpoint, payload = self._prepare_get_prompt(prompt_name, user_id, arguments)
        return await self._request_post_json(endpoint, payload)

    # =========================================================================
    # Suggestion APIs
    # =========================================================================

    async def get_suggestions(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 8,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_suggestions."""
        endpoint, params = self._prepare_get_suggestions(user_id, context, limit)
        return await self._request_get(endpoint, params, timeout=timeout)

    # =========================================================================
    # Onboarding APIs
    # =========================================================================

    async def get_onboarding_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_onboarding_status."""
        endpoint, params = self._prepare_get_onboarding_status(user_id)
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    async def complete_onboarding(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.complete_onboarding."""
        endpoint, payload = self._prepare_complete_onboarding(user_id)
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    # =========================================================================
    # Document APIs (RAG)
    # =========================================================================

    async def upload_document(
        self,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
        visibility: Optional[str] = None,
        shared_with: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.upload_document."""
        endpoint, params, f_field, f_name, f_data, c_type = self._prepare_upload_document(
            file_path, file_data, file_name, content_type,
            user_id=user_id, visibility=visibility, shared_with=shared_with,
        )
        return await self._request_post_multipart(
            endpoint, params=params, file_field=f_field,
            file_name=f_name, file_data=f_data, content_type=c_type,
            timeout=120.0, api_base=self.memory_api_base,
        )

    async def list_documents(
        self, limit: int = 50, offset: int = 0, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_documents."""
        endpoint, params = self._prepare_list_documents(limit, offset, user_id=user_id)
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_document."""
        endpoint, params = self._prepare_get_document(document_id)
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    async def list_chunks(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_chunks."""
        endpoint, params = self._prepare_list_chunks(
            document_id, user_id=user_id, search=search, limit=limit, offset=offset
        )
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    async def get_document_content(
        self, document_id: str, user_id: Optional[str] = None
    ) -> tuple:
        """Async version of AssistantRuntimeClient.get_document_content."""
        endpoint, params = self._prepare_get_document_content(document_id, user_id=user_id)
        return await self._request_get_raw(endpoint, params, api_base=self.memory_api_base)

    async def delete_document(
        self, document_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.delete_document."""
        endpoint, payload = self._prepare_delete_document(document_id, user_id=user_id)
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    async def update_document_access(
        self,
        document_id: str,
        user_id: str,
        visibility: Optional[str] = None,
        add_users: Optional[List[str]] = None,
        remove_users: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.update_document_access."""
        endpoint, payload = self._prepare_update_document_access(
            document_id, user_id,
            visibility=visibility, add_users=add_users, remove_users=remove_users,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    async def get_storage_info(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_storage_info."""
        endpoint, params = self._prepare_get_storage_info()
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    # =========================================================================
    # Memory APIs (User Memory Viewer)
    # =========================================================================

    async def list_memories(
        self,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_memories."""
        endpoint, params = self._prepare_list_memories(user_id, memory_type, limit, offset)
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    async def delete_memory(self, user_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.delete_memory."""
        endpoint, payload = self._prepare_delete_memory(user_id, memory_id)
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    async def delete_all_memories(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.delete_all_memories."""
        endpoint, payload = self._prepare_delete_all_memories(user_id)
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    async def update_memory(self, user_id: str, memory_id: str, content: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.update_memory."""
        endpoint, payload = self._prepare_update_memory(user_id, memory_id, content)
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    async def get_memory_stats(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_memory_stats."""
        endpoint, params = self._prepare_get_memory_stats(user_id)
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    async def get_memory_summary(
        self,
        user_id: str,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async get AI-generated narrative summary of user's memories."""
        endpoint, params = self._prepare_get_memory_summary(user_id, force)
        return await self._request_get(endpoint, params, timeout=timeout, api_base=self.memory_api_base)

    # =========================================================================
    # Shared Knowledge APIs
    # =========================================================================

    async def get_shared_knowledge(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_shared_knowledge."""
        endpoint, params = self._prepare_get_shared_knowledge()
        return await self._request_get(endpoint, params, api_base=self.memory_api_base)

    async def update_shared_knowledge(self, content: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.update_shared_knowledge."""
        endpoint, payload = self._prepare_update_shared_knowledge(content)
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    async def share_memory_to_knowledge(self, user_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.share_memory_to_knowledge."""
        endpoint, payload = self._prepare_share_memory_to_knowledge(user_id, memory_id)
        return await self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    # =========================================================================
    # Resource APIs (Skills/Documentation)
    # =========================================================================

    async def list_resources(
        self,
        user_id: str,
        server: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_resources."""
        params = self._prepare_resource_params(user_id, server=server)
        return await self._request_get("resources.list_resources", params)

    async def read_resource(self, user_id: str, uri: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.read_resource."""
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
        """Async version of AssistantRuntimeClient.list_tools."""
        endpoint, params = self._prepare_list_tools(user_id, server)
        return await self._request_get(endpoint, params)

    # =========================================================================
    # Tool Preference APIs (per-user approval settings)
    # =========================================================================

    async def list_tool_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_tool_preferences."""
        endpoint, params = self._prepare_list_tool_preferences(user_id)
        return await self._request_get(endpoint, params)

    async def set_tool_preference(
        self,
        user_id: str,
        tool_name: str,
        preference: str,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.set_tool_preference."""
        endpoint, payload = self._prepare_set_tool_preference(user_id, tool_name, preference)
        return await self._request_post_json(endpoint, payload)

    # =========================================================================
    # Billing & Subscription APIs
    # =========================================================================

    async def check_billing_available(self) -> bool:
        """Async version of AssistantRuntimeClient.check_billing_available."""
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
        """Async version of AssistantRuntimeClient.get_plan_comparison."""
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
        """Async version of AssistantRuntimeClient.get_recommended_gateway."""
        endpoint, params = self._prepare_get_recommended_gateway()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def get_available_gateways(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_available_gateways."""
        endpoint, params = self._prepare_get_available_gateways()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def preview_plan_pricing(
        self, plan: str, billing_cycle: str = "monthly",
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.preview_plan_pricing."""
        endpoint, params = self._prepare_preview_plan_pricing(plan, billing_cycle)
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def add_user_seat(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.add_user_seat."""
        endpoint, params = self._prepare_add_user_seat()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def remove_user_seat(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.remove_user_seat."""
        endpoint, params = self._prepare_remove_user_seat()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def preview_seat_charge(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.preview_seat_charge."""
        endpoint, params = self._prepare_preview_seat_charge()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def download_invoice_pdf(self, ar_invoice_name: str) -> tuple:
        """Async version of AssistantRuntimeClient.download_invoice_pdf."""
        endpoint, params = self._prepare_download_invoice_pdf(ar_invoice_name)
        return await self._request_get_raw(
            endpoint, params, api_base=self.billing_api_base,
        )

    async def initiate_checkout(
        self,
        plan: str,
        billing_cycle: str = "monthly",
        gateway: Optional[str] = None,
        billing_name: Optional[str] = None,
        billing_email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.initiate_checkout."""
        endpoint, payload = self._prepare_initiate_checkout(plan, billing_cycle, gateway, billing_name, billing_email)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def verify_checkout(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.verify_checkout."""
        endpoint, payload = self._prepare_verify_checkout(session_id)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def verify_razorpay_payment(
        self,
        razorpay_payment_id: str,
        razorpay_subscription_id: str,
        razorpay_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.verify_razorpay_payment."""
        endpoint, payload = self._prepare_verify_razorpay_payment(razorpay_payment_id, razorpay_subscription_id, razorpay_signature)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def verify_razorpay_credit_payment(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.verify_razorpay_credit_payment."""
        endpoint, payload = self._prepare_verify_razorpay_credit_payment(razorpay_payment_id, razorpay_order_id, razorpay_signature)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def verify_seat_payment(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.verify_seat_payment."""
        endpoint, payload = self._prepare_verify_seat_payment(
            razorpay_payment_id, razorpay_order_id, razorpay_signature
        )
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def get_token_analytics(self, days: int = 30, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_token_analytics."""
        endpoint, payload = self._prepare_get_token_analytics(days, user_id)
        return await self._request_post_json(endpoint, payload)

    async def get_conversation_analytics(
        self, user_id: str = None, days: int = 30, limit: int = 50, offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_conversation_analytics."""
        endpoint, payload = self._prepare_get_conversation_analytics(user_id, days, limit, offset)
        return await self._request_post_json(endpoint, payload)

    async def get_message_credits(self, conversation_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_message_credits."""
        endpoint, payload = self._prepare_get_message_credits(conversation_id, user_id)
        return await self._request_post_json(endpoint, payload)

    async def get_usage_dashboard(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_usage_dashboard."""
        endpoint, payload = self._prepare_get_usage_dashboard()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def get_usage_history(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_usage_history."""
        endpoint, payload = self._prepare_get_usage_history(days)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def get_invoices(self, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_invoices."""
        endpoint, payload = self._prepare_get_invoices(limit)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def get_upcoming_invoice(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_upcoming_invoice."""
        endpoint, payload = self._prepare_get_upcoming_invoice()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def get_payment_methods(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_payment_methods."""
        endpoint, payload = self._prepare_get_payment_methods()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def upgrade_plan(
        self,
        new_plan: str,
        billing_cycle: str = "monthly",
        gateway: Optional[str] = None,
        billing_name: Optional[str] = None,
        billing_email: Optional[str] = None,
        promo_code: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.upgrade_plan."""
        endpoint, payload = self._prepare_upgrade_plan(
            new_plan, billing_cycle, gateway, billing_name, billing_email, promo_code,
            payment_method=payment_method,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def reauthorize_mandate(
        self,
        billing_name: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.reauthorize_mandate."""
        endpoint, payload = self._prepare_reauthorize_mandate(
            billing_name=billing_name,
            payment_method=payment_method,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def validate_promo_code(
        self,
        promo_code: str,
        plan: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async validate a promo code for this tenant."""
        endpoint, payload = self._prepare_validate_promo_code(promo_code, plan)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base, timeout=timeout)

    async def downgrade_to_free(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.downgrade_to_free."""
        endpoint, payload = self._prepare_downgrade_to_free()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def cancel_scheduled_change(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.cancel_scheduled_change."""
        endpoint, payload = self._prepare_cancel_scheduled_change()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def cancel_subscription(self, cancel_immediately: bool = False) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.cancel_subscription."""
        endpoint, payload = self._prepare_cancel_subscription(cancel_immediately)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def reactivate_subscription(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.reactivate_subscription."""
        endpoint, payload = self._prepare_reactivate_subscription()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def pause_subscription(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.pause_subscription."""
        endpoint, payload = self._prepare_pause_subscription()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def resume_subscription(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.resume_subscription."""
        endpoint, payload = self._prepare_resume_subscription()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def update_payment_method(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.update_payment_method."""
        endpoint, payload = self._prepare_update_payment_method()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def get_subscription_status(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_subscription_status."""
        endpoint, params = self._prepare_get_subscription_status()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def get_billing_history(self, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_billing_history."""
        endpoint, params = self._prepare_get_billing_history(limit)
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def get_billing_details(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_billing_details."""
        endpoint, params = self._prepare_get_billing_details()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def save_billing_details(self, **billing_fields: Any) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.save_billing_details."""
        endpoint, payload = self._prepare_save_billing_details(billing_fields)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    # =========================================================================
    # Prepaid Credit APIs
    # =========================================================================

    async def get_credit_balance(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_credit_balance."""
        endpoint, payload = self._prepare_get_credit_balance()
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def purchase_credits(
        self, credit_amount: int, gateway: str = None
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.purchase_credits."""
        endpoint, payload = self._prepare_purchase_credits(credit_amount, gateway)
        return await self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    async def get_expiring_credits(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_expiring_credits."""
        endpoint, params = self._prepare_get_expiring_credits()
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    async def get_consumption_breakdown(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_consumption_breakdown."""
        endpoint, params = self._prepare_get_consumption_breakdown(days)
        return await self._request_get(endpoint, params, api_base=self.billing_api_base)

    # =========================================================================
    # Conversation APIs
    # =========================================================================

    async def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_conversations."""
        endpoint, params = self._prepare_list_conversations(user_id, limit, offset, include_deleted, from_date, to_date)
        return await self._request_get(endpoint, params)

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_conversation."""
        endpoint, params = self._prepare_get_conversation(conversation_id)
        return await self._request_get(endpoint, params)

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_messages."""
        endpoint, params = self._prepare_get_messages(conversation_id, limit, offset, include_deleted)
        return await self._request_get(endpoint, params)

    async def create_message(
        self,
        conversation_id: str,
        message_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        tokens_used: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.create_message."""
        endpoint, payload = self._prepare_create_message(conversation_id, message_id, role, content, user_id, tokens_used, context)
        return await self._request_post_json(endpoint, payload)

    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.update_conversation."""
        endpoint, payload = self._prepare_update_conversation(conversation_id, title, user_id)
        return await self._request_post_json(endpoint, payload)

    async def delete_conversation(self, conversation_id: str, hard_delete: bool = False) -> Optional[Dict[str, Any]]:
        """Delete a conversation. Use hard_delete=True for permanent GDPR erasure."""
        endpoint, payload = self._prepare_delete_conversation(conversation_id, hard_delete)
        return await self._request_post_json(endpoint, payload)

    async def delete_message(self, conversation_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.delete_message."""
        endpoint, payload = self._prepare_delete_message(conversation_id, message_id)
        return await self._request_post_json(endpoint, payload)

    async def get_sync_stats(self) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_sync_stats."""
        endpoint, params = self._prepare_get_sync_stats()
        return await self._request_get(endpoint, params)

    # =========================================================================
    # Streaming Events APIs (Historical)
    # =========================================================================

    async def get_message_events(
        self,
        conversation_id: str,
        message_id: Optional[str] = None,
        event_types: Optional[list] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_message_events."""
        endpoint, params = self._prepare_get_message_events(conversation_id, message_id, event_types, limit, offset)
        return await self._request_get(endpoint, params)

    async def get_tool_execution_stats(
        self,
        conversation_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_tool_execution_stats."""
        endpoint, params = self._prepare_get_tool_execution_stats(conversation_id, from_date, to_date)
        return await self._request_get(endpoint, params)

    # =========================================================================
    # User & MCP Server APIs
    # =========================================================================

    async def register_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        locale: Optional[str] = None,
        timezone: Optional[str] = None,
        user_role: Optional[str] = None,
        email: Optional[str] = None,
        registered_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.register_user."""
        endpoint, params = self._prepare_register_user(
            user_id, display_name, custom_instructions,
            locale=locale, timezone=timezone, user_role=user_role, email=email,
            registered_by=registered_by,
        )
        return await self._request_post_form(endpoint, params)

    async def invite_user(
        self,
        user_id: str,
        user_role: Optional[str] = None,
        invited_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.invite_user."""
        endpoint, params = self._prepare_invite_user(user_id, user_role, invited_by)
        return await self._request_post_form(endpoint, params)

    async def revoke_invite(
        self,
        user_id: str,
        revoked_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.revoke_invite."""
        endpoint, params = self._prepare_revoke_invite(user_id, revoked_by)
        return await self._request_post_form(endpoint, params)

    async def resend_invite(
        self,
        user_id: str,
        resent_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.resend_invite."""
        endpoint, params = self._prepare_resend_invite(user_id, resent_by)
        return await self._request_post_form(endpoint, params)

    async def list_invites(self) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.list_invites."""
        endpoint, params = self._prepare_list_invites()
        return await self._request_get(endpoint, params)

    async def get_member_audit_log(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.get_member_audit_log."""
        endpoint, params = self._prepare_get_member_audit_log(limit, offset)
        return await self._request_get(endpoint, params)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_user."""
        endpoint, params = self._prepare_get_user(user_id)
        return await self._request_get(endpoint, params)

    async def get_user_auth_status(self, user_id: str) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.get_user_auth_status.

        See sync client docstring for the ``_ar_unreachable`` contract.
        """
        endpoint, params = self._prepare_get_user_auth_status(user_id)
        try:
            return await self._request_get(endpoint, params)
        except Exception as e:
            return {
                "_ar_unreachable": True,
                "error": str(e),
            }

    async def add_user_mcp_server(
        self,
        user_id: str,
        server_name: str,
        endpoint_url: str,
        transport_type: str = "SSE",
        auth_type: str = "OAuth",
        oauth_client_id: Optional[str] = None,
        oauth_client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_in: int = 3600,
        api_key: Optional[str] = None,
        api_key_header: str = "Authorization",
        allowed_tools: Optional[list] = None,
        blocked_tools: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.add_user_mcp_server."""
        endpoint, params = self._prepare_add_user_mcp_server(
            user_id, server_name, endpoint_url, transport_type, auth_type,
            oauth_client_id, oauth_client_secret, access_token, refresh_token,
            token_expires_in, api_key, api_key_header, allowed_tools, blocked_tools,
        )
        return await self._request_post_form(endpoint, params)

    async def get_user_mcp_servers(self, user_id: str) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.get_user_mcp_servers."""
        endpoint, params = self._prepare_get_user_mcp_servers(user_id)
        try:
            return await self._request_get(endpoint, params)
        except Exception as e:
            return {"user_id": user_id, "mcp_servers": [], "error": str(e)}

    async def update_mcp_server_tokens(
        self,
        user_id: str,
        server_name: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_in: int = 3600,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.update_mcp_server_tokens."""
        endpoint, params = self._prepare_update_mcp_server_tokens(user_id, server_name, access_token, refresh_token, token_expires_in)
        return await self._request_post_form(endpoint, params)

    async def remove_user_mcp_server(self, user_id: str, server_name: str) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.remove_user_mcp_server."""
        endpoint, params = self._prepare_remove_user_mcp_server(user_id, server_name)
        return await self._request_delete(endpoint, params)

    async def list_users(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_mcp_count: bool = True,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.list_users."""
        endpoint, params = self._prepare_list_users(status, limit, offset, include_mcp_count)
        return await self._request_get(endpoint, params)

    async def update_user(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        locale: Optional[str] = None,
        timezone: Optional[str] = None,
        user_role: Optional[str] = None,
        email: Optional[str] = None,
        job_title: Optional[str] = None,
        department: Optional[str] = None,
        about: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.update_user."""
        endpoint, params = self._prepare_update_user(
            user_id, display_name, custom_instructions,
            locale=locale, timezone=timezone, user_role=user_role, email=email,
            job_title=job_title, department=department, about=about,
        )
        return await self._request_post_form(endpoint, params)

    async def deregister_user(self, user_id: str) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.deregister_user."""
        endpoint, params = self._prepare_deregister_user(user_id)
        return await self._request_post_form(endpoint, params)

    async def get_user_limit_status(self) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.get_user_limit_status."""
        endpoint, params = self._prepare_get_user_limit_status()
        return await self._request_get(endpoint, params)

    async def suspend_user(self, user_id: str) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.suspend_user."""
        endpoint, params = self._prepare_suspend_user(user_id)
        return await self._request_post_form(endpoint, params)

    async def revoke_user(self, user_id: str) -> Dict[str, Any]:
        """Async version of AssistantRuntimeClient.revoke_user."""
        endpoint, params = self._prepare_revoke_user(user_id)
        return await self._request_post_form(endpoint, params)

    async def set_user_credit_limit(self, user_id: str, monthly_credit_limit: float = 0) -> Dict[str, Any]:
        """Async version: Set per-user monthly credit limit."""
        endpoint = "users.set_user_credit_limit"
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "monthly_credit_limit": str(monthly_credit_limit),
        }
        return await self._request_post_form(endpoint, params)

    async def get_my_credit_status(self, user_id: str) -> Dict[str, Any]:
        """Async version: Get credit usage status for a specific user."""
        endpoint = "users.get_my_credit_status"
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        return await self._request_get(endpoint, params)

    # =========================================================================
    # Workflow APIs
    # =========================================================================

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
        """Async version of AssistantRuntimeClient.create_workflow."""
        endpoint, payload = self._prepare_create_workflow(
            workflow_name, graph_json, description, default_model_id,
            default_user_id, error_strategy, timeout_seconds,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def get_workflow(
        self,
        name: Optional[str] = None,
        workflow_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_workflow."""
        endpoint, params = self._prepare_get_workflow(name, workflow_name)
        return await self._request_get(endpoint, params, api_base=self.workflows_api_base)

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
        """Async version of AssistantRuntimeClient.update_workflow."""
        endpoint, payload = self._prepare_update_workflow(
            name, graph_json, workflow_name, description, status,
            default_model_id, default_user_id, error_strategy,
            timeout_seconds, max_node_executions, max_retries,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def delete_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.delete_workflow."""
        endpoint, payload = self._prepare_delete_workflow(name)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def list_workflows(
        self,
        status: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_workflows."""
        endpoint, params = self._prepare_list_workflows(status, page, page_size)
        return await self._request_get(endpoint, params, api_base=self.workflows_api_base)

    async def execute_workflow(
        self,
        name: str,
        input_data: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.execute_workflow."""
        endpoint, payload = self._prepare_execute_workflow(name, input_data, user_id)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def execute_workflow_from_event(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        user_id: str,
        trigger_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.execute_workflow_from_event."""
        endpoint, payload = self._prepare_execute_workflow_from_event(
            workflow_name, input_data, user_id, trigger_id,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def cancel_workflow_run(self, run_name: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.cancel_workflow_run."""
        endpoint, payload = self._prepare_cancel_workflow_run(run_name)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def get_workflow_run(self, run_name: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_workflow_run."""
        endpoint, params = self._prepare_get_workflow_run(run_name)
        return await self._request_get(endpoint, params, api_base=self.workflows_api_base)

    async def list_workflow_runs(
        self,
        workflow_name: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.list_workflow_runs."""
        endpoint, params = self._prepare_list_workflow_runs(workflow_name, status, page, page_size)
        return await self._request_get(endpoint, params, api_base=self.workflows_api_base)

    async def get_workflow_audit_summary(
        self,
        workflow_id: str,
        window: str = "last_7_days",
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_workflow_audit_summary."""
        endpoint, params = self._prepare_get_workflow_audit_summary(workflow_id, window)
        return await self._request_get(endpoint, params, api_base=self.workflows_api_base)

    async def set_workflow_schedule(
        self,
        name: str,
        cron_expression: str,
        timezone: str = "UTC",
        enabled: bool = True,
        default_input: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.set_workflow_schedule."""
        endpoint, payload = self._prepare_set_workflow_schedule(name, cron_expression, timezone, enabled, default_input)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def validate_workflow_graph(self, graph_json: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.validate_workflow_graph."""
        endpoint, payload = self._prepare_validate_workflow_graph(graph_json)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def test_workflow_node(
        self,
        node_json: str,
        input_text: str = "Test input",
        default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.test_workflow_node."""
        endpoint, payload = self._prepare_test_workflow_node(node_json, input_text, default_model_id, default_user_id)
        return await self._request_post_json(endpoint, payload, timeout=120.0, api_base=self.workflows_api_base)

    async def resolve_workflow_tools(
        self,
        user_id: str,
        tool_directives: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.resolve_workflow_tools."""
        endpoint, payload = self._prepare_resolve_workflow_tools(user_id, tool_directives)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    async def run_workflow_node(
        self,
        name: str,
        node_id: str,
        input_text: str = "Test input",
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.run_workflow_node."""
        endpoint, payload = self._prepare_run_workflow_node(name, node_id, input_text, user_id)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base, timeout=120.0)

    # --- Workflow Templates ---

    async def export_workflow(
        self,
        name: str,
        template_name: Optional[str] = None,
        category: str = "General",
        save_as_template: bool = False,
        is_public: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.export_workflow."""
        endpoint, payload = self._prepare_export_workflow(name, template_name, category, save_as_template, is_public)
        return await self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    # `list_templates`, `get_template`, `import_template`, `update_template`,
    # and `delete_template` removed in chunk 4 — use the async marketplace
    # methods (`list_listings(listing_type="Workflow")`, `get_listing`,
    # `import_listing`, `update_listing`, `delete_listing`) instead.

    async def upload_listing_from_json(
        self,
        file_path: str,
        user_id: str,
        is_public: bool = False,
        is_published: bool = True,
        plan_tier: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async upload an ``ar_workflow_template_v1`` JSON file + create a listing."""
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "is_public": "1" if is_public else "0",
            "is_published": "1" if is_published else "0",
        }
        if plan_tier:
            payload["plan_tier"] = plan_tier
        url = f"{self.marketplace_api_base}.publishing.upload_listing_from_json"
        payload = self._with_site_url(payload)
        headers = self._get_headers(payload, for_query_string=False)
        timeout_val = timeout or self.timeout

        data = aiohttp.FormData()
        for k, v in payload.items():
            data.add_field(k, str(v))
        with open(file_path, "rb") as f:
            data.add_field(
                "file", f.read(),
                filename=os.path.basename(file_path),
                content_type="application/json",
            )

        async with self.session.post(
            url, data=data, headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout_val),
        ) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result.get("message", result)

    # `rate_template` removed in chunk 4 — use `rate_listing` instead.
    # `download_template` removed in chunk 5 — use `download_listing_as_json` instead.

    # --- GDPR / Privacy ---

    async def export_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Export all user data as structured JSON (GDPR Article 20)."""
        endpoint, payload = self._prepare_export_user_data(user_id)
        return await self._request_post_json(endpoint, payload)

    async def erase_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Permanently delete all user data (GDPR Article 17)."""
        endpoint, payload = self._prepare_erase_user_data(user_id)
        return await self._request_post_json(endpoint, payload)

    async def rectify_user_data(self, user_id: str, updates: dict) -> Optional[Dict[str, Any]]:
        """Update user's personal data (GDPR Article 16)."""
        endpoint, payload = self._prepare_rectify_user_data(user_id, updates)
        return await self._request_post_json(endpoint, payload)

    async def restrict_user_processing(self, user_id: str, restrict: bool = True) -> Optional[Dict[str, Any]]:
        """Restrict or unrestrict data processing for a user (GDPR Article 18)."""
        endpoint, payload = self._prepare_restrict_user_processing(user_id, restrict)
        return await self._request_post_json(endpoint, payload)

    async def update_user_consent(self, user_id: str, consent_type: str, granted: bool = True) -> Optional[Dict[str, Any]]:
        """Update user consent for a specific processing activity."""
        endpoint, payload = self._prepare_update_user_consent(user_id, consent_type, granted)
        return await self._request_post_json(endpoint, payload)

    async def create_ticket(self, user_id: str, subject: str, description: str,
                            category: Optional[str] = None,
                            conversation_id: Optional[str] = None,
                            environment: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Raise a support ticket. Returns {ticket_id, portal_link}."""
        endpoint, payload = self._prepare_create_ticket(
            user_id, subject, description, category, conversation_id, environment)
        return await self._request_post_json(endpoint, payload)

    async def submit_feedback(self, user_id: str, rating: Optional[int] = None,
                             comment: Optional[str] = None,
                             category: Optional[str] = None,
                             conversation_id: Optional[str] = None,
                             environment: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Submit product/service feedback. Returns {feedback_id}."""
        endpoint, payload = self._prepare_submit_feedback(
            user_id, rating, comment, category, conversation_id, environment)
        return await self._request_post_json(endpoint, payload)

    async def list_tickets(self, user_id: str, status: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """List the user's support tickets. Returns {tickets: [...]}."""
        endpoint, payload = self._prepare_list_tickets(user_id, status)
        return await self._request_post_json(endpoint, payload)

    async def get_ticket_thread(self, user_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a ticket's full conversation thread. Returns {ticket, messages: [...]}."""
        endpoint, payload = self._prepare_get_ticket_thread(user_id, ticket_id)
        return await self._request_post_json(endpoint, payload)

    async def reply_to_ticket(self, user_id: str, ticket_id: str, message: str) -> Optional[Dict[str, Any]]:
        """Post a reply to a ticket. Returns {message_id}."""
        endpoint, payload = self._prepare_reply_to_ticket(user_id, ticket_id, message)
        return await self._request_post_json(endpoint, payload)

    async def get_tenant_privacy_config(self) -> Optional[Dict[str, Any]]:
        """Get tenant's privacy policy configuration."""
        endpoint, payload = self._prepare_get_tenant_privacy_config()
        return await self._request_post_json(endpoint, payload)

    async def update_tenant_privacy_config(self, config: dict) -> Optional[Dict[str, Any]]:
        """Update tenant's privacy policy configuration."""
        endpoint, payload = self._prepare_update_tenant_privacy_config(config)
        return await self._request_post_json(endpoint, payload)

    # --- Heartbeat & Notifications ---

    async def heartbeat(
        self,
        faco_version: Optional[str] = None,
        fac_version: Optional[str] = None,
        frappe_version: Optional[str] = None,
        erpnext_version: Optional[str] = None,
        python_version: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async send version/health info and receive pending notifications."""
        endpoint, payload = self._prepare_heartbeat(
            faco_version, fac_version, frappe_version, erpnext_version, python_version
        )
        return await self._request_post_json(endpoint, payload, timeout=timeout)

    async def dismiss_notification(
        self,
        notification_id: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Async record that a user has dismissed a notification."""
        endpoint, payload = self._prepare_dismiss_notification(notification_id, user_id)
        return await self._request_post_json(endpoint, payload, timeout=timeout)

    # -------------------------------------------------------------------
    # Marketplace API — async, routes via marketplace_api_base
    # -------------------------------------------------------------------

    async def list_listings(
        self,
        listing_type: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        featured_only: bool = False,
        min_rating: Optional[float] = None,
        plan_tier: Optional[str] = None,
        sort_by: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
        user_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_list_listings(
            listing_type, category, search, featured_only, min_rating,
            plan_tier, sort_by, page, page_size, user_id,
        )
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base, timeout=timeout)

    async def get_listing(
        self, name: str, user_id: Optional[str] = None,
        include_source: bool = True,
    ) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_get_listing(name, user_id, include_source)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def import_listing(
        self,
        user_id: str,
        name: str,
        new_title: Optional[str] = None,
        variables: Optional[str] = None,
        default_model_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_import_listing(
            user_id, name, new_title, variables, default_model_id,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def update_listing(
        self,
        name: str,
        title: Optional[str] = None,
        short_description: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        icon: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_published: Optional[bool] = None,
        plan_tier: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_update_listing(
            name, title, short_description, description, category, tags,
            icon, is_public, is_published, plan_tier,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def delete_listing(self, name: str) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_delete_listing(name)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def rate_listing(
        self, user_id: str, listing: str, rating: int,
        review: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_rate_listing(user_id, listing, rating, review)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def report_listing(
        self, user_id: str, listing: str, reason: str,
        details: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_report_listing(user_id, listing, reason, details)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def list_pending_reviews(
        self, page: int = 0, page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_list_pending_reviews(page, page_size)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def approve_listing(
        self, listing: str, notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_approve_listing(listing, notes)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def reject_listing(
        self, listing: str, notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_reject_listing(listing, notes)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def get_creator_stats(
        self, user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_get_creator_stats(user_id)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def list_my_listings(
        self,
        user_id: Optional[str] = None,
        listing_type: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_list_my_listings(user_id, listing_type, page, page_size)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    # -------------------------------------------------------------------
    # Marketplace publishing + downloads + version checks (chunk 5)
    # -------------------------------------------------------------------

    async def publish_workflow(
        self,
        user_id: str,
        workflow_name: str,
        template_name: Optional[str] = None,
        category: str = "General",
        short_description: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[str] = None,
        is_public: bool = False,
        plan_tier: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        endpoint, payload = self._prepare_publish_workflow(
            user_id, workflow_name, template_name, category, short_description,
            description, tags, is_public, plan_tier,
        )
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def download_listing_as_json(self, name: str) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_download_listing_as_json(name)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def check_workflow_update(self, name: str) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_check_workflow_update(name)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def check_all_workflow_updates(self) -> Optional[Dict[str, Any]]:
        endpoint, params = self._prepare_check_all_workflow_updates()
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    # -------------------------------------------------------------------
    # Tenant Packs API — admin-grade pack management for the calling tenant
    # -------------------------------------------------------------------

    async def list_packs(self) -> Optional[Dict[str, Any]]:
        """Return every active pack with eligibility + enablement annotations."""
        endpoint, params = self._prepare_list_packs()
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def get_pack_contents(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Return the named prompts + skills of a pack the tenant owns."""
        endpoint, params = self._prepare_get_pack_contents(pack_id)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def set_industry(
        self,
        industry: Optional[str],
        auto_enable: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Set the calling tenant's industry and optionally auto-enable its pack."""
        endpoint, payload = self._prepare_set_industry(industry, auto_enable)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def set_pack_enabled(
        self,
        pack_id: str,
        enabled: bool,
        source: str = "User",
    ) -> Optional[Dict[str, Any]]:
        """Toggle a pack on or off for the calling tenant."""
        endpoint, payload = self._prepare_set_pack_enabled(pack_id, enabled, source)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    async def get_recommended_pack(
        self, user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return at most one pack to surface in the onboarding recommendation toast."""
        endpoint, params = self._prepare_get_recommended_pack(user_id)
        return await self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    async def dismiss_pack_recommendation(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mark the recommendation toast as dismissed for the given user."""
        endpoint, payload = self._prepare_dismiss_pack_recommendation(user_id)
        return await self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    # =========================================================================
    # HITL APIs
    # =========================================================================

    async def get_pending_interrupt(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Async version of AssistantRuntimeClient.get_pending_interrupt."""
        endpoint, params = self._prepare_get_pending_interrupt(session_id, user_id)
        return await self._request_get(endpoint, params, api_base=self.api_base)

    # =========================================================================
    # Voice API
    # =========================================================================

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        user_id: Optional[str] = None,
        duration_ms: int = 0,
        language: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Async transcribe an audio blob via AR's voice endpoint.

        Args:
            audio_bytes: Raw audio bytes.
            mime_type: MIME type (default: audio/webm).
            user_id: User identifier for per-user billing attribution.
            duration_ms: Client-reported recording length (advisory only;
                billing uses the provider's authoritative duration).
            language: ISO-639-1 hint ("en", "es"…). Strongly recommended —
                without it Whisper auto-detects and frequently hallucinates
                outro phrases ("Thank you for watching") on silent clips.

        Returns:
            {"text": str, "duration_seconds": float, "credits_consumed": float}
        """
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "duration_ms": duration_ms,
        }
        if user_id:
            params["user_id"] = user_id
        if language:
            params["language"] = language
        return await self._request_post_multipart(
            endpoint="transcribe_v1",
            params=params,
            file_field="audio",
            file_name="audio.webm",
            file_data=audio_bytes,
            content_type=mime_type,
            api_base=self.voice_api_base,
        )


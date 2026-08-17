# Assistant Runtime SDK - Synchronous Client
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Synchronous Assistant Runtime client using the requests library.

For async support, use AsyncAssistantRuntimeClient from assistant_runtime_sdk.async_client.
"""

import json
import os
from typing import Generator, List, Optional, Dict, Any

import requests

from .base import BaseAssistantRuntimeClient
from .exceptions import (
    ARAPIError,
    ARAuthenticationError,
    ARTimeoutError,
    ARConnectionError,
)


class AssistantRuntimeClient(BaseAssistantRuntimeClient):
    """
    Synchronous Assistant Runtime client using the requests library.

    All methods are blocking and return results directly.

    Example:
        >>> from assistant_runtime_sdk import AssistantRuntimeClient
        >>> client = AssistantRuntimeClient("tenant-id", "secret", "https://ar.example.com")
        >>> models = client.list_available_models()
        >>> for event in client.stream_chat("session-1", "Hello", user_id="user@example.com"):
        ...     print(event)
    """

    # =========================================================================
    # Internal Request Methods
    # =========================================================================

    def _extract_error_message(self, response) -> Optional[str]:
        """Extract a human-readable error message from a Frappe HTTP error response."""
        try:
            data = response.json()
        except Exception:
            return None
        return self._extract_error_from_data(data)

    def _extract_error_payload(self, response) -> tuple:
        """Return (message, raw_body_dict) so callers can attach both to
        ARAPIError. The raw body is what lets FACO read non-standard keys
        like ``tenant_owner_user_id`` that AR sets on ``frappe.local.response``.
        """
        try:
            data = response.json()
        except Exception:
            return None, None
        return self._extract_error_from_data(data), data

    def _request_get(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated GET request with query parameters."""
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        params = self._with_site_url(params)
        headers = self._get_headers(params, for_query_string=True)
        timeout = timeout or self.timeout

        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json().get("message", response.json())
        except requests.exceptions.Timeout as e:
            self._log_error(f"GET {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.ConnectionError as e:
            self._log_error(f"GET {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except requests.exceptions.HTTPError as e:
            self._log_error(f"GET {endpoint} HTTP error: {e}")
            status_code = e.response.status_code if e.response is not None else None
            msg, body = (
                self._extract_error_payload(e.response) if e.response is not None else (None, None)
            )
            if status_code == 401:
                raise ARAuthenticationError(msg or "Authentication failed") from e
            raise ARAPIError(msg or str(e), status_code=status_code, response_data=body) from e
        except requests.exceptions.RequestException as e:
            self._log_error(f"GET {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    def _request_get_raw(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> tuple:
        """Make authenticated GET request expecting raw binary response.

        Returns:
            (content_bytes, content_type, filename) tuple
        """
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        params = self._with_site_url(params)
        headers = self._get_headers(params, for_query_string=True)
        timeout = timeout or self.timeout

        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "application/octet-stream")
            # Extract filename from Content-Disposition header if available
            filename = ""
            cd = response.headers.get("Content-Disposition", "")
            if "filename=" in cd:
                parts = cd.split("filename=")
                if len(parts) > 1:
                    filename = parts[1].strip().strip('"')

            return response.content, content_type, filename
        except requests.exceptions.Timeout as e:
            self._log_error(f"GET raw {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.ConnectionError as e:
            self._log_error(f"GET raw {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except requests.exceptions.HTTPError as e:
            self._log_error(f"GET raw {endpoint} HTTP error: {e}")
            status_code = e.response.status_code if e.response is not None else None
            msg, body = (
                self._extract_error_payload(e.response) if e.response is not None else (None, None)
            )
            if status_code == 401:
                raise ARAuthenticationError(msg or "Authentication failed") from e
            raise ARAPIError(msg or str(e), status_code=status_code, response_data=body) from e
        except requests.exceptions.RequestException as e:
            self._log_error(f"GET raw {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    def _request_post_json(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated POST request with JSON body."""
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        payload = self._with_site_url(payload)
        headers = {
            **self._get_headers(payload, for_query_string=False),
            "Content-Type": "application/json",
        }
        timeout = timeout or self.timeout

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json().get("message", response.json())
        except requests.exceptions.Timeout as e:
            self._log_error(f"POST {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.ConnectionError as e:
            self._log_error(f"POST {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except requests.exceptions.HTTPError as e:
            self._log_error(f"POST {endpoint} HTTP error: {e}")
            status_code = e.response.status_code if e.response is not None else None
            msg, body = (
                self._extract_error_payload(e.response) if e.response is not None else (None, None)
            )
            if status_code == 401:
                raise ARAuthenticationError(msg or "Authentication failed") from e
            raise ARAPIError(msg or str(e), status_code=status_code, response_data=body) from e
        except requests.exceptions.RequestException as e:
            self._log_error(f"POST {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    def _request_post_form(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated POST request with form-urlencoded body."""
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        params = self._with_site_url(params)
        headers = {
            **self._get_headers(params, for_query_string=True),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        timeout = timeout or self.timeout

        try:
            response = requests.post(url, data=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json().get("message", response.json())
        except requests.exceptions.Timeout as e:
            self._log_error(f"POST form {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.ConnectionError as e:
            self._log_error(f"POST form {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except requests.exceptions.HTTPError as e:
            self._log_error(f"POST form {endpoint} HTTP error: {e}")
            status_code = e.response.status_code if e.response is not None else None
            msg, body = (
                self._extract_error_payload(e.response) if e.response is not None else (None, None)
            )
            if status_code == 401:
                raise ARAuthenticationError(msg or "Authentication failed") from e
            raise ARAPIError(msg or str(e), status_code=status_code, response_data=body) from e
        except requests.exceptions.RequestException as e:
            self._log_error(f"POST form {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    def _request_post_multipart(
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
        """Make authenticated POST request with multipart form data including a file."""
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        # Sign only non-file form fields — Frappe's form_dict excludes file parts
        params = self._with_site_url(params)
        headers = self._get_headers(params, for_query_string=True)
        # Do NOT set Content-Type — requests sets multipart boundary automatically
        timeout = timeout or self.timeout

        try:
            response = requests.post(
                url,
                data=params,
                files={file_field: (file_name, file_data, content_type)},
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json().get("message", response.json())
        except requests.exceptions.Timeout as e:
            self._log_error(f"POST multipart {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.ConnectionError as e:
            self._log_error(f"POST multipart {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except requests.exceptions.HTTPError as e:
            self._log_error(f"POST multipart {endpoint} HTTP error: {e}")
            status_code = e.response.status_code if e.response is not None else None
            msg, body = (
                self._extract_error_payload(e.response) if e.response is not None else (None, None)
            )
            if status_code == 401:
                raise ARAuthenticationError(msg or "Authentication failed") from e
            raise ARAPIError(msg or str(e), status_code=status_code, response_data=body) from e
        except requests.exceptions.RequestException as e:
            self._log_error(f"POST multipart {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    def _request_delete(
        self,
        endpoint: str,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
        api_base: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated DELETE request with query parameters."""
        url = f"{api_base}.{endpoint}" if api_base else self._build_endpoint_url(endpoint)
        params = self._with_site_url(params)
        headers = self._get_headers(params, for_query_string=True)
        timeout = timeout or self.timeout

        try:
            response = requests.delete(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json().get("message", response.json())
        except requests.exceptions.Timeout as e:
            self._log_error(f"DELETE {endpoint} timeout: {e}")
            raise ARTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.ConnectionError as e:
            self._log_error(f"DELETE {endpoint} connection error: {e}")
            raise ARConnectionError(f"Failed to connect to {endpoint}") from e
        except requests.exceptions.HTTPError as e:
            self._log_error(f"DELETE {endpoint} HTTP error: {e}")
            status_code = e.response.status_code if e.response is not None else None
            msg, body = (
                self._extract_error_payload(e.response) if e.response is not None else (None, None)
            )
            if status_code == 401:
                raise ARAuthenticationError(msg or "Authentication failed") from e
            raise ARAPIError(msg or str(e), status_code=status_code, response_data=body) from e
        except requests.exceptions.RequestException as e:
            self._log_error(f"DELETE {endpoint} error: {e}")
            raise ARAPIError(str(e)) from e

    # =========================================================================
    # Streaming API
    # =========================================================================

    def stream_chat(
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
        continue_from_message_id: Optional[str] = None,
        *,
        web_search: Optional[bool] = None,
        thinking_enabled: Optional[bool] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream chat response from Assistant Runtime.

        Connects to Assistant Runtime's SSE endpoint and yields parsed events.
        Also handles HITL resume when interrupt_response is provided.

        Args:
            session_id: Conversation session identifier
            message: User's message to send (optional when interrupt_response is provided)
            user_id: User identifier (required)
            context: Optional page context (doctype, document info, etc.)
            model_id: Optional model ID to use (use "auto" for auto-selection)
            attachments: Optional list of attachments (images/documents)
                Each attachment: {
                    "type": "image" | "document",
                    "format": "png" | "jpeg" | "gif" | "webp" | "pdf" | "txt",
                    "data": "<base64-encoded-data>",
                    "name": "optional-filename.png",  # Optional
                    "file_url": "/files/..."  # Optional, for storage reference
                }
            system_prompt_addendum: Optional per-request addition to the system prompt
            interrupt_response: Optional HITL resume responses. Each item:
                {"interruptId": str, "response": "approve"|"rejected"|"trust"|"session"}
            message_id: Optional message ID to reuse on HITL resume
            session_state: Optional client-held signed session blob (zero-retention).
                On ``stream_complete``, ``event['session_state']`` is the updated
                signed blob — store it and pass it as ``session_state`` on the next turn.
            continue_from_message_id: Optional message ID to continue a previous
                truncated response from
            web_search: Optional explicit web-search toggle for this turn
            thinking_enabled: Optional explicit extended-thinking toggle for this turn

        Yields:
            Parsed SSE events with structure:
            {
                "event": "stream_start|stream_chunk|stream_complete|stream_error|...",
                "data": {...event-specific data...}
            }

        Example:
            >>> for event in client.stream_chat("session-1", "Hello", "user@example.com"):
            ...     if event["event"] == "stream_chunk":
            ...         print(event["data"].get("content", ""), end="")

            # Resume from HITL interrupt
            >>> for event in client.stream_chat(
            ...     "session-1", None, "user@example.com",
            ...     interrupt_response=[{"interruptId": "abc", "response": "approve"}]
            ... ):
            ...     print(event)
        """
        payload = self._prepare_stream_payload(
            session_id, message, user_id, context, model_id, attachments,
            system_prompt_addendum, client_type=client_type,
            interrupt_response=interrupt_response,
            message_id=message_id,
            session_state=session_state,
            continue_from_message_id=continue_from_message_id,
            web_search=web_search,
            thinking_enabled=thinking_enabled,
        )
        url = self._build_endpoint_url("streaming.stream_chat")
        payload = self._with_site_url(payload)
        headers = self._get_stream_headers(payload, for_json_body=True)

        try:
            with requests.post(
                url,
                json=payload,
                headers=headers,
                stream=True,
                timeout=(self.STREAM_CONNECT_TIMEOUT, self.STREAM_READ_TIMEOUT),
            ) as response:
                response.raise_for_status()

                current_event = None

                for line in response.iter_lines(decode_unicode=True):
                    if line is None:
                        continue

                    parsed = self._parse_sse_line(line)
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

        except requests.exceptions.Timeout as e:
            yield {
                "event": "stream_error",
                "data": {
                    "error": "The assistant took too long to respond. Please try again.",
                    "error_code": "TIMEOUT",
                    "_detail": str(e),
                },
            }
        except requests.exceptions.ChunkedEncodingError as e:
            # Connection dropped mid-stream — typically a proxy idle timeout,
            # worker restart, or OOM kill on the server side. ChunkedEncodingError
            # is a subclass of ConnectionError, so it must be caught first.
            yield {
                "event": "stream_error",
                "data": {
                    "error": "Connection to the assistant was interrupted. Please try again.",
                    "error_code": "CONNECTION_INTERRUPTED",
                    "_detail": str(e),
                },
            }
        except requests.exceptions.ConnectionError as e:
            yield {
                "event": "stream_error",
                "data": {
                    "error": "Couldn't reach the assistant service. Please check your connection and try again.",
                    "error_code": "CONNECTION_ERROR",
                    "_detail": str(e),
                },
            }
        except requests.exceptions.RequestException as e:
            yield {
                "event": "stream_error",
                "data": {
                    "error": "Something went wrong with your request. Please try again.",
                    "error_code": "REQUEST_ERROR",
                    "_detail": str(e),
                },
            }

    # =========================================================================
    # Tenant APIs
    # =========================================================================

    def get_tenant_info(self) -> Optional[Dict[str, Any]]:
        """Get tenant information including subscription status."""
        endpoint, params = self._prepare_get_tenant_info()
        return self._request_get(endpoint, params)

    def accept_terms(self, terms_version: str, accepted_by: str) -> Dict[str, Any]:
        """Accept or re-accept Terms and Conditions for this tenant."""
        endpoint, payload = self._prepare_accept_terms(terms_version, accepted_by)
        return self._request_post_json(endpoint, payload)

    def get_terms_status(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Report whether this tenant must (re-)accept Terms and Conditions.

        Read-only — safe to call at boot to decide whether to render the
        acceptance surface before a gated feature fails.
        """
        endpoint, params = self._prepare_get_terms_status()
        return self._request_get(endpoint, params, timeout=timeout)

    # =========================================================================
    # Model APIs
    # =========================================================================

    def list_available_models(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        List available AI models for this tenant's subscription tier.

        Args:
            timeout: Optional request timeout in seconds (overrides client default)

        Returns:
            Dict with models list, auto_mode info, and default model
        """
        endpoint, params = self._prepare_list_available_models()
        return self._request_get(endpoint, params, timeout=timeout)

    def get_available_models(self) -> Optional[Dict[str, Any]]:
        """Get available AI models (deprecated). Use list_available_models() instead."""
        endpoint, params = self._prepare_get_available_models()
        return self._request_get(endpoint, params)

    def set_preferred_model(self, model_id: str) -> bool:
        """Set the preferred AI model for this tenant."""
        endpoint, payload = self._prepare_set_preferred_model(model_id)
        result = self._request_post_json(endpoint, payload)
        return result.get("success", False) if result else False

    # =========================================================================
    # Origin Binding APIs (Phase 2)
    # =========================================================================

    def request_rebind(self, new_site_url: str) -> Dict[str, Any]:
        """Initiate a tenant rebind. Returns {"rebind_token": str, "expires_at": str}.

        When the site URL of an installation changes, call this to begin the
        rebind flow. AR sends a confirmation email to the tenant owner. After
        the owner clicks the link, call the module-level helper
        ``get_rotated_secret(ar_url, rebind_token)`` with the token from the
        link to retrieve the new ``tenant_secret``.
        """
        return self._request_post_json(
            "request_rebind",
            {"tenant_id": self.tenant_id, "new_site_url": new_site_url},
        )

    def claim_tenant_email(self, owner_email: str) -> Dict[str, Any]:
        """Bootstrap an owner_email on a legacy tenant (one without a verified
        owner_email on file). AR sends a verification email; the email is only
        persisted to the tenant record after the owner clicks the link.
        """
        return self._request_post_json(
            "claim_tenant_email",
            {"tenant_id": self.tenant_id, "owner_email": owner_email},
        )

    def diagnose_registration(self) -> Dict[str, Any]:
        """Diagnose registration issues. Returns one of:

        - ``{"status": "ok", "bound_host": ..., "last_verification": ...}``
        - ``{"status": "origin_mismatch", "bound_host": ..., "claimed_host": ...,
          "remediation": "rebind", "rebind_url": ...}``
        """
        return self._request_post_json(
            "diagnose_registration",
            {"tenant_id": self.tenant_id},
        )

    # =========================================================================
    # Prompt APIs
    # =========================================================================

    def list_prompts(self, user_id: str, cursor: Optional[str] = None, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """List available prompt templates from user's configured MCP servers."""
        endpoint, params = self._prepare_list_prompts(user_id, cursor)
        return self._request_get(endpoint, params, timeout=timeout)

    def get_prompt(
        self,
        prompt_name: str,
        user_id: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific prompt rendered with provided arguments."""
        endpoint, payload = self._prepare_get_prompt(prompt_name, user_id, arguments)
        return self._request_post_json(endpoint, payload)

    # =========================================================================
    # Suggestion APIs
    # =========================================================================

    def get_suggestions(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 8,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get personalized prompt suggestions based on user conversation history.

        Uses frequency analysis of past conversations, frequently-used DocTypes,
        and extracted memories to surface relevant suggestions. No LLM cost.

        Args:
            user_id: User identifier (required)
            context: Optional page context {"type": "Form", "doctype": "Sales Invoice"}
            limit: Max suggestions to return (default 8, max 20)
            timeout: Optional request timeout in seconds (overrides client default)

        Returns:
            Dict with suggestions, history flag, and stats:
            {
                "suggestions": [
                    {"text": str, "source": "history"|"memory"|"doctype", "score": float}
                ],
                "has_history": bool,
                "stats": {"total_conversations": int, "top_doctypes": [str]}
            }
        """
        endpoint, params = self._prepare_get_suggestions(user_id, context, limit)
        return self._request_get(endpoint, params, timeout=timeout)

    def generate_curated_suggestions(
        self,
        user_id: str,
        signals: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate LLM-curated welcome suggestions from usage signals.

        Costs one Economy-tier completion on AR (rate-limited server-side to
        one generation per user per 20h). Returns
        {"suggestions": [...], "generated_at": ...} or an empty-suggestions
        dict with a reason/rate_limited flag.
        """
        endpoint, payload = self._prepare_generate_curated_suggestions(user_id, signals)
        return self._request_post_json(endpoint, payload, timeout=timeout)

    # =========================================================================
    # Onboarding APIs
    # =========================================================================
    # These methods route through memory_api_base -> assistant_runtime_memory.api

    def get_onboarding_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if a user has completed onboarding.

        Args:
            user_id: User identifier (required)

        Returns:
            {"onboarding_complete": bool, "has_conversations": bool}
        """
        endpoint, params = self._prepare_get_onboarding_status(user_id)
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    def complete_onboarding(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Mark onboarding complete for a user.

        Memory is seeded from real chat turns via turn-end extraction, so this
        only flips the completion flag and refreshes personalized suggestions.

        Args:
            user_id: User identifier (required)

        Returns:
            {"success": bool}
        """
        endpoint, payload = self._prepare_complete_onboarding(user_id)
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    # =========================================================================
    # Document APIs (RAG)
    # =========================================================================
    # These methods route through memory_api_base -> assistant_runtime_memory.api

    def upload_document(
        self,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
        visibility: Optional[str] = None,
        shared_with: Optional[List[str]] = None,
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
            user_id: Uploader's user identifier. Enables ownership tracking.
            visibility: Document visibility (public, private, shared). Defaults to
                tenant configuration if omitted.
            shared_with: List of user IDs to share with. Required when
                visibility is "shared".

        Returns:
            {"status": "queued", "document_id": str, "file_name": str,
             "file_size_mb": float, "visibility": str, "message": str}
        """
        endpoint, params, f_field, f_name, f_data, c_type = self._prepare_upload_document(
            file_path, file_data, file_name, content_type,
            user_id=user_id, visibility=visibility, shared_with=shared_with,
        )
        return self._request_post_multipart(
            endpoint, params=params, file_field=f_field,
            file_name=f_name, file_data=f_data, content_type=c_type,
            timeout=120.0, api_base=self.memory_api_base,
        )

    def list_documents(
        self, limit: int = 50, offset: int = 0, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        List RAG documents for this tenant.

        When user_id is provided, returns documents visible to that user
        (public + user's private + shared). Without user_id, returns only
        public documents.

        Args:
            limit: Maximum number of documents to return (default 50).
            offset: Pagination offset (default 0).
            user_id: User performing the query. Enables visibility filtering.

        Returns:
            {"documents": [...], "pagination": {...}, "storage": {...}}
        """
        endpoint, params = self._prepare_list_documents(limit, offset, user_id=user_id)
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific RAG document.

        Args:
            document_id: The document identifier.

        Returns:
            Document details including embedding_status, total_chunks,
            visibility, uploaded_by, and processing_error (if Failed).
        """
        endpoint, params = self._prepare_get_document(document_id)
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    def list_chunks(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        List stored chunks for a document (read-only chunk browser).

        Visibility is enforced backend-side using user_id (private/shared
        documents require the requesting user to own or be granted access).

        Args:
            document_id: Document whose chunks to list.
            user_id: Requesting user. Enables visibility enforcement.
            search: Optional case-insensitive substring filter on chunk text.
            limit: Page size (default 50).
            offset: Pagination offset (default 0).

        Returns:
            {"chunks": [...], "total": int, "pagination": {...}}
        """
        endpoint, params = self._prepare_list_chunks(
            document_id, user_id=user_id, search=search, limit=limit, offset=offset
        )
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    def get_document_content(
        self, document_id: str, user_id: Optional[str] = None
    ) -> tuple:
        """
        Download raw file content for a RAG document.

        Enforces visibility rules on the AR backend. Returns the file bytes
        along with content type and filename for serving to the browser.

        Args:
            document_id: The document identifier.
            user_id: Requesting user for visibility checks.

        Returns:
            (file_bytes, content_type, filename) tuple
        """
        endpoint, params = self._prepare_get_document_content(document_id, user_id=user_id)
        return self._request_get_raw(endpoint, params, api_base=self.memory_api_base)

    def delete_document(
        self, document_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Delete a RAG document and remove its embeddings.

        Performs a soft delete -- the document is marked as deleted and its
        vector embeddings are removed from the search index. For private and
        shared documents, only the owner (uploaded_by) can delete.

        Args:
            document_id: The document identifier to delete.
            user_id: User requesting deletion. Used for ownership verification.

        Returns:
            {"status": "deleted", "document_id": str, "file_size_mb": float}
        """
        endpoint, payload = self._prepare_delete_document(document_id, user_id=user_id)
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    def update_document_access(
        self,
        document_id: str,
        user_id: str,
        visibility: Optional[str] = None,
        add_users: Optional[List[str]] = None,
        remove_users: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update document visibility and sharing.

        Only the document owner (uploaded_by) can manage access.

        Args:
            document_id: The document identifier.
            user_id: User requesting the change. Must match uploaded_by.
            visibility: New visibility (public, private, shared).
            add_users: User IDs to grant access (for shared visibility).
            remove_users: User IDs to revoke access.

        Returns:
            {"status": "updated", "document_id": str, "visibility": str,
             "shared_with": [str]}
        """
        endpoint, payload = self._prepare_update_document_access(
            document_id, user_id,
            visibility=visibility, add_users=add_users, remove_users=remove_users,
        )
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    def get_storage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get storage quota and usage information for this tenant's RAG documents.

        Returns:
            {"quota_mb": float, "used_mb": float, "available_mb": float,
             "usage_percentage": float, "document_count": int}
        """
        endpoint, params = self._prepare_get_storage_info()
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    # =========================================================================
    # Memory APIs (User Memory Viewer)
    # =========================================================================
    # These methods route through memory_api_base -> assistant_runtime_memory.api

    def list_memories(
        self,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        List stored memories for this tenant.

        Args:
            user_id: Optional user filter.
            memory_type: Optional type filter (preference, summary, fact).
            limit: Page size (default 50).
            offset: Pagination offset (default 0).

        Returns:
            {"memories": [...], "pagination": {...}}
        """
        endpoint, params = self._prepare_list_memories(user_id, memory_type, limit, offset)
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    def delete_memory(self, user_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete a single memory.

        Args:
            user_id: User who owns the memory.
            memory_id: The memory identifier to delete.

        Returns:
            {"status": "deleted", "memory_id": str}
        """
        endpoint, payload = self._prepare_delete_memory(user_id, memory_id)
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    def delete_all_memories(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete all memories for a user.

        Args:
            user_id: User whose memories to delete.

        Returns:
            {"status": "deleted", "count": int}
        """
        endpoint, payload = self._prepare_delete_all_memories(user_id)
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    def update_memory(self, user_id: str, memory_id: str, content: str) -> Optional[Dict[str, Any]]:
        """
        Update a memory's content.

        Preserves the memory_id. Re-embeds the new content and updates
        both Redis and the MariaDB audit record.

        Args:
            user_id: User who owns the memory.
            memory_id: The memory identifier to update.
            content: New memory text.

        Returns:
            {"status": "updated", "memory_id": str}
        """
        endpoint, payload = self._prepare_update_memory(user_id, memory_id, content)
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    def get_memory_stats(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get memory statistics.

        Args:
            user_id: Optional user filter.

        Returns:
            {"total": int, "by_type": {...}, "total_accesses": int}
        """
        endpoint, params = self._prepare_get_memory_stats(user_id)
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    def get_memory_summary(
        self,
        user_id: str,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI-generated narrative summary of user's memories.

        Args:
            user_id: User whose memory summary to generate.
            force: Bypass cache and regenerate.
            timeout: Optional request timeout in seconds.

        Returns:
            {"summary": str | None, "cached": bool, "reason": str | None}
        """
        endpoint, params = self._prepare_get_memory_summary(user_id, force)
        return self._request_get(endpoint, params, timeout=timeout, api_base=self.memory_api_base)

    # =========================================================================
    # Shared Knowledge APIs
    # These methods route through memory_api_base -> assistant_runtime_memory.api
    # =========================================================================

    def get_shared_knowledge(self) -> Optional[Dict[str, Any]]:
        """
        Get shared knowledge document for the tenant.

        Returns:
            {"content": str, "embedding_status": str, "total_chunks": int, ...}
        """
        endpoint, params = self._prepare_get_shared_knowledge()
        return self._request_get(endpoint, params, api_base=self.memory_api_base)

    def update_shared_knowledge(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Update shared knowledge content. Triggers re-embedding via RAG pipeline.

        Args:
            content: New markdown content.

        Returns:
            {"status": "updated", "embedding_status": str}
        """
        endpoint, payload = self._prepare_update_shared_knowledge(content)
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    def share_memory_to_knowledge(self, user_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Share a personal memory to the shared knowledge document.

        Appends the memory content with attribution, then re-embeds.

        Args:
            user_id: User sharing the memory.
            memory_id: AR Memory ID to share.

        Returns:
            {"status": "shared", "embedding_status": str}
        """
        endpoint, payload = self._prepare_share_memory_to_knowledge(user_id, memory_id)
        return self._request_post_json(endpoint, payload, api_base=self.memory_api_base)

    # =========================================================================
    # Resource APIs (Skills/Documentation)
    # =========================================================================

    def list_resources(
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
            >>> resources = client.list_resources("user@example.com")
            >>> for r in resources.get("resources", []):
            ...     print(f"{r['name']}: {r['uri']}")
        """
        params = self._prepare_resource_params(user_id, server=server)
        return self._request_get("resources.list_resources", params)

    def read_resource(self, user_id: str, uri: str) -> Optional[Dict[str, Any]]:
        """
        Read a specific resource's content from user's MCP server.

        Args:
            user_id: User identifier (required)
            uri: Resource URI to read

        Returns:
            Dict with resource content

        Example:
            >>> result = client.read_resource("user@example.com", "fac://tools/create_document")
            >>> print(result.get("content"))
        """
        params = self._prepare_resource_params(user_id, uri=uri)
        return self._request_post_json("resources.read_resource", params)

    # =========================================================================
    # Tool APIs
    # =========================================================================

    def list_tools(
        self,
        user_id: str,
        server: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        List available tools from user's configured MCP servers.

        Args:
            user_id: User identifier (required)
            server: Optional - filter to specific MCP server

        Returns:
            Dict with tools list, servers_queried, and any errors

        Example:
            >>> tools = client.list_tools("user@example.com")
            >>> for t in tools.get("tools", []):
            ...     print(f"{t['name']}: {t['description']}")
        """
        endpoint, params = self._prepare_list_tools(user_id, server)
        return self._request_get(endpoint, params)

    # =========================================================================
    # Tool Preference APIs (per-user approval settings)
    # =========================================================================

    def list_tool_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        List persistent tool approval preferences for a user.

        Args:
            user_id: User identifier

        Returns:
            {"preferences": {tool_name: "always_allow" | "block", ...}}
        """
        endpoint, params = self._prepare_list_tool_preferences(user_id)
        return self._request_get(endpoint, params)

    def set_tool_preference(
        self,
        user_id: str,
        tool_name: str,
        preference: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Set a user's approval preference for one tool.

        Args:
            user_id: User identifier
            tool_name: MCP tool name (e.g. "create_document")
            preference: One of "ask", "always_allow", "block"

        Returns:
            {"success": True, "tool_name": ..., "preference": ...}
        """
        endpoint, payload = self._prepare_set_tool_preference(user_id, tool_name, preference)
        return self._request_post_json(endpoint, payload)

    # =========================================================================
    # Billing & Subscription APIs
    # =========================================================================
    # These methods route through billing_api_base -> assistant_runtime_payments.api

    def check_billing_available(self) -> bool:
        """
        Probe the server to check if billing features are available.

        Calls ``get_capabilities`` on the core API and checks the
        ``billing_enabled`` flag. The result is cached in ``_billing_available``
        so subsequent billing method calls can fail fast via ``_require_billing()``.

        Returns:
            True if billing is available, False otherwise.
        """
        try:
            url = f"{self.api_base}.get_capabilities"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get("message", response.json())
            self._billing_available = data.get("billing_enabled", False)
        except requests.exceptions.RequestException:
            self._billing_available = False
        return self._billing_available

    def get_plan_comparison(self) -> Optional[Dict[str, Any]]:
        """Get comparison of all available subscription plans (no auth required)."""
        self._require_billing()
        url = self._build_billing_endpoint_url("get_plan_comparison")
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("message", response.json())
        except requests.exceptions.RequestException as e:
            self._log_error(f"get_plan_comparison error: {e}")
            return None

    def get_recommended_gateway(self) -> Optional[Dict[str, Any]]:
        """Get the recommended payment gateway for this tenant."""
        endpoint, params = self._prepare_get_recommended_gateway()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def get_available_gateways(self) -> Optional[Dict[str, Any]]:
        """
        Get all enabled payment gateways with pricing for each plan.

        Returns:
            Dict with gateways list, recommended_gateway, and tenant_country.
        """
        endpoint, params = self._prepare_get_available_gateways()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def preview_plan_pricing(
        self, plan: str, billing_cycle: str = "monthly",
    ) -> Optional[Dict[str, Any]]:
        """Return the tax-inclusive pricing breakdown for a plan.

        Use this to show the user "subtotal + GST = total due today"
        before opening the Razorpay widget. No DB writes, no Razorpay
        calls — just runs the tax pipeline for the current tenant.

        Returns:
            {base, tax, total, currency, tax_rate_percent, components}.
        """
        endpoint, params = self._prepare_preview_plan_pricing(plan, billing_cycle)
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def add_user_seat(self) -> Optional[Dict[str, Any]]:
        """Add one seat to the per-user subscription and charge prorated amount."""
        endpoint, params = self._prepare_add_user_seat()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def remove_user_seat(self) -> Optional[Dict[str, Any]]:
        """Remove one seat. No refund; next renewal reflects lower count."""
        endpoint, params = self._prepare_remove_user_seat()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def preview_seat_charge(self) -> Optional[Dict[str, Any]]:
        """Preview the prorated cost of adding one seat."""
        endpoint, params = self._prepare_preview_seat_charge()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def download_invoice_pdf(self, ar_invoice_name: str) -> tuple:
        """Download the GST invoice PDF for an AR Invoice.

        Returns the raw bytes so callers can stream to a file / HTTP
        response / bucket without buffering through JSON.

        Returns:
            (content_bytes, content_type, filename) tuple. Backend
            sets `filename = "{ar_invoice_name}.pdf"` and streams
            `application/pdf`.
        """
        endpoint, params = self._prepare_download_invoice_pdf(ar_invoice_name)
        return self._request_get_raw(
            endpoint, params, api_base=self.billing_api_base,
        )

    def initiate_checkout(
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
            gateway: "stripe" or "razorpay" (optional)
            billing_name: Customer/company name for billing
            billing_email: Email for billing notifications

        Returns:
            Dict with checkout_url, session_id, and gateway used.
        """
        endpoint, payload = self._prepare_initiate_checkout(plan, billing_cycle, gateway, billing_name, billing_email)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def verify_checkout(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Verify payment completion after checkout."""
        endpoint, payload = self._prepare_verify_checkout(session_id)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def verify_razorpay_payment(
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
            {"success": True, "message": str, "subscription_status": str, "plan": str, "credit_quota": int}
        """
        endpoint, payload = self._prepare_verify_razorpay_payment(razorpay_payment_id, razorpay_subscription_id, razorpay_signature)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def verify_razorpay_credit_payment(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Verify Razorpay credit (token top-up) payment from embedded widget.

        Args:
            razorpay_payment_id: Payment ID from Razorpay widget response
            razorpay_order_id: Order ID from Razorpay widget response
            razorpay_signature: Signature from Razorpay widget response

        Returns:
            {"success": True, "balance": int, "tokens_added": int, "message": str}
        """
        endpoint, payload = self._prepare_verify_razorpay_credit_payment(razorpay_payment_id, razorpay_order_id, razorpay_signature)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def verify_seat_payment(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """Verify a Razorpay seat-purchase payment from the embedded widget.

        Args:
            razorpay_payment_id: Payment ID from Razorpay widget response.
            razorpay_order_id: Order ID from Razorpay widget response.
            razorpay_signature: Signature from Razorpay widget response.

        Returns:
            ``{"success": True, "user_count": int, "invoice": str|None, "message": str}``
        """
        endpoint, payload = self._prepare_verify_seat_payment(
            razorpay_payment_id, razorpay_order_id, razorpay_signature
        )
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_token_analytics(self, days: int = 30, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get per-user/model/source token usage analytics for dashboard.

        Queries AR Token Usage (AR core) for aggregated breakdowns.
        When user_id is provided, results are scoped to that user only.

        Args:
            days: Number of days to query (7, 30, or 90)
            user_id: Optional user filter for scoping results

        Returns:
            Analytics data with summary, daily, by_user, by_model, by_source
        """
        endpoint, payload = self._prepare_get_token_analytics(days, user_id)
        return self._request_post_json(endpoint, payload)

    def get_conversation_analytics(
        self, user_id: str = None, days: int = 30, limit: int = 50, offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Get per-conversation credit breakdown for analytics drill-down.

        Args:
            user_id: Optional user filter for privacy enforcement
            days: Number of days to query (7, 30, or 90)
            limit: Page size (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            Conversations with credits, summary totals, pagination
        """
        endpoint, payload = self._prepare_get_conversation_analytics(user_id, days, limit, offset)
        return self._request_post_json(endpoint, payload)

    def get_message_credits(self, conversation_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get per-message credit breakdown for a single conversation.

        Args:
            conversation_id: The conversation to drill into
            user_id: Optional user filter for privacy enforcement

        Returns:
            Messages with credits, model info, and content previews
        """
        endpoint, payload = self._prepare_get_message_credits(conversation_id, user_id)
        return self._request_post_json(endpoint, payload)

    def get_usage_dashboard(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive usage and billing data for dashboard."""
        endpoint, payload = self._prepare_get_usage_dashboard()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_usage_history(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """Get historical usage data for charts."""
        endpoint, payload = self._prepare_get_usage_history(days)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_invoices(self, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Get invoice history."""
        endpoint, payload = self._prepare_get_invoices(limit)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_upcoming_invoice(self) -> Optional[Dict[str, Any]]:
        """Get upcoming invoice preview (Stripe only)."""
        endpoint, payload = self._prepare_get_upcoming_invoice()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_payment_methods(self) -> Optional[Dict[str, Any]]:
        """Get saved payment methods."""
        endpoint, payload = self._prepare_get_payment_methods()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_payment_instrument(self) -> Optional[Dict[str, Any]]:
        """Get the instrument on file for automatic payments.

        One shape regardless of gateway — callers never need to branch on
        ``gateway`` to read ``autopay``. Fields that only apply to Razorpay
        (``mandate``, ``max_amount``, ``authorized_on``, ``needs_reauth``,
        ``vpa``, ``bank``, and ``card.issuer``) are ``None`` on Stripe, not
        omitted.

        Returns:
            {
              "gateway": "razorpay" | "stripe",
              "autopay": {
                "mandate": str | None,      # Razorpay only
                "status": str,
                "method": "upi" | "card" | "emandate",
                "label": str,               # "UPI Autopay"
                "display": str,             # "paul@okhdfcbank" / "Visa •••• 4242"
                "card": {
                    "last4": str | None,
                    "network": str | None,
                    "issuer": str | None,   # Razorpay only
                    "expiry": str | None,   # "MM/YYYY"
                } | None,
                "vpa": str | None,          # Razorpay UPI only
                "bank": str | None,         # Razorpay only
                "max_amount": float | None, # per-debit ceiling, Razorpay only
                "currency": str,
                "authorized_on": str | None,  # Razorpay only
                "next_charge_date": str | None,
                "needs_reauth": bool | None,  # Razorpay only
                "suspended": bool,
              } | None,               # None when no instrument is on file
              "can_update": bool,
              "update_mode": "settle" | "swap" | "portal",
              "amount_due": {"invoice", "amount", "currency"} | None,
            }

        ``update_mode`` tells the caller what ``update_payment_method`` will
        do: settle an outstanding invoice, swap the saved instrument, or
        hand back a Stripe portal URL.
        """
        endpoint, payload = self._prepare_get_payment_instrument()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def upgrade_plan(
        self,
        new_plan: str,
        billing_cycle: str = "monthly",
        gateway: Optional[str] = None,
        billing_name: Optional[str] = None,
        billing_email: Optional[str] = None,
        promo_code: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Change subscription plan (upgrade or downgrade).

        The API automatically detects whether this is an upgrade or downgrade
        based on plan hierarchy: Free < Starter < Pro < Enterprise

        Args:
            new_plan: Plan name ("Free", "Starter", "Pro", "Enterprise")
            billing_cycle: "monthly" or "annual" (default: monthly)
            gateway: "stripe" or "razorpay" (optional)
            billing_name: Customer/company name for billing
            billing_email: Email for billing notifications
            promo_code: Promotional/referral code (optional)
            payment_method: Razorpay-only — "upi" (UPI Autopay) or "card".
                Defaults to "upi" for India, "card" for international.

        Returns:
            For upgrades: {"success": True, "message": str, "subscription_id": str}
            For downgrades: {"success": True, "message": str, "effective_date": str}
            If checkout needed: {"checkout_url": str, "session_id": str, "gateway": str}
        """
        endpoint, payload = self._prepare_upgrade_plan(
            new_plan, billing_cycle, gateway, billing_name, billing_email, promo_code,
            payment_method=payment_method,
        )
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def reauthorize_mandate(
        self,
        billing_name: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Authorize a fresh recurring mandate on the customer's CURRENT plan.

        Used when the renewal cron flagged the saved Razorpay token as
        exhausted (e.g., projected next-cycle debit > UPI Autopay's
        per-debit ₹1,00,000 NPCI ceiling), or when the bank cancelled the
        token. Returns the same Razorpay-checkout shape as ``upgrade_plan``
        so callers reuse their existing widget-launching code path.
        """
        endpoint, payload = self._prepare_reauthorize_mandate(
            billing_name=billing_name,
            payment_method=payment_method,
        )
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)


    def validate_promo_code(
        self,
        promo_code: str,
        plan: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a promotional or referral code for this tenant.

        Args:
            promo_code: The promo/referral code to validate
            plan: Optional plan name to check code applicability against

        Returns:
            {"valid": True, "discount_type": str, "discount_value": float, ...}
            or {"valid": False, "error": str}
        """
        endpoint, payload = self._prepare_validate_promo_code(promo_code, plan)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base, timeout=timeout)

    def downgrade_to_free(self) -> Optional[Dict[str, Any]]:
        """
        Schedule downgrade to the Free plan at end of billing period.

        Returns:
            {"success": True, "message": str, "effective_date": str}
        """
        endpoint, payload = self._prepare_downgrade_to_free()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def cancel_scheduled_change(self) -> Optional[Dict[str, Any]]:
        """Cancel a pending downgrade that was scheduled for end of billing period."""
        endpoint, payload = self._prepare_cancel_scheduled_change()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def cancel_subscription(self, cancel_immediately: bool = False) -> Optional[Dict[str, Any]]:
        """Cancel subscription."""
        endpoint, payload = self._prepare_cancel_subscription(cancel_immediately)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def reactivate_subscription(self) -> Optional[Dict[str, Any]]:
        """Reactivate a subscription that was set to cancel at period end."""
        endpoint, payload = self._prepare_reactivate_subscription()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def pause_subscription(self) -> Optional[Dict[str, Any]]:
        """Pause subscription (Razorpay only)."""
        endpoint, payload = self._prepare_pause_subscription()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def resume_subscription(self) -> Optional[Dict[str, Any]]:
        """Resume a paused subscription (Razorpay only)."""
        endpoint, payload = self._prepare_resume_subscription()
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def update_payment_method(
        self,
        payment_method: Optional[str] = None,
        billing_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Change the instrument that pays for this subscription.

        What this does depends on whether anything is owed, which the
        server decides — call ``get_payment_instrument`` first if you need
        to know in advance:

        - An unpaid renewal exists: the returned Razorpay checkout settles
          *that* invoice at the amount it was billed for and registers the
          new instrument for autopay in the same authorization. The billing
          period does not move. ``amount_due`` carries the figure.
        - Nothing is owed: the checkout debits one currency unit purely to
          register the token, refunded automatically on capture.
        - Stripe: returns ``portal_url`` for the Customer Portal.

        Args:
            payment_method: Razorpay only — "upi" (UPI Autopay) or "card".
                Defaults to "upi" for India, "card" for international.
            billing_name: Name to prefill in the checkout widget.

        Returns:
            Razorpay: the checkout payload (``razorpay_key``,
            ``razorpay_order_id``, ``amount``, ``currency``, ``prefill``, …)
            plus ``update_mode`` and, when settling, ``amount_due``.
            Stripe: ``{"update_mode": "portal", "portal_url": str}``.
        """
        endpoint, payload = self._prepare_update_payment_method(
            payment_method=payment_method,
            billing_name=billing_name,
        )
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_subscription_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current subscription status including any scheduled changes.

        Returns:
            Dict with subscription status including plan, quota, usage, dates,
            and scheduled_change info.
        """
        endpoint, params = self._prepare_get_subscription_status()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def get_billing_history(self, limit: int = 20) -> Optional[Dict[str, Any]]:
        """
        Get payment/billing history for this tenant.

        Args:
            limit: Maximum number of records to return (default: 20)

        Returns:
            Dict with billing history list and optional portal_url (Stripe only).
        """
        endpoint, params = self._prepare_get_billing_history(limit)
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def get_billing_details(self) -> Optional[Dict[str, Any]]:
        """
        Get the tenant's billing identity (email, phone, GSTIN, address).

        Returns:
            Dict with billing_email, billing_phone, gstin, billing_address_line1,
            billing_address_line2, billing_city, billing_state, billing_pincode,
            billing_country. Empty strings for fields not yet configured.
        """
        endpoint, params = self._prepare_get_billing_details()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def save_billing_details(self, **billing_fields: Any) -> Optional[Dict[str, Any]]:
        """
        Upsert the tenant's billing identity on the ERPNext Customer + Address.

        Required: billing_email, billing_country.
        Optional: gstin, billing_state, billing_city, billing_pincode,
        billing_address_line1, billing_address_line2, billing_phone.

        Returns:
            Dict with the saved values (server-canonicalised: country name,
            normalised GSTIN, derived gst_category, etc.).
        """
        endpoint, payload = self._prepare_save_billing_details(billing_fields)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    # =========================================================================
    # Prepaid Credit APIs
    # =========================================================================

    def get_credit_balance(self) -> Optional[Dict[str, Any]]:
        """
        Get prepaid credit balance and recent transaction history.

        Returns:
            Dict with ``balance`` (int) and ``transactions`` (list).
        """
        endpoint, params = self._prepare_get_credit_balance()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def purchase_credits(
        self, credit_amount: int, gateway: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a one-time checkout session for purchasing prepaid credits.

        Args:
            credit_amount: Number of credits to purchase. Pricing is flat —
                ``(credit_amount / pack_credits) * pack_price`` per the
                AR Payment Gateway Settings.
            gateway: "stripe" or "razorpay" (optional, auto-selects).

        Returns:
            Gateway-specific checkout data (checkout URL or order ID).
        """
        endpoint, payload = self._prepare_purchase_credits(credit_amount, gateway)
        return self._request_post_json(endpoint, payload, api_base=self.billing_api_base)

    def get_expiring_credits(self) -> Optional[Dict[str, Any]]:
        """List unallocated credit batches expiring within 7 days."""
        endpoint, params = self._prepare_get_expiring_credits()
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    def get_consumption_breakdown(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """Daily credit consumption rollup grouped by source."""
        endpoint, params = self._prepare_get_consumption_breakdown(days)
        return self._request_get(endpoint, params, api_base=self.billing_api_base)

    # =========================================================================
    # Conversation APIs
    # =========================================================================

    def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """List conversations for tenant, optionally filtered by user_id."""
        endpoint, params = self._prepare_list_conversations(user_id, limit, offset, include_deleted, from_date, to_date)
        return self._request_get(endpoint, params)

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific conversation."""
        endpoint, params = self._prepare_get_conversation(conversation_id)
        return self._request_get(endpoint, params)

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get messages for a specific conversation with pagination."""
        endpoint, params = self._prepare_get_messages(conversation_id, limit, offset, include_deleted)
        return self._request_get(endpoint, params)

    def create_message(
        self,
        conversation_id: str,
        message_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        tokens_used: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new message in a conversation."""
        endpoint, payload = self._prepare_create_message(conversation_id, message_id, role, content, user_id, tokens_used, context)
        return self._request_post_json(endpoint, payload)

    def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update conversation title or user_id."""
        endpoint, payload = self._prepare_update_conversation(conversation_id, title, user_id)
        return self._request_post_json(endpoint, payload)

    def delete_conversation(self, conversation_id: str, hard_delete: bool = False) -> Optional[Dict[str, Any]]:
        """Delete a conversation. Use hard_delete=True for permanent GDPR erasure."""
        endpoint, payload = self._prepare_delete_conversation(conversation_id, hard_delete)
        return self._request_post_json(endpoint, payload)

    def delete_message(self, conversation_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        """Soft delete a specific message."""
        endpoint, payload = self._prepare_delete_message(conversation_id, message_id)
        return self._request_post_json(endpoint, payload)

    def get_sync_stats(self) -> Optional[Dict[str, Any]]:
        """Get synchronization statistics for the tenant."""
        endpoint, params = self._prepare_get_sync_stats()
        return self._request_get(endpoint, params)

    # =========================================================================
    # Streaming Events APIs (Historical)
    # =========================================================================

    def get_message_events(
        self,
        conversation_id: str,
        message_id: Optional[str] = None,
        event_types: Optional[list] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve persisted streaming events for audit trail."""
        endpoint, params = self._prepare_get_message_events(conversation_id, message_id, event_types, limit, offset)
        return self._request_get(endpoint, params)

    def get_tool_execution_stats(
        self,
        conversation_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get aggregated tool execution statistics."""
        endpoint, params = self._prepare_get_tool_execution_stats(conversation_id, from_date, to_date)
        return self._request_get(endpoint, params)

    # =========================================================================
    # User & MCP Server APIs
    # =========================================================================

    def register_user(
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
        """Register a user with Assistant Runtime."""
        endpoint, params = self._prepare_register_user(
            user_id, display_name, custom_instructions,
            locale=locale, timezone=timezone, user_role=user_role, email=email,
            registered_by=registered_by,
        )
        return self._request_post_form(endpoint, params)

    def invite_user(
        self,
        user_id: str,
        user_role: Optional[str] = None,
        invited_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invite an existing site user to the workspace as a Pending member.

        The invite reserves a billed seat immediately and auto-activates on the
        user's first activity. ``invited_by`` is the acting admin's user_id
        (used for the server-side authority check).
        """
        endpoint, params = self._prepare_invite_user(user_id, user_role, invited_by)
        return self._request_post_form(endpoint, params)

    def revoke_invite(
        self,
        user_id: str,
        revoked_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Revoke a Pending invite, freeing its reserved seat.

        Only Pending invites can be revoked; use deregister_user to remove an
        active member.
        """
        endpoint, params = self._prepare_revoke_invite(user_id, revoked_by)
        return self._request_post_form(endpoint, params)

    def resend_invite(
        self,
        user_id: str,
        resent_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resend a Pending invite, restarting its 7-day expiry window."""
        endpoint, params = self._prepare_resend_invite(user_id, resent_by)
        return self._request_post_form(endpoint, params)

    def list_invites(self) -> Dict[str, Any]:
        """List all Pending invites for this tenant (with invited-by + timing)."""
        endpoint, params = self._prepare_list_invites()
        return self._request_get(endpoint, params)

    def get_member_audit_log(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get the member-management audit log (newest first, paginated).

        Returns only member-management actions — never GDPR/append-only rows.
        Each entry's ``details`` field is a JSON string the caller must parse.
        """
        endpoint, params = self._prepare_get_member_audit_log(limit, offset)
        return self._request_get(endpoint, params)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details including MCP server count."""
        endpoint, params = self._prepare_get_user(user_id)
        return self._request_get(endpoint, params)

    def get_user_auth_status(self, user_id: str) -> Dict[str, Any]:
        """Check user authentication status and MCP server readiness.

        On success, returns AR's authoritative response — including the case
        where AR says the user genuinely doesn't exist (``user_exists: False``).

        On transport failure (network, timeout, 5xx), returns a marker
        response with ``_ar_unreachable: True`` so callers can distinguish
        "AR is briefly down" from "AR says this user is unregistered". The
        previous implementation silently returned ``user_exists: False`` for
        both cases, which caused FACO to wrongly kick logged-in users to the
        connect-account screen on transient AR hiccups.
        """
        endpoint, params = self._prepare_get_user_auth_status(user_id)
        try:
            return self._request_get(endpoint, params)
        except Exception as e:
            return {
                "_ar_unreachable": True,
                "error": str(e),
            }

    def add_user_mcp_server(
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
        """Add or update an MCP server for a user."""
        endpoint, params = self._prepare_add_user_mcp_server(
            user_id, server_name, endpoint_url, transport_type, auth_type,
            oauth_client_id, oauth_client_secret, access_token, refresh_token,
            token_expires_in, api_key, api_key_header, allowed_tools, blocked_tools,
        )
        return self._request_post_form(endpoint, params)

    def get_user_mcp_servers(self, user_id: str) -> Dict[str, Any]:
        """Get all MCP servers configured for a user."""
        endpoint, params = self._prepare_get_user_mcp_servers(user_id)
        try:
            return self._request_get(endpoint, params)
        except Exception as e:
            return {"user_id": user_id, "mcp_servers": [], "error": str(e)}

    def update_mcp_server_tokens(
        self,
        user_id: str,
        server_name: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_in: int = 3600,
    ) -> Dict[str, Any]:
        """Update OAuth tokens for an MCP server."""
        endpoint, params = self._prepare_update_mcp_server_tokens(user_id, server_name, access_token, refresh_token, token_expires_in)
        return self._request_post_form(endpoint, params)

    def remove_user_mcp_server(self, user_id: str, server_name: str) -> Dict[str, Any]:
        """Remove an MCP server from a user."""
        endpoint, params = self._prepare_remove_user_mcp_server(user_id, server_name)
        return self._request_delete(endpoint, params)

    def list_users(
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
        endpoint, params = self._prepare_list_users(status, limit, offset, include_mcp_count)
        return self._request_get(endpoint, params)

    def update_user(
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
        """
        Update user profile fields.

        Args:
            user_id: User identifier
            display_name: New display name (optional)
            custom_instructions: New custom instructions (optional)
            locale: User's locale/language preference (optional)
            timezone: User's timezone (optional)
            user_role: User's role (optional)
            email: User's email (optional)
            job_title: User's job title (optional)
            department: User's department or team (optional)
            about: Brief self-description, max 500 chars (optional)

        Returns:
            Dict with success status and message
        """
        endpoint, params = self._prepare_update_user(
            user_id, display_name, custom_instructions,
            locale=locale, timezone=timezone, user_role=user_role, email=email,
            job_title=job_title, department=department, about=about,
        )
        return self._request_post_form(endpoint, params)

    def deregister_user(self, user_id: str) -> Dict[str, Any]:
        """Permanently delete a user and all their MCP servers."""
        endpoint, params = self._prepare_deregister_user(user_id)
        return self._request_post_form(endpoint, params)

    def get_user_limit_status(self) -> Dict[str, Any]:
        """Get user count and limit for this tenant."""
        endpoint, params = self._prepare_get_user_limit_status()
        return self._request_get(endpoint, params)

    def suspend_user(self, user_id: str) -> Dict[str, Any]:
        """Suspend a user (disable their access)."""
        endpoint, params = self._prepare_suspend_user(user_id)
        return self._request_post_form(endpoint, params)

    def revoke_user(self, user_id: str) -> Dict[str, Any]:
        """Revoke a user (permanently disable, also disables their MCP servers)."""
        endpoint, params = self._prepare_revoke_user(user_id)
        return self._request_post_form(endpoint, params)

    def set_user_credit_limit(
        self,
        user_id: str,
        monthly_credit_limit: float = 0,
        acted_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set a per-user monthly credit limit. 0 = no limit (shared pool).

        ``acted_by`` is the acting admin's user_id (recorded on the member
        audit log when provided).
        """
        endpoint = "users.set_user_credit_limit"
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "monthly_credit_limit": str(monthly_credit_limit),
        }
        if acted_by:
            params["acted_by"] = acted_by
        return self._request_post_form(endpoint, params)

    def get_my_credit_status(self, user_id: str) -> Dict[str, Any]:
        """Get credit usage status for a specific user."""
        endpoint = "users.get_my_credit_status"
        params = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        return self._request_get(endpoint, params)

    # =========================================================================
    # Workflow APIs
    # =========================================================================
    # These methods route through workflows_api_base -> assistant_runtime_workflows.api

    def create_workflow(
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
        """
        endpoint, payload = self._prepare_create_workflow(
            workflow_name, graph_json, description, default_model_id,
            default_user_id, error_strategy, timeout_seconds,
        )
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def get_workflow(
        self,
        name: Optional[str] = None,
        workflow_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a workflow definition by document name or human-readable name."""
        endpoint, params = self._prepare_get_workflow(name, workflow_name)
        return self._request_get(endpoint, params, api_base=self.workflows_api_base)

    def update_workflow(
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
            graph_json: Updated workflow graph
            workflow_name: New human-readable name
            description: New description
            status: New status ("Draft", "Active", "Paused", "Archived")
            default_model_id: New default model
            default_user_id: New default user
            error_strategy: New error strategy
            timeout_seconds: New timeout
            max_node_executions: New max executions
            max_retries: New max retries

        Returns:
            {"name": str, "workflow_name": str, "status": str, "version": int}
        """
        endpoint, payload = self._prepare_update_workflow(
            name, graph_json, workflow_name, description, status,
            default_model_id, default_user_id, error_strategy,
            timeout_seconds, max_node_executions, max_retries,
        )
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def delete_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Soft-delete a workflow (sets status to Archived)."""
        endpoint, payload = self._prepare_delete_workflow(name)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def list_workflows(
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
        endpoint, params = self._prepare_list_workflows(status, page, page_size)
        return self._request_get(endpoint, params, api_base=self.workflows_api_base)

    def execute_workflow(
        self,
        name: str,
        input_data: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Manually trigger workflow execution.

        Args:
            name: AR Workflow document name (e.g., "WF-00001")
            input_data: Input data (JSON string or plain text)
            user_id: User triggering the execution

        Returns:
            {"status": "queued", "workflow": str, "workflow_name": str, "message": str}
        """
        endpoint, payload = self._prepare_execute_workflow(name, input_data, user_id)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def execute_workflow_from_event(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        user_id: str,
        trigger_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger workflow execution from a FACO-side doc event.

        Args:
            workflow_name: AR Workflow.workflow_name (human identifier)
            input_data: Structured payload {trigger, doc, changed_fields}
            user_id: User on the customer bench who saved the doc
            trigger_id: FACO AR Workflow Trigger name (for traceability)

        Returns:
            {"status": "queued", "run_name": str, "run_id": str, ...}
        """
        endpoint, payload = self._prepare_execute_workflow_from_event(
            workflow_name, input_data, user_id, trigger_id,
        )
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def cancel_workflow_run(self, run_name: str) -> Optional[Dict[str, Any]]:
        """Cancel a queued or running workflow execution."""
        endpoint, payload = self._prepare_cancel_workflow_run(run_name)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def get_workflow_run(self, run_name: str) -> Optional[Dict[str, Any]]:
        """Get execution run details including per-node results."""
        endpoint, params = self._prepare_get_workflow_run(run_name)
        return self._request_get(endpoint, params, api_base=self.workflows_api_base)

    def list_workflow_runs(
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
        endpoint, params = self._prepare_list_workflow_runs(workflow_name, status, page, page_size)
        return self._request_get(endpoint, params, api_base=self.workflows_api_base)

    def get_workflow_audit_summary(
        self,
        workflow_id: str,
        window: str = "last_7_days",
    ) -> Optional[Dict[str, Any]]:
        """
        Get an audit summary for a workflow over the given window.

        Args:
            workflow_id: AR Workflow document name (e.g., "WF-00042")
            window: One of "this_week", "last_7_days" (default), "last_30_days"

        Returns:
            {
              "workflow_id": str,
              "workflow_name": str,
              "window": str,
              "stats": {
                "runs": int,
                "success_rate": float (0..1),
                "avg_latency_seconds": float,
                "avg_credits_used": float,
                "trigger_breakdown": {"manual": int, "scheduled": int, "api": int, "doc_event": int}
              },
              "runs_per_day": [{"date": "YYYY-MM-DD", "completed": int, "failed": int, "running": int}, ...]
            }
        """
        endpoint, params = self._prepare_get_workflow_audit_summary(workflow_id, window)
        return self._request_get(endpoint, params, api_base=self.workflows_api_base)

    def set_workflow_schedule(
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
        endpoint, payload = self._prepare_set_workflow_schedule(name, cron_expression, timezone, enabled, default_input)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def validate_workflow_graph(self, graph_json: str) -> Optional[Dict[str, Any]]:
        """
        Validate a workflow graph JSON without saving.

        Args:
            graph_json: Graph JSON string to validate

        Returns:
            If valid: {"valid": True, "stats": {...}}
            If invalid: {"valid": False, "error": str}
        """
        endpoint, payload = self._prepare_validate_workflow_graph(graph_json)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def test_workflow_node(
        self,
        node_json: str,
        input_text: str = "Test input",
        default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a single node in isolation for testing.

        Args:
            node_json: Single node definition as JSON string
            input_text: Test input text (default: "Test input")
            default_model_id: LLM model to use for agent nodes
            default_user_id: User whose MCP tools to use

        Returns:
            {"status": str, "node_result": {...}, "duration_ms": int, "tokens_used": int}
        """
        endpoint, payload = self._prepare_test_workflow_node(node_json, input_text, default_model_id, default_user_id)
        return self._request_post_json(endpoint, payload, timeout=120.0, api_base=self.workflows_api_base)

    def resolve_workflow_tools(
        self,
        user_id: str,
        tool_directives: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Preview how tool directives resolve against a user's MCP tools.

        Args:
            user_id: User whose MCP tools to check against
            tool_directives: List of directive dicts

        Returns:
            {"resolved": [...], "all_tools_available": bool, "missing_tools": [...]}
        """
        endpoint, payload = self._prepare_resolve_workflow_tools(user_id, tool_directives)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    def run_workflow_node(
        self,
        name: str,
        node_id: str,
        input_text: str = "Test input",
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Run a single node from a saved workflow with manual input.

        Args:
            name: Workflow document name or workflow_name
            node_id: Node ID within the graph
            input_text: Input text to feed the node
            user_id: Override the workflow's default_user_id

        Returns:
            {"status": str, "node_id": str, "node_result": {...}, "duration_ms": int, "tokens_used": int}
        """
        endpoint, payload = self._prepare_run_workflow_node(name, node_id, input_text, user_id)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base, timeout=120.0)

    # --- Workflow Templates ---

    def export_workflow(
        self,
        name: str,
        template_name: Optional[str] = None,
        category: str = "General",
        save_as_template: bool = False,
        is_public: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Export a workflow as a portable template JSON."""
        endpoint, payload = self._prepare_export_workflow(name, template_name, category, save_as_template, is_public)
        return self._request_post_json(endpoint, payload, api_base=self.workflows_api_base)

    # `list_templates`, `get_template`, `import_template`, `update_template`,
    # and `delete_template` removed in chunk 4 — use the marketplace methods
    # (`list_listings(listing_type="Workflow")`, `get_listing`, `import_listing`,
    # `update_listing`, `delete_listing`) instead.

    def upload_listing_from_json(
        self,
        file_path: str,
        user_id: str,
        is_public: bool = False,
        is_published: bool = True,
        plan_tier: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Upload an ``ar_workflow_template_v1`` JSON file + create a listing.

        Creates an AR Workflow Template owning the graph definition, then
        wraps it in an AR Marketplace Listing. Replaces the legacy
        ``upload_template`` method (deleted in chunk 5).
        """
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
        timeout = timeout or self.timeout

        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    url,
                    data=payload,
                    files={"file": (os.path.basename(file_path), f, "application/json")},
                    headers=headers,
                    timeout=timeout,
                )
            response.raise_for_status()
            return response.json().get("message", response.json())
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            msg, body = (
                self._extract_error_payload(e.response) if e.response is not None else (None, None)
            )
            raise ARAPIError(msg or str(e), status_code=status_code, response_data=body) from e
        except requests.exceptions.RequestException as e:
            raise ARAPIError(str(e)) from e

    # `rate_template` removed in chunk 4 — use `rate_listing` instead.
    # `download_template` removed in chunk 5 — use `download_listing_as_json` instead.

    # --- GDPR / Privacy ---

    def export_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Export all user data as structured JSON (GDPR Article 20)."""
        endpoint, payload = self._prepare_export_user_data(user_id)
        return self._request_post_json(endpoint, payload)

    def erase_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Permanently delete all user data (GDPR Article 17)."""
        endpoint, payload = self._prepare_erase_user_data(user_id)
        return self._request_post_json(endpoint, payload)

    def rectify_user_data(self, user_id: str, updates: dict) -> Optional[Dict[str, Any]]:
        """Update user's personal data (GDPR Article 16)."""
        endpoint, payload = self._prepare_rectify_user_data(user_id, updates)
        return self._request_post_json(endpoint, payload)

    def restrict_user_processing(self, user_id: str, restrict: bool = True) -> Optional[Dict[str, Any]]:
        """Restrict or unrestrict data processing for a user (GDPR Article 18)."""
        endpoint, payload = self._prepare_restrict_user_processing(user_id, restrict)
        return self._request_post_json(endpoint, payload)

    def update_user_consent(self, user_id: str, consent_type: str, granted: bool = True) -> Optional[Dict[str, Any]]:
        """Update user consent for a specific processing activity."""
        endpoint, payload = self._prepare_update_user_consent(user_id, consent_type, granted)
        return self._request_post_json(endpoint, payload)

    def create_ticket(self, user_id: str, subject: str, description: str,
                      category: Optional[str] = None,
                      conversation_id: Optional[str] = None,
                      environment: Optional[dict] = None,
                      attachment_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Raise a support ticket. Returns {ticket_id, portal_link}."""
        endpoint, payload = self._prepare_create_ticket(
            user_id, subject, description, category, conversation_id, environment,
            attachment_ids)
        return self._request_post_json(endpoint, payload)

    def submit_feedback(self, user_id: str, rating: Optional[int] = None,
                       comment: Optional[str] = None,
                       category: Optional[str] = None,
                       conversation_id: Optional[str] = None,
                       environment: Optional[dict] = None) -> Optional[Dict[str, Any]]:
        """Submit product/service feedback. Returns {feedback_id}."""
        endpoint, payload = self._prepare_submit_feedback(
            user_id, rating, comment, category, conversation_id, environment)
        return self._request_post_json(endpoint, payload)

    def list_tickets(self, user_id: str, status: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """List the user's support tickets. Returns {tickets: [...]}."""
        endpoint, payload = self._prepare_list_tickets(user_id, status)
        return self._request_post_json(endpoint, payload)

    def get_ticket_thread(self, user_id: str, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a ticket's full conversation thread. Returns {ticket, messages: [...]}."""
        endpoint, payload = self._prepare_get_ticket_thread(user_id, ticket_id)
        return self._request_post_json(endpoint, payload)

    def reply_to_ticket(self, user_id: str, ticket_id: str, message: str,
                        attachment_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Post a reply to a ticket. Returns {message_id}."""
        endpoint, payload = self._prepare_reply_to_ticket(user_id, ticket_id, message, attachment_ids)
        return self._request_post_json(endpoint, payload)

    def upload_ticket_attachment(
        self,
        user_id: str,
        file_name: str,
        file_data: bytes,
        content_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Pre-upload a support-ticket attachment (image or PDF).

        Stores a private, pending File on AR scoped to this tenant+user and
        returns a reference to embed later via create_ticket/reply_to_ticket's
        ``attachment_ids``.

        Returns:
            {"file_id": str, "file_url": str, "file_name": str, "is_image": bool}
        """
        endpoint, params, f_field, f_name, f_data, c_type = self._prepare_upload_ticket_attachment(
            user_id, file_name, file_data, content_type,
        )
        return self._request_post_multipart(
            endpoint, params=params, file_field=f_field,
            file_name=f_name, file_data=f_data, content_type=c_type,
            timeout=120.0,
        )

    def get_tenant_privacy_config(self) -> Optional[Dict[str, Any]]:
        """Get tenant's privacy policy configuration."""
        endpoint, payload = self._prepare_get_tenant_privacy_config()
        return self._request_post_json(endpoint, payload)

    def update_tenant_privacy_config(self, config: dict) -> Optional[Dict[str, Any]]:
        """Update tenant's privacy policy configuration."""
        endpoint, payload = self._prepare_update_tenant_privacy_config(config)
        return self._request_post_json(endpoint, payload)

    # --- Heartbeat & Notifications ---

    def heartbeat(
        self,
        faco_version: Optional[str] = None,
        fac_version: Optional[str] = None,
        frappe_version: Optional[str] = None,
        erpnext_version: Optional[str] = None,
        python_version: Optional[str] = None,
        copilot_version: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send version/health info and receive pending notifications."""
        endpoint, payload = self._prepare_heartbeat(
            faco_version, fac_version, frappe_version, erpnext_version,
            python_version, copilot_version,
        )
        return self._request_post_json(endpoint, payload, timeout=timeout)

    def get_notifications(self, user_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Fetch pending notifications for a user."""
        endpoint, payload = self._prepare_get_notifications(user_id)
        return self._request_post_json(endpoint, payload, timeout=timeout)

    def dismiss_notification(
        self,
        notification_id: str,
        user_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Record that a user has dismissed a notification."""
        endpoint, payload = self._prepare_dismiss_notification(notification_id, user_id)
        return self._request_post_json(endpoint, payload, timeout=timeout)

    # -------------------------------------------------------------------
    # Marketplace API — routes via marketplace_api_base
    # -------------------------------------------------------------------

    def list_listings(
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
        """List marketplace listings (workflows / prompts / skills) visible to the tenant."""
        endpoint, params = self._prepare_list_listings(
            listing_type, category, search, featured_only, min_rating,
            plan_tier, sort_by, page, page_size, user_id,
        )
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base, timeout=timeout)

    def get_listing(
        self, name: str, user_id: Optional[str] = None,
        include_source: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get full listing details + the wrapped source record."""
        endpoint, params = self._prepare_get_listing(name, user_id, include_source)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def import_listing(
        self,
        user_id: str,
        name: str,
        new_title: Optional[str] = None,
        variables: Optional[str] = None,
        default_model_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Import a marketplace listing into the requesting tenant."""
        endpoint, payload = self._prepare_import_listing(
            user_id, name, new_title, variables, default_model_id,
        )
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def update_listing(
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
        """Update a marketplace listing's metadata. Owner-only or admin."""
        endpoint, payload = self._prepare_update_listing(
            name, title, short_description, description, category, tags,
            icon, is_public, is_published, plan_tier,
        )
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def delete_listing(self, name: str) -> Optional[Dict[str, Any]]:
        """Delete a marketplace listing. Owner-only or admin."""
        endpoint, payload = self._prepare_delete_listing(name)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def rate_listing(
        self, user_id: str, listing: str, rating: int,
        review: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Submit (or update) a 1-5 star rating + optional review."""
        endpoint, payload = self._prepare_rate_listing(user_id, listing, rating, review)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def report_listing(
        self, user_id: str, listing: str, reason: str,
        details: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """File an abuse / spam / copyright report against a listing."""
        endpoint, payload = self._prepare_report_listing(user_id, listing, reason, details)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def list_pending_reviews(
        self, page: int = 0, page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """Admin: list listings awaiting moderation (oldest-first)."""
        endpoint, params = self._prepare_list_pending_reviews(page, page_size)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def approve_listing(
        self, listing: str, notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Admin: approve a listing for cross-tenant visibility."""
        endpoint, payload = self._prepare_approve_listing(listing, notes)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def reject_listing(
        self, listing: str, notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Admin: reject a listing's moderation request."""
        endpoint, payload = self._prepare_reject_listing(listing, notes)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def get_creator_stats(
        self, user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Aggregate stats for listings authored by this tenant."""
        endpoint, params = self._prepare_get_creator_stats(user_id)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def list_my_listings(
        self,
        user_id: Optional[str] = None,
        listing_type: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """List listings created by this tenant."""
        endpoint, params = self._prepare_list_my_listings(user_id, listing_type, page, page_size)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    # -------------------------------------------------------------------
    # Marketplace publishing + downloads + version checks (chunk 5)
    # -------------------------------------------------------------------

    def publish_workflow(
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
        """Export a workflow + create a listing wrapping the new template."""
        endpoint, payload = self._prepare_publish_workflow(
            user_id, workflow_name, template_name, category, short_description,
            description, tags, is_public, plan_tier,
        )
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def download_listing_as_json(self, name: str) -> Optional[Dict[str, Any]]:
        """Return a workflow listing as portable ar_workflow_template_v1 JSON."""
        endpoint, params = self._prepare_download_listing_as_json(name)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def check_workflow_update(self, name: str) -> Optional[Dict[str, Any]]:
        """Check whether the workflow's source template has a newer version."""
        endpoint, params = self._prepare_check_workflow_update(name)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def check_all_workflow_updates(self) -> Optional[Dict[str, Any]]:
        """Batch-check all tenant workflows for available template updates."""
        endpoint, params = self._prepare_check_all_workflow_updates()
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    # -------------------------------------------------------------------
    # Tenant Packs API — admin-grade pack management for the calling tenant
    #
    # These methods hit the *signed* marketplace endpoints — tenant identity
    # comes from the HMAC signature, so callers don't pass a tenant arg.
    # -------------------------------------------------------------------

    def list_packs(self) -> Optional[Dict[str, Any]]:
        """Return every active pack with eligibility + enablement annotations.

        Response shape: ``{"packs": [...]}`` where each pack dict carries
        ``eligible``, ``enabled``, ``prompt_count``, ``skill_count`` and the
        underlying ``AR Platform Pack`` fields.
        """
        endpoint, params = self._prepare_list_packs()
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def get_pack_contents(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Return the named prompts + skills of a pack the tenant owns.

        Response: ``{"pack_id": str, "prompts": [{prompt_id,title,category}],
        "skills": [{skill_id,title,category,skill_type}]}``.
        """
        endpoint, params = self._prepare_get_pack_contents(pack_id)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def set_industry(
        self,
        industry: Optional[str],
        auto_enable: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Set the calling tenant's industry and optionally auto-enable its pack.

        Pass an empty/None industry to clear (skip path). Returns
        ``{"industry": str|None, "enabled_pack": str|None}``.
        """
        endpoint, payload = self._prepare_set_industry(industry, auto_enable)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def set_pack_enabled(
        self,
        pack_id: str,
        enabled: bool,
        source: str = "User",
    ) -> Optional[Dict[str, Any]]:
        """Toggle a pack on or off for the calling tenant."""
        endpoint, payload = self._prepare_set_pack_enabled(pack_id, enabled, source)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    def get_recommended_pack(
        self, user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return at most one pack to surface in the onboarding recommendation toast.

        Returns ``{"pack": <dict|null>}``. Returns null when the user has
        already dismissed the toast, when there's no industry on the tenant,
        or when the recommended pack is already enabled.
        """
        endpoint, params = self._prepare_get_recommended_pack(user_id)
        return self._request_get(endpoint, params, api_base=self.marketplace_api_base)

    def dismiss_pack_recommendation(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mark the recommendation toast as dismissed for the given user."""
        endpoint, payload = self._prepare_dismiss_pack_recommendation(user_id)
        return self._request_post_json(endpoint, payload, api_base=self.marketplace_api_base)

    # -------------------------------------------------------------------
    # Pack acquisition + checkout (paid packs v2)
    # -------------------------------------------------------------------

    def enable_pack_as_free_grant(
        self, pack_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Activate a pack as the tenant's free-grant pick. Permanent."""
        endpoint, payload = self._prepare_enable_pack_as_free_grant(pack_id)
        return self._request_post_json(
            endpoint, payload, api_base=self.marketplace_api_base
        )

    def grant_pack_as_admin(
        self, pack_id: str, granted_by_user: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Admin grant — does not consume free allowance."""
        endpoint, payload = self._prepare_grant_pack_as_admin(
            pack_id, granted_by_user
        )
        return self._request_post_json(
            endpoint, payload, api_base=self.marketplace_api_base
        )

    def toggle_purchased_pack(
        self, pack_id: str, enabled: bool,
    ) -> Optional[Dict[str, Any]]:
        """Enable or disable a purchased pack."""
        endpoint, payload = self._prepare_toggle_purchased_pack(pack_id, enabled)
        return self._request_post_json(
            endpoint, payload, api_base=self.marketplace_api_base
        )

    def list_pack_purchases(self) -> Optional[Dict[str, Any]]:
        """Return the tenant's AR Pack Purchase history."""
        endpoint, params = self._prepare_list_pack_purchases()
        return self._request_get(
            endpoint, params, api_base=self.marketplace_api_base
        )

    def initiate_pack_checkout(
        self, pack_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Create a Razorpay one-time order for a pack purchase."""
        endpoint, payload = self._prepare_initiate_pack_checkout(pack_id)
        return self._request_post_json(
            endpoint, payload, api_base=self.billing_api_base
        )

    def verify_razorpay_pack_payment(
        self,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> Optional[Dict[str, Any]]:
        """Verify a Razorpay pack payment from the embedded widget."""
        endpoint, payload = self._prepare_verify_razorpay_pack_payment(
            razorpay_payment_id, razorpay_order_id, razorpay_signature
        )
        return self._request_post_json(
            endpoint, payload, api_base=self.billing_api_base
        )

    # =========================================================================
    # HITL APIs
    # =========================================================================

    def get_pending_interrupt(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the currently-pending HITL pause for `session_id`, or None.

        Used by the FAC chat frontend on mount + on socket reconnect to
        rehydrate the InteractionCard after the user steps away or the
        socket times out.

        Args:
            session_id: The AR session whose HITL pause to retrieve.
            user_id: The authenticated user on the FAC side (frappe.session.user).
                     Checked against the persisted row's user_id on the AR side.

        Response shape (when pending):
            {
                "pending": True,
                "session_id": str,
                "expires_at": str (ISO),
                "event": {
                    "tool_id": str,
                    "tool_name": str,
                    "input": dict,
                    "interrupts": [{"id", "name", "reason"}, ...]
                }
            }
        Or `{"pending": False}` when nothing is pending.
        Or None on transport error.
        """
        endpoint, params = self._prepare_get_pending_interrupt(session_id, user_id)
        return self._request_get(endpoint, params, api_base=self.api_base)

    def cancel_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Stop the session's active stream / clear its HITL pause."""
        endpoint, payload = self._prepare_cancel_session(session_id)
        return self._request_post_json(endpoint, payload, api_base=self.api_base)

    # =========================================================================
    # Voice API
    # =========================================================================

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/webm",
        user_id: Optional[str] = None,
        duration_ms: int = 0,
        language: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe an audio blob via AR's voice endpoint.

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
        return self._request_post_multipart(
            endpoint="transcribe_v1",
            params=params,
            file_field="audio",
            file_name="audio.webm",
            file_data=audio_bytes,
            content_type=mime_type,
            api_base=self.voice_api_base,
        )


# =============================================================================
# Standalone Functions
# =============================================================================


def get_terms(ar_url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch current Terms and Conditions from Assistant Runtime.

    No authentication required - allows display before registration.

    Args:
        ar_url: Assistant Runtime server URL

    Returns:
        Terms content dict or None on failure
    """
    url = f"{ar_url.rstrip('/')}/api/method/assistant_runtime.api.get_terms"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json().get("message", response.json())
    except requests.exceptions.RequestException:
        return None


def validate_referral_code(ar_url: str, referral_code: str) -> Dict[str, Any]:
    """
    Validate a partner referral code against the AR server.

    Guest-allowed endpoint — no tenant credentials required (used during signup).

    Args:
        ar_url: Assistant Runtime server URL
        referral_code: The referral code to validate

    Returns:
        {"valid": True, "partner_name": str, "referral_code": str} on success,
        {"valid": False, "error": str} on failure.
    """
    url = f"{ar_url.rstrip('/')}/api/method/assistant_runtime.api.validate_referral_code"
    try:
        response = requests.post(
            url,
            json={"referral_code": referral_code},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("message", response.json())
    except requests.exceptions.RequestException as e:
        return {"valid": False, "error": str(e)}


def register_tenant(
    ar_url: str,
    site_url: str,
    owner_email: str,
    application_id: str,
    fac_mcp_endpoint: Optional[str] = None,
    terms_accepted: bool = True,
    terms_version: Optional[str] = None,
    accepted_by: Optional[str] = None,
    referral_code: Optional[str] = None,
    promotion_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Register this installation as a tenant with Assistant Runtime.

    Args:
        ar_url: Assistant Runtime server URL
        site_url: This site's URL (used for origin binding)
        owner_email: Email address of the tenant owner. Required. AR sends a
            verification email to this address; the tenant is not fully active
            until the owner confirms. After confirmation, call
            ``get_initial_secret(ar_url, verification_token)`` with the token
            from the link to retrieve the ``tenant_secret``. The response from
            this function does **not** include the secret directly.
        application_id: The AR Application identifier this tenant belongs to
            (required, e.g. "faco"). AR hard-validates that a matching
            AR Application row exists and stores it on AR Tenant.application.
        fac_mcp_endpoint: Optional FAC MCP server endpoint URL
        terms_accepted: Must be True to register
        terms_version: Version of terms being accepted
        accepted_by: User who accepted the terms
        referral_code: Optional referral code
        promotion_token: Optional one-time waitlist promotion token. When an
            admin approves a waitlisted applicant, AR emails a resume link
            carrying this token; passing it here lets the applicant bypass the
            registration cap exactly once.

    Returns:
        Registration result with tenant_id (secret delivered via email link), or error
    """
    url = f"{ar_url.rstrip('/')}/api/method/assistant_runtime.api.register_tenant"

    payload = {
        "site_url": site_url,
        "owner_email": owner_email,
        "application_id": application_id,
        "terms_accepted": terms_accepted,
        "terms_version": terms_version,
        "accepted_by": accepted_by,
    }

    if fac_mcp_endpoint:
        payload["fac_endpoint"] = fac_mcp_endpoint

    if referral_code:
        payload["referral_code"] = referral_code

    if promotion_token:
        payload["promotion_token"] = promotion_token

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("message", response.json())
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_registration_state(
    ar_url: str,
    site_url: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Look up whether a tenant already exists for site_url (guest, no auth).

    Returns {"exists": bool, "status": str, "owner_email_masked": str,
    "reregistration": bool} or {"error": str}. Never returns a secret.
    """
    url = f"{ar_url.rstrip('/')}/api/method/assistant_runtime.api.get_registration_state"
    payload = {"site_url": site_url}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    try:
        response = requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json"}, timeout=30,
        )
        response.raise_for_status()
        return response.json().get("message", response.json())
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_initial_secret(ar_url: str, verification_token: str) -> Dict[str, Any]:
    """One-shot retrieval of the freshly-minted tenant_secret after the
    owner has confirmed their email via the verification link.

    Returns: {"tenant_secret": str} on success, or {"error": str} on failure.
    Subsequent calls with the same token return {"error": ...} (single use).
    """
    url = f"{ar_url.rstrip('/')}/api/method/assistant_runtime.api.get_initial_secret"
    try:
        resp = requests.post(
            url,
            json={"verification_token": verification_token},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("message", resp.json())
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_rotated_secret(ar_url: str, rebind_token: str) -> Dict[str, Any]:
    """One-shot retrieval of the rotated tenant_secret after a rebind has
    been confirmed by the owner via the email link.

    Returns: {"tenant_secret": str} on success, or {"error": str} on failure.
    """
    url = f"{ar_url.rstrip('/')}/api/method/assistant_runtime.api.get_rotated_secret"
    try:
        resp = requests.post(
            url,
            json={"rebind_token": rebind_token},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("message", resp.json())
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

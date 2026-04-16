# Assistant Runtime SDK - Base Client
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Base client class with shared authentication and configuration logic.

Both AssistantRuntimeClient (sync) and AsyncAssistantRuntimeClient (async) inherit from this.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable

from .auth import generate_signature
from .streaming import parse_sse_line
from .exceptions import ARConfigurationError, ARBillingUnavailableError, ARAuthenticationError


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
    - Multi API base routing (core + billing + memory + workflows)

    Both AssistantRuntimeClient (sync) and AsyncAssistantRuntimeClient (async) inherit from this class.

    Args:
        tenant_id: Unique tenant identifier from Assistant Runtime
        tenant_secret: HMAC secret for request signing
        ar_url: Base URL of Assistant Runtime server (default: https://ar.example.com)
        logger: Optional logger instance (uses stdlib logging if None)
        timeout: Default request timeout in seconds (default: 30.0)
        billing_api_base: Override URL for billing API endpoints. Defaults to
            ``{ar_url}/api/method/assistant_runtime_payments.api``. Pass a full
            URL or just a Frappe dotted module path (e.g.
            ``"assistant_runtime_payments.api"``).
        memory_api_base: Override URL for memory/onboarding API endpoints. Defaults to
            ``{ar_url}/api/method/assistant_runtime_memory.api``. Pass a full
            URL or just a Frappe dotted module path (e.g.
            ``"assistant_runtime_memory.api"``).
        workflows_api_base: Override URL for workflow API endpoints. Defaults to
            ``{ar_url}/api/method/assistant_runtime_workflows.api``. Pass a full
            URL or just a Frappe dotted module path (e.g.
            ``"assistant_runtime_workflows.api"``).

    Example:
        >>> # Don't instantiate directly - use AssistantRuntimeClient or AsyncAssistantRuntimeClient
        >>> from assistant_runtime_sdk import AssistantRuntimeClient
        >>> client = AssistantRuntimeClient("tenant-id", "secret")
    """

    DEFAULT_AR_URL = "https://ar.example.com"
    DEFAULT_BILLING_API_MODULE = "assistant_runtime_payments.api"
    DEFAULT_MEMORY_API_MODULE = "assistant_runtime_memory.api"
    DEFAULT_WORKFLOWS_API_MODULE = "assistant_runtime_workflows.api"
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
        billing_api_base: Optional[str] = None,
        memory_api_base: Optional[str] = None,
        workflows_api_base: Optional[str] = None,
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

        # Companion app API bases
        self.billing_api_base = self._resolve_api_base(billing_api_base, self.DEFAULT_BILLING_API_MODULE)
        self.memory_api_base = self._resolve_api_base(memory_api_base, self.DEFAULT_MEMORY_API_MODULE)
        self.workflows_api_base = self._resolve_api_base(workflows_api_base, self.DEFAULT_WORKFLOWS_API_MODULE)

        # Billing availability state — None means unknown (not yet probed)
        self._billing_available: Optional[bool] = None

        # Setup logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def _resolve_api_base(self, override: Optional[str], default_module: str) -> str:
        """Resolve an API base URL from an override or default module path."""
        if override is None:
            return f"{self.ar_url}/api/method/{default_module}"
        if override.startswith(("http://", "https://")):
            return override.rstrip("/")
        return f"{self.ar_url}/api/method/{override}"

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
        Build full URL for a core API endpoint.

        Args:
            endpoint: Endpoint path (e.g., 'streaming.stream_chat')

        Returns:
            Full URL
        """
        return f"{self.api_base}.{endpoint}"

    def _build_billing_endpoint_url(self, endpoint: str) -> str:
        """
        Build full URL for a billing/payments API endpoint.

        Routes through ``billing_api_base`` which targets the payments app.

        Args:
            endpoint: Endpoint path (e.g., 'get_usage_dashboard')

        Returns:
            Full URL
        """
        return f"{self.billing_api_base}.{endpoint}"

    def _build_memory_endpoint_url(self, endpoint: str) -> str:
        """
        Build full URL for a memory/onboarding API endpoint.

        Routes through ``memory_api_base`` which targets the memory app.

        Args:
            endpoint: Endpoint path (e.g., 'onboarding.get_onboarding_status')

        Returns:
            Full URL
        """
        return f"{self.memory_api_base}.{endpoint}"

    def _build_workflows_endpoint_url(self, endpoint: str) -> str:
        """
        Build full URL for a workflow API endpoint.

        Routes through ``workflows_api_base`` which targets the workflows app.

        Args:
            endpoint: Endpoint path (e.g., 'workflows.create_workflow')

        Returns:
            Full URL
        """
        return f"{self.workflows_api_base}.{endpoint}"

    def _require_billing(self) -> None:
        """
        Guard for billing methods.

        Raises ``ARBillingUnavailableError`` only if billing has been explicitly
        probed and found unavailable (``_billing_available is False``). When the
        state is unknown (``None``), the call proceeds — it will succeed if the
        payments app is installed, or fail with an HTTP error if not.
        """
        if self._billing_available is False:
            raise ARBillingUnavailableError()

    def _prepare_stream_payload(
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
    ) -> Dict[str, Any]:
        """
        Prepare JSON payload for stream_chat POST request.

        Args:
            session_id: Conversation session identifier
            message: User's message (optional when interrupt_response is provided)
            user_id: User identifier (required)
            context: Optional page context (sent as native dict, not JSON string)
            model_id: Optional model ID
            attachments: Optional list of attachments (images/documents)
                Each attachment: {
                    "type": "image" | "document",
                    "format": "png" | "jpeg" | "gif" | "webp" | "pdf" | "txt",
                    "data": "<base64-encoded-data>",
                    "name": "optional-filename.png",  # Optional
                    "file_url": "/files/..."  # Optional, for storage reference
                }
            system_prompt_addendum: Optional per-request addition to the system prompt
            client_type: Optional client type for tool filtering (widget/spa/mobile/api)
            interrupt_response: Optional HITL resume responses. Each item:
                {"interruptId": str, "response": "approve"|"rejected"|"trust"|"session"}
            message_id: Optional message ID to reuse on HITL resume (ensures all
                events across multiple resume cycles link to the same message)

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
            "user_id": user_id,
        }

        if message:
            payload["message"] = message

        if context:
            # Context is sent as a native dict in JSON body, not a JSON string
            payload["context"] = context

        if model_id:
            payload["model_id"] = model_id

        if attachments:
            payload["attachments"] = attachments

        if system_prompt_addendum:
            payload["system_prompt_addendum"] = system_prompt_addendum

        if client_type:
            payload["client_type"] = client_type

        if interrupt_response:
            payload["interrupt_response"] = interrupt_response

        if message_id:
            payload["message_id"] = message_id

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

    # =========================================================================
    # Error Extraction
    # =========================================================================

    @staticmethod
    def _extract_error_from_data(data: dict) -> Optional[str]:
        """Extract a human-readable error message from a Frappe error response dict.

        Works with both sync and async clients since it accepts a parsed dict
        rather than a library-specific response object.
        """
        try:
            server_messages = data.get("_server_messages")
            if server_messages:
                messages = json.loads(server_messages)
                if messages:
                    msg = json.loads(messages[0])
                    return msg.get("message", str(msg))
            if data.get("exception"):
                exc = data["exception"]
                lines = exc.strip().splitlines()
                if lines:
                    last = lines[-1]
                    if ": " in last:
                        return last.split(": ", 1)[1]
                    return last
            if data.get("message"):
                return data["message"]
        except Exception:
            pass
        return None

    # =========================================================================
    # Prepare Methods — Tenant
    # =========================================================================

    def _prepare_get_tenant_info(self) -> tuple:
        """Returns (endpoint, params)."""
        return "get_tenant_info", {"tenant_id": self.tenant_id}

    def _prepare_accept_terms(self, terms_version: str, accepted_by: str) -> tuple:
        """Returns (endpoint, payload)."""
        return "accept_terms", {
            "tenant_id": self.tenant_id,
            "terms_version": terms_version,
            "accepted_by": accepted_by,
        }

    # =========================================================================
    # Prepare Methods — Models
    # =========================================================================

    def _prepare_list_available_models(self) -> tuple:
        return "streaming.list_available_models", {"tenant_id": self.tenant_id}

    def _prepare_get_available_models(self) -> tuple:
        return "get_available_models", {"tenant_id": self.tenant_id}

    def _prepare_set_preferred_model(self, model_id: str) -> tuple:
        return "set_preferred_model", {"tenant_id": self.tenant_id, "model_id": model_id}

    # =========================================================================
    # Prepare Methods — Prompts & Suggestions
    # =========================================================================

    def _prepare_list_prompts(self, user_id: str, cursor: Optional[str] = None) -> tuple:
        params = {"tenant_id": self.tenant_id, "user_id": user_id}
        if cursor:
            params["cursor"] = cursor
        return "prompts.list_prompts", params

    def _prepare_get_prompt(self, prompt_name: str, user_id: str,
                            arguments: Optional[Dict[str, Any]] = None) -> tuple:
        payload = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "prompt_name": prompt_name,
        }
        if arguments:
            payload["arguments"] = arguments
        return "prompts.get_prompt", payload

    def _prepare_get_suggestions(self, user_id: str,
                                 context: Optional[Dict[str, Any]] = None,
                                 limit: int = 8) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "limit": str(limit),
        }
        if context:
            params["context"] = json.dumps(context)
        return "suggestions.get_suggestions", params

    # =========================================================================
    # Prepare Methods — Onboarding
    # =========================================================================

    def _prepare_get_onboarding_status(self, user_id: str) -> tuple:
        return "onboarding.get_onboarding_status", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_complete_onboarding(self, user_id: str,
                                     conversation_id: Optional[str] = None) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        return "onboarding.complete_onboarding", payload

    # =========================================================================
    # Prepare Methods — Documents
    # =========================================================================

    def _prepare_upload_document(
        self,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None,
        visibility: Optional[str] = None,
        shared_with: Optional[List[str]] = None,
    ) -> tuple:
        """Returns (endpoint, params, file_field, file_name, file_data, content_type)."""
        import mimetypes as _mt
        import os as _os

        if file_path and file_data:
            raise ARConfigurationError("Provide either file_path or file_data, not both")
        if not file_path and not file_data:
            raise ARConfigurationError("Either file_path or file_data is required")
        if file_data and not file_name:
            raise ARConfigurationError("file_name is required when using file_data")

        if visibility and visibility not in ("public", "private", "shared"):
            raise ARConfigurationError(
                f"Invalid visibility: {visibility}. Must be public, private, or shared."
            )
        if visibility == "shared" and not shared_with:
            raise ARConfigurationError(
                "shared_with is required when visibility is 'shared'"
            )

        if file_path:
            with open(file_path, "rb") as f:
                data = f.read()
            if not file_name:
                file_name = _os.path.basename(file_path)
        else:
            data = file_data

        if not content_type:
            guessed, _ = _mt.guess_type(file_name)
            content_type = guessed or "application/octet-stream"

        params: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if user_id:
            params["user_id"] = user_id
        if visibility:
            params["visibility"] = visibility
        if shared_with:
            params["shared_with"] = json.dumps(shared_with)

        return (
            "documents.upload_document",
            params,
            "file",
            file_name,
            data,
            content_type,
        )

    def _prepare_list_documents(
        self, limit: int = 50, offset: int = 0, user_id: Optional[str] = None
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "limit": str(limit),
            "offset": str(offset),
        }
        if user_id:
            params["user_id"] = user_id
        return "documents.list_documents", params

    def _prepare_get_document(self, document_id: str) -> tuple:
        return "documents.get_document", {
            "tenant_id": self.tenant_id,
            "document_id": document_id,
        }

    def _prepare_get_document_content(
        self, document_id: str, user_id: Optional[str] = None, download: bool = False
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "document_id": document_id,
        }
        if user_id:
            params["user_id"] = user_id
        if download:
            params["download"] = "1"
        return "documents.get_document_content", params

    def _prepare_delete_document(
        self, document_id: str, user_id: Optional[str] = None
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "document_id": document_id,
        }
        if user_id:
            payload["user_id"] = user_id
        return "documents.delete_document", payload

    def _prepare_get_storage_info(self) -> tuple:
        return "documents.get_storage_info", {"tenant_id": self.tenant_id}

    def _prepare_update_document_access(
        self,
        document_id: str,
        user_id: str,
        visibility: Optional[str] = None,
        add_users: Optional[List[str]] = None,
        remove_users: Optional[List[str]] = None,
    ) -> tuple:
        """Returns (endpoint, payload) for updating document visibility/sharing."""
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "document_id": document_id,
            "user_id": user_id,
        }
        if visibility:
            payload["visibility"] = visibility
        if add_users:
            payload["add_users"] = json.dumps(add_users)
        if remove_users:
            payload["remove_users"] = json.dumps(remove_users)
        return "documents.update_document_access", payload

    # =========================================================================
    # Prepare Methods — Memories
    # =========================================================================

    def _prepare_list_memories(
        self, user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50, offset: int = 0
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "limit": str(limit),
            "offset": str(offset),
        }
        if user_id:
            params["user_id"] = user_id
        if memory_type:
            params["memory_type"] = memory_type
        return "memories.list_memories", params

    def _prepare_delete_memory(self, user_id: str, memory_id: str) -> tuple:
        return "memories.delete_memory", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "memory_id": memory_id,
        }

    def _prepare_delete_all_memories(self, user_id: str) -> tuple:
        return "memories.delete_all_memories", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_update_memory(self, user_id: str, memory_id: str, content: str) -> tuple:
        return "memories.update_memory", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "memory_id": memory_id,
            "content": content,
        }

    def _prepare_get_memory_stats(self, user_id: Optional[str] = None) -> tuple:
        params: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if user_id:
            params["user_id"] = user_id
        return "memories.get_memory_stats", params

    def _prepare_get_memory_summary(self, user_id: str, force: bool = False) -> tuple:
        params: Dict[str, Any] = {"tenant_id": self.tenant_id, "user_id": user_id}
        if force:
            params["force"] = "1"
        return "memories.get_memory_summary", params

    # =========================================================================
    # Prepare Methods — Shared Knowledge
    # =========================================================================

    def _prepare_get_shared_knowledge(self) -> tuple:
        return "shared_knowledge.get_shared_knowledge", {
            "tenant_id": self.tenant_id,
        }

    def _prepare_update_shared_knowledge(self, content: str) -> tuple:
        return "shared_knowledge.update_shared_knowledge", {
            "tenant_id": self.tenant_id,
            "content": content,
        }

    def _prepare_share_memory_to_knowledge(self, user_id: str, memory_id: str) -> tuple:
        return "shared_knowledge.share_memory", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "memory_id": memory_id,
        }

    # =========================================================================
    # Prepare Methods — Tools
    # =========================================================================

    def _prepare_list_tools(self, user_id: str,
                            server: Optional[str] = None) -> tuple:
        params: Dict[str, Any] = {"tenant_id": self.tenant_id, "user_id": user_id}
        if server:
            params["server"] = server
        return "tools.list_tools", params

    # =========================================================================
    # Prepare Methods — Billing
    # =========================================================================

    def _prepare_get_recommended_gateway(self) -> tuple:
        self._require_billing()
        return "get_recommended_gateway", {"tenant_id": self.tenant_id}

    def _prepare_get_available_gateways(self) -> tuple:
        self._require_billing()
        return "get_available_gateways", {"tenant_id": self.tenant_id}

    def _prepare_preview_plan_pricing(
        self, plan: str, billing_cycle: str = "monthly",
    ) -> tuple:
        self._require_billing()
        return "preview_plan_pricing", {
            "tenant_id": self.tenant_id,
            "plan": plan,
            "billing_cycle": billing_cycle,
        }

    def _prepare_download_invoice_pdf(self, ar_invoice_name: str) -> tuple:
        self._require_billing()
        return "download_invoice_pdf", {
            "tenant_id": self.tenant_id,
            "ar_invoice_name": ar_invoice_name,
        }

    def _prepare_initiate_checkout(
        self, plan: str, billing_cycle: str = "monthly",
        gateway: Optional[str] = None, billing_name: Optional[str] = None,
        billing_email: Optional[str] = None,
    ) -> tuple:
        self._require_billing()
        payload: Dict[str, Any] = {
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
        return "initiate_checkout", payload

    def _prepare_verify_checkout(self, session_id: Optional[str] = None) -> tuple:
        self._require_billing()
        payload: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if session_id:
            payload["session_id"] = session_id
        return "verify_checkout", payload

    def _prepare_verify_razorpay_payment(
        self, razorpay_payment_id: str,
        razorpay_subscription_id: str, razorpay_signature: str,
    ) -> tuple:
        self._require_billing()
        return "verify_razorpay_payment", {
            "tenant_id": self.tenant_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_subscription_id": razorpay_subscription_id,
            "razorpay_signature": razorpay_signature,
        }

    def _prepare_verify_razorpay_credit_payment(
        self, razorpay_payment_id: str,
        razorpay_order_id: str, razorpay_signature: str,
    ) -> tuple:
        self._require_billing()
        return "verify_razorpay_credit_payment", {
            "tenant_id": self.tenant_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_signature": razorpay_signature,
        }

    def _prepare_get_token_analytics(self, days: int = 30, user_id: str = None) -> tuple:
        params = {"tenant_id": self.tenant_id, "days": days}
        if user_id:
            params["user_id"] = user_id
        return "usage.get_token_analytics", params

    def _prepare_get_conversation_analytics(
        self, user_id: str = None, days: int = 30, limit: int = 50, offset: int = 0,
    ) -> tuple:
        params = {"tenant_id": self.tenant_id, "days": days, "limit": limit, "offset": offset}
        if user_id:
            params["user_id"] = user_id
        return "usage.get_conversation_analytics", params

    def _prepare_get_message_credits(self, conversation_id: str, user_id: str = None) -> tuple:
        params = {"tenant_id": self.tenant_id, "conversation_id": conversation_id}
        if user_id:
            params["user_id"] = user_id
        return "usage.get_message_credits", params

    def _prepare_get_usage_dashboard(self) -> tuple:
        self._require_billing()
        return "get_usage_dashboard", {"tenant_id": self.tenant_id}

    def _prepare_get_usage_history(self, days: int = 30) -> tuple:
        self._require_billing()
        return "get_usage_history", {"tenant_id": self.tenant_id, "days": days}

    def _prepare_get_invoices(self, limit: int = 10) -> tuple:
        self._require_billing()
        return "get_invoices", {"tenant_id": self.tenant_id, "limit": limit}

    def _prepare_get_upcoming_invoice(self) -> tuple:
        self._require_billing()
        return "get_upcoming_invoice", {"tenant_id": self.tenant_id}

    def _prepare_get_payment_methods(self) -> tuple:
        self._require_billing()
        return "get_payment_methods", {"tenant_id": self.tenant_id}

    def _prepare_upgrade_plan(
        self, new_plan: str, billing_cycle: str = "monthly",
        gateway: Optional[str] = None, billing_name: Optional[str] = None,
        billing_email: Optional[str] = None,
        promo_code: Optional[str] = None,
    ) -> tuple:
        self._require_billing()
        payload: Dict[str, Any] = {
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
        if promo_code:
            payload["promo_code"] = promo_code
        return "upgrade_plan", payload

    def _prepare_validate_promo_code(
        self, promo_code: str, plan: Optional[str] = None,
    ) -> tuple:
        self._require_billing()
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "promo_code": promo_code,
        }
        if plan:
            payload["plan"] = plan
        return "promotions.validate_promo_code", payload

    def _prepare_downgrade_to_free(self) -> tuple:
        self._require_billing()
        return "downgrade_to_free", {"tenant_id": self.tenant_id}

    def _prepare_cancel_scheduled_change(self) -> tuple:
        self._require_billing()
        return "cancel_scheduled_change", {"tenant_id": self.tenant_id}

    def _prepare_cancel_subscription(self, cancel_immediately: bool = False) -> tuple:
        self._require_billing()
        return "cancel_subscription", {
            "tenant_id": self.tenant_id,
            "cancel_immediately": cancel_immediately,
        }

    def _prepare_reactivate_subscription(self) -> tuple:
        self._require_billing()
        return "reactivate_subscription", {"tenant_id": self.tenant_id}

    def _prepare_pause_subscription(self) -> tuple:
        self._require_billing()
        return "pause_subscription", {"tenant_id": self.tenant_id}

    def _prepare_resume_subscription(self) -> tuple:
        self._require_billing()
        return "resume_subscription", {"tenant_id": self.tenant_id}

    def _prepare_update_payment_method(self) -> tuple:
        self._require_billing()
        return "update_payment_method", {"tenant_id": self.tenant_id}

    def _prepare_get_subscription_status(self) -> tuple:
        self._require_billing()
        return "get_subscription_status", {"tenant_id": self.tenant_id}

    def _prepare_get_billing_history(self, limit: int = 20) -> tuple:
        self._require_billing()
        return "get_billing_history", {"tenant_id": self.tenant_id, "limit": limit}

    def _prepare_get_credit_balance(self) -> tuple:
        self._require_billing()
        return "get_credit_balance", {"tenant_id": self.tenant_id}

    def _prepare_purchase_credits(self, token_amount: int,
                                  gateway: Optional[str] = None) -> tuple:
        self._require_billing()
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "token_amount": token_amount,
        }
        if gateway:
            payload["gateway"] = gateway
        return "purchase_credits", payload

    # =========================================================================
    # Prepare Methods — Conversations
    # =========================================================================

    def _prepare_list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50,
        offset: int = 0, include_deleted: bool = False,
        from_date: Optional[str] = None, to_date: Optional[str] = None,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "limit": limit,
            "offset": offset,
            "include_deleted": include_deleted,
        }
        if user_id:
            params["user_id"] = user_id
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        return "conversations.list_conversations", params

    def _prepare_get_conversation(self, conversation_id: str) -> tuple:
        return "conversations.get_conversation", {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
        }

    def _prepare_get_messages(
        self, conversation_id: str, limit: int = 100,
        offset: int = 0, include_deleted: bool = False,
    ) -> tuple:
        return "conversations.get_messages", {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
            "limit": limit,
            "offset": offset,
            "include_deleted": include_deleted,
        }

    def _prepare_create_message(
        self, conversation_id: str, message_id: str, role: str, content: str,
        user_id: Optional[str] = None, tokens_used: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "role": role,
            "content": content,
            "tokens_used": tokens_used,
        }
        if user_id:
            payload["user_id"] = user_id
        if context:
            payload["context"] = context
        return "conversations.create_message", payload

    def _prepare_update_conversation(
        self, conversation_id: str,
        title: Optional[str] = None, user_id: Optional[str] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
        }
        if title is not None:
            payload["title"] = title
        if user_id is not None:
            payload["user_id"] = user_id
        return "conversations.update_conversation", payload

    def _prepare_delete_conversation(self, conversation_id: str, hard_delete: bool = False) -> tuple:
        payload = {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
        }
        if hard_delete:
            payload["hard_delete"] = True
        return "conversations.delete_conversation", payload

    def _prepare_delete_message(self, conversation_id: str, message_id: str) -> tuple:
        return "conversations.delete_message", {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
        }

    def _prepare_get_sync_stats(self) -> tuple:
        return "conversations.get_sync_stats", {"tenant_id": self.tenant_id}

    def _prepare_get_message_events(
        self, conversation_id: str, message_id: Optional[str] = None,
        event_types: Optional[list] = None, limit: int = 100, offset: int = 0,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "conversation_id": conversation_id,
            "limit": limit,
            "offset": offset,
        }
        if message_id:
            params["message_id"] = message_id
        if event_types:
            params["event_types"] = ",".join(event_types) if isinstance(event_types, list) else event_types
        return "conversations.get_message_events", params

    def _prepare_get_tool_execution_stats(
        self, conversation_id: Optional[str] = None,
        from_date: Optional[str] = None, to_date: Optional[str] = None,
    ) -> tuple:
        params: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if conversation_id:
            params["conversation_id"] = conversation_id
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        return "conversations.get_tool_execution_stats", params

    # =========================================================================
    # Prepare Methods — Users & MCP Servers
    # =========================================================================

    def _prepare_register_user(
        self, user_id: str, display_name: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        locale: Optional[str] = None,
        timezone: Optional[str] = None,
        user_role: Optional[str] = None,
        email: Optional[str] = None,
        registered_by: Optional[str] = None,
    ) -> tuple:
        params: Dict[str, Any] = {"tenant_id": self.tenant_id, "user_id": user_id}
        if display_name:
            params["display_name"] = display_name
        if custom_instructions:
            params["custom_instructions"] = custom_instructions
        if locale:
            params["locale"] = locale
        if timezone:
            params["timezone"] = timezone
        if user_role:
            params["user_role"] = user_role
        if email:
            params["email"] = email
        if registered_by:
            params["registered_by"] = registered_by
        return "users.register_user", params

    def _prepare_get_user(self, user_id: str) -> tuple:
        return "users.get_user", {"tenant_id": self.tenant_id, "user_id": user_id}

    def _prepare_get_user_auth_status(self, user_id: str) -> tuple:
        return "users.get_user_auth_status", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_add_user_mcp_server(
        self, user_id: str, server_name: str, endpoint_url: str,
        transport_type: str = "SSE", auth_type: str = "OAuth",
        oauth_client_id: Optional[str] = None,
        oauth_client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_in: int = 3600,
        api_key: Optional[str] = None,
        api_key_header: str = "Authorization",
        allowed_tools: Optional[list] = None,
        blocked_tools: Optional[list] = None,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "server_name": server_name,
            "endpoint_url": endpoint_url,
            "transport_type": transport_type,
            "auth_type": auth_type,
        }
        if oauth_client_id:
            params["oauth_client_id"] = oauth_client_id
        if oauth_client_secret:
            params["oauth_client_secret"] = oauth_client_secret
        if access_token:
            params["access_token"] = access_token
        if refresh_token:
            params["refresh_token"] = refresh_token
        if token_expires_in:
            params["token_expires_in"] = str(token_expires_in)
        if api_key:
            params["api_key"] = api_key
        if api_key_header:
            params["api_key_header"] = api_key_header
        if allowed_tools:
            params["allowed_tools"] = json.dumps(allowed_tools)
        if blocked_tools:
            params["blocked_tools"] = json.dumps(blocked_tools)
        return "users.add_user_mcp_server", params

    def _prepare_get_user_mcp_servers(self, user_id: str) -> tuple:
        return "users.get_user_mcp_servers", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_update_mcp_server_tokens(
        self, user_id: str, server_name: str, access_token: str,
        refresh_token: Optional[str] = None, token_expires_in: int = 3600,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "server_name": server_name,
            "access_token": access_token,
            "token_expires_in": str(token_expires_in),
        }
        if refresh_token:
            params["refresh_token"] = refresh_token
        return "users.update_mcp_server_tokens", params

    def _prepare_remove_user_mcp_server(self, user_id: str, server_name: str) -> tuple:
        return "users.remove_user_mcp_server", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "server_name": server_name,
        }

    def _prepare_list_users(
        self, status: Optional[str] = None, limit: int = 50,
        offset: int = 0, include_mcp_count: bool = True,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "limit": str(limit),
            "offset": str(offset),
            "include_mcp_count": str(include_mcp_count).lower(),
        }
        if status:
            params["status"] = status
        return "users.list_users", params

    def _prepare_update_user(
        self, user_id: str, display_name: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        locale: Optional[str] = None,
        timezone: Optional[str] = None,
        user_role: Optional[str] = None,
        email: Optional[str] = None,
        job_title: Optional[str] = None,
        department: Optional[str] = None,
        about: Optional[str] = None,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }
        if display_name is not None:
            params["display_name"] = display_name
        if custom_instructions is not None:
            params["custom_instructions"] = custom_instructions
        if locale is not None:
            params["locale"] = locale
        if timezone is not None:
            params["timezone"] = timezone
        if user_role is not None:
            params["user_role"] = user_role
        if email is not None:
            params["email"] = email
        if job_title is not None:
            params["job_title"] = job_title
        if department is not None:
            params["department"] = department
        if about is not None:
            params["about"] = about
        return "users.update_user", params

    def _prepare_deregister_user(self, user_id: str) -> tuple:
        return "users.deregister_user", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_get_user_limit_status(self) -> tuple:
        return "users.get_user_limit_status", {"tenant_id": self.tenant_id}

    def _prepare_suspend_user(self, user_id: str) -> tuple:
        return "users.suspend_user", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_revoke_user(self, user_id: str) -> tuple:
        return "users.revoke_user", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    # =========================================================================
    # Prepare Methods — Workflows
    # =========================================================================

    def _prepare_create_workflow(
        self, workflow_name: str, graph_json: Optional[str] = None,
        description: str = "", default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
        error_strategy: str = "fail_fast", timeout_seconds: int = 600,
    ) -> tuple:
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
        return "workflows.create_workflow", payload

    def _prepare_get_workflow(
        self, name: Optional[str] = None, workflow_name: Optional[str] = None,
    ) -> tuple:
        params: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if name:
            params["name"] = name
        if workflow_name:
            params["workflow_name"] = workflow_name
        return "workflows.get_workflow", params

    def _prepare_update_workflow(
        self, name: str, graph_json: Optional[str] = None,
        workflow_name: Optional[str] = None, description: Optional[str] = None,
        status: Optional[str] = None, default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
        error_strategy: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_node_executions: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> tuple:
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
        return "workflows.update_workflow", payload

    def _prepare_delete_workflow(self, name: str) -> tuple:
        return "workflows.delete_workflow", {
            "tenant_id": self.tenant_id,
            "name": name,
        }

    def _prepare_list_workflows(
        self, status: Optional[str] = None,
        page: int = 0, page_size: int = 20,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "page": str(page),
            "page_size": str(page_size),
        }
        if status:
            params["status"] = status
        return "workflows.list_workflows", params

    def _prepare_execute_workflow(
        self, name: str, input_data: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
        }
        if input_data:
            payload["input_data"] = input_data
        if user_id:
            payload["user_id"] = user_id
        return "workflows.execute_workflow", payload

    def _prepare_cancel_workflow_run(self, run_name: str) -> tuple:
        return "workflows.cancel_run", {
            "tenant_id": self.tenant_id,
            "run_name": run_name,
        }

    def _prepare_get_workflow_run(self, run_name: str) -> tuple:
        return "workflows.get_run", {
            "tenant_id": self.tenant_id,
            "run_name": run_name,
        }

    def _prepare_list_workflow_runs(
        self, workflow_name: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 0, page_size: int = 20,
    ) -> tuple:
        params: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "page": str(page),
            "page_size": str(page_size),
        }
        if workflow_name:
            params["workflow_name"] = workflow_name
        if status:
            params["status"] = status
        return "workflows.list_runs", params

    def _prepare_set_workflow_schedule(
        self, name: str, cron_expression: str,
        timezone: str = "UTC", enabled: bool = True,
        default_input: Optional[str] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
            "cron_expression": cron_expression,
            "timezone": timezone,
            "enabled": enabled,
        }
        if default_input is not None:
            payload["default_input"] = default_input
        return "workflows.set_schedule", payload

    def _prepare_validate_workflow_graph(self, graph_json: str) -> tuple:
        return "workflows.validate_graph", {
            "tenant_id": self.tenant_id,
            "graph_json": graph_json,
        }

    def _prepare_test_workflow_node(
        self, node_json: str, input_text: str = "Test input",
        default_model_id: Optional[str] = None,
        default_user_id: Optional[str] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "node_json": node_json,
            "input_text": input_text,
        }
        if default_model_id:
            payload["default_model_id"] = default_model_id
        if default_user_id:
            payload["default_user_id"] = default_user_id
        return "workflows.test_node", payload

    def _prepare_resolve_workflow_tools(
        self, user_id: str, tool_directives: List[Dict[str, Any]],
    ) -> tuple:
        return "workflows.resolve_workflow_tools", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "tool_directives": json.dumps(tool_directives),
        }

    def _prepare_run_workflow_node(
        self, name: str, node_id: str, input_text: str = "Test input",
        user_id: Optional[str] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
            "node_id": node_id,
            "input_text": input_text,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        return "workflows.run_workflow_node", payload

    # =========================================================================
    # Prepare Methods — Workflow Templates
    # =========================================================================

    def _prepare_export_workflow(
        self, name: str, template_name: Optional[str] = None,
        category: str = "General", save_as_template: bool = False,
        is_public: bool = False,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
            "category": category,
            "save_as_template": save_as_template,
            "is_public": is_public,
        }
        if template_name:
            payload["template_name"] = template_name
        return "workflows.export_workflow", payload

    def _prepare_list_templates(
        self, category: Optional[str] = None, search: Optional[str] = None,
        user_id: Optional[str] = None, sort_by: Optional[str] = None,
        featured_only: bool = False, min_rating: Optional[float] = None,
        page: int = 0, page_size: int = 20,
    ) -> tuple:
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
        if sort_by:
            params["sort_by"] = sort_by
        if featured_only:
            params["featured_only"] = "1"
        if min_rating is not None:
            params["min_rating"] = min_rating
        return "workflows.list_templates", params

    def _prepare_get_template(
        self, template_name: Optional[str] = None,
        name: Optional[str] = None, user_id: Optional[str] = None,
    ) -> tuple:
        params: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if name:
            params["name"] = name
        elif template_name:
            params["template_name"] = template_name
        if user_id:
            params["user_id"] = user_id
        return "workflows.get_template", params

    def _prepare_import_template(
        self, user_id: str, template_name: Optional[str] = None,
        template_json: Optional[str] = None,
        workflow_name: Optional[str] = None,
        variables: Optional[str] = None,
        default_user_id: Optional[str] = None,
        default_model_id: Optional[str] = None,
    ) -> tuple:
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
        return "workflows.import_template", payload

    def _prepare_update_template(
        self, name: str, template_name: Optional[str] = None,
        description: Optional[str] = None, category: Optional[str] = None,
        is_public: Optional[bool] = None, is_published: Optional[bool] = None,
        graph_json: Optional[str] = None,
        variables_schema: Optional[str] = None,
        default_variables: Optional[str] = None,
        default_model_id: Optional[str] = None,
        error_strategy: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        tags: Optional[str] = None,
    ) -> tuple:
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
        return "workflows.update_template", payload

    # =========================================================================
    # Prepare Methods — GDPR / Privacy
    # =========================================================================

    def _prepare_export_user_data(self, user_id: str) -> tuple:
        return "gdpr.export_user_data", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_erase_user_data(self, user_id: str) -> tuple:
        return "gdpr.erase_user_data", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
        }

    def _prepare_rectify_user_data(self, user_id: str, updates: dict) -> tuple:
        import json
        return "gdpr.rectify_user_data", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "updates": json.dumps(updates) if isinstance(updates, dict) else updates,
        }

    def _prepare_restrict_user_processing(self, user_id: str, restrict: bool = True) -> tuple:
        return "gdpr.restrict_user_processing", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "restrict": restrict,
        }

    def _prepare_update_user_consent(self, user_id: str, consent_type: str, granted: bool = True) -> tuple:
        return "gdpr.update_user_consent", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
        }

    def _prepare_get_tenant_privacy_config(self) -> tuple:
        return "gdpr.get_tenant_privacy_config", {
            "tenant_id": self.tenant_id,
        }

    def _prepare_update_tenant_privacy_config(self, config: dict) -> tuple:
        import json
        return "gdpr.update_tenant_privacy_config", {
            "tenant_id": self.tenant_id,
            "config": json.dumps(config) if isinstance(config, dict) else config,
        }

    def _prepare_delete_template(self, name: str) -> tuple:
        return "workflows.delete_template", {
            "tenant_id": self.tenant_id,
            "name": name,
        }

    def _prepare_upload_template(
        self, user_id: str, is_public: bool = False, is_published: bool = True,
    ) -> tuple:
        return "workflows.upload_template", {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "is_public": "1" if is_public else "0",
            "is_published": "1" if is_published else "0",
        }

    def _prepare_rate_template(
        self, name: str, user_id: str, rating: int,
        review: Optional[str] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "name": name,
            "user_id": user_id,
            "rating": rating,
        }
        if review:
            payload["review"] = review
        return "workflows.rate_template", payload

    def _prepare_download_template(self, name: str) -> tuple:
        return "workflows.download_template", {
            "tenant_id": self.tenant_id,
            "name": name,
        }

    # --- Heartbeat & Notifications ---

    def _prepare_heartbeat(
        self,
        faco_version: Optional[str] = None,
        fac_version: Optional[str] = None,
        frappe_version: Optional[str] = None,
        erpnext_version: Optional[str] = None,
        python_version: Optional[str] = None,
    ) -> tuple:
        payload: Dict[str, Any] = {"tenant_id": self.tenant_id}
        if faco_version:
            payload["faco_version"] = faco_version
        if fac_version:
            payload["fac_version"] = fac_version
        if frappe_version:
            payload["frappe_version"] = frappe_version
        if erpnext_version is not None:
            payload["erpnext_version"] = erpnext_version
        if python_version:
            payload["python_version"] = python_version
        return "heartbeat.heartbeat", payload

    def _prepare_dismiss_notification(
        self, notification_id: str, user_id: str,
    ) -> tuple:
        return "heartbeat.dismiss_notification", {
            "tenant_id": self.tenant_id,
            "notification_id": notification_id,
            "user_id": user_id,
        }

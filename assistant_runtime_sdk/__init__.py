# Assistant Runtime SDK - Python SDK for Assistant Runtime
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Assistant Runtime SDK - Python SDK for Assistant Runtime.

A framework-agnostic Python client for integrating with Assistant Runtime APIs.
Supports both synchronous (requests) and asynchronous (aiohttp) usage.

Quick Start:
    >>> from assistant_runtime_sdk import AssistantRuntimeClient
    >>>
    >>> client = AssistantRuntimeClient(
    ...     tenant_id="your-tenant-id",
    ...     tenant_secret="your-secret",
    ...     ar_url="https://ar.example.com"
    ... )
    >>>
    >>> # List available models
    >>> models = client.list_available_models()
    >>>
    >>> # Stream a chat response
    >>> for event in client.stream_chat("session-1", "Hello!", "user@example.com"):
    ...     if event["event"] == "stream_chunk":
    ...         print(event["data"].get("content", ""), end="")

Async Usage:
    >>> from assistant_runtime_sdk import AsyncAssistantRuntimeClient
    >>> import asyncio
    >>>
    >>> async def main():
    ...     async with AsyncAssistantRuntimeClient("tenant-id", "secret") as client:
    ...         async for event in client.stream_chat("session-1", "Hi!", "user@example.com"):
    ...             print(event)
    >>>
    >>> asyncio.run(main())

Standalone Functions:
    >>> from assistant_runtime_sdk import get_terms, register_tenant
    >>>
    >>> # Get current terms (no auth required)
    >>> terms = get_terms("https://ar.example.com")
    >>>
    >>> # Register a new tenant
    >>> result = register_tenant(
    ...     ar_url="https://ar.example.com",
    ...     site_url="https://mysite.frappe.cloud",
    ...     terms_accepted=True,
    ...     terms_version="1.0",
    ...     accepted_by="admin@example.com"
    ... )

Backwards Compatibility:
    The old FACL* class names are still available as aliases:
    - FACLClient -> AssistantRuntimeClient
    - AsyncFACLClient -> AsyncAssistantRuntimeClient
    - FACLError -> ARError (and all other exceptions)
"""

__version__ = "0.1.0"
__author__ = "Paul Clinton"
__license__ = "AGPL-3.0"

# =============================================================================
# Core Client Classes
# =============================================================================

from .client import AssistantRuntimeClient, get_terms, register_tenant

# Async client - import lazily to avoid requiring aiohttp
# Skill providers - import lazily to avoid requiring strands-agents
def __getattr__(name: str):
    """Lazy import for optional dependencies and backwards compatibility."""
    # New names
    if name == "AsyncAssistantRuntimeClient":
        from .async_client import AsyncAssistantRuntimeClient
        return AsyncAssistantRuntimeClient
    if name == "SkillProvider":
        from .skills import SkillProvider
        return SkillProvider
    if name == "AsyncSkillProvider":
        from .skills import AsyncSkillProvider
        return AsyncSkillProvider

    # Backwards compatibility aliases for old FACL names
    if name == "FACLClient":
        from .client import AssistantRuntimeClient
        return AssistantRuntimeClient
    if name == "AsyncFACLClient":
        from .async_client import AsyncAssistantRuntimeClient
        return AsyncAssistantRuntimeClient

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# =============================================================================
# Exceptions (with backwards compatibility aliases)
# =============================================================================

from .exceptions import (
    # New names
    ARError,
    ARAuthenticationError,
    ARRateLimitError,
    ARStreamError,
    ARConfigurationError,
    ARAPIError,
    ARTimeoutError,
    ARConnectionError,
    ARBillingUnavailableError,
    # Backwards compatibility aliases
    FACLError,
    FACLAuthenticationError,
    FACLRateLimitError,
    FACLStreamError,
    FACLConfigurationError,
    FACLAPIError,
    FACLTimeoutError,
    FACLConnectionError,
    FACLBillingUnavailableError,
)

# =============================================================================
# Utilities
# =============================================================================

from .auth import generate_signature, verify_signature, get_signature_header
from .streaming import SSEEventType, parse_sse_line, parse_sse_stream

# =============================================================================
# Type Definitions
# =============================================================================

from .types import (
    # Model types
    ModelInfo,
    AutoModeInfo,
    ModelsResponse,
    # Streaming types
    StreamEvent,
    StreamStartData,
    StreamChunkData,
    StreamCompleteData,
    ModelFallbackData,
    RateLimitedData,
    ToolCallStartData,
    ToolCallResultData,
    ApprovalRequiredData,
    # Conversation types
    ConversationInfo,
    MessageInfo,
    PaginationInfo,
    ConversationsResponse,
    MessagesResponse,
    # User types
    UserInfo,
    MCPServerInfo,
    UserAuthStatus,
    # Billing types
    UsageDashboard,
    UsageHistoryEntry,
    UsageHistoryResponse,
    # Tenant types
    TenantInfo,
    TermsInfo,
    # Prompt types
    PromptArgument,
    PromptInfo,
    PromptsResponse,
    # Document types
    DocumentInfo,
    DocumentDetailInfo,
    DocumentUploadResponse,
    DocumentDeleteResponse,
    StorageInfo,
    DocumentsListResponse,
)

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "__version__",
    # Core clients - new names
    "AssistantRuntimeClient",
    "AsyncAssistantRuntimeClient",
    # Core clients - backwards compatibility
    "FACLClient",
    "AsyncFACLClient",
    # Skill providers (for Strands Agent integration)
    "SkillProvider",
    "AsyncSkillProvider",
    # Standalone functions
    "get_terms",
    "register_tenant",
    # Exceptions - new names
    "ARError",
    "ARAuthenticationError",
    "ARRateLimitError",
    "ARStreamError",
    "ARConfigurationError",
    "ARAPIError",
    "ARTimeoutError",
    "ARConnectionError",
    "ARBillingUnavailableError",
    # Exceptions - backwards compatibility
    "FACLError",
    "FACLAuthenticationError",
    "FACLRateLimitError",
    "FACLStreamError",
    "FACLConfigurationError",
    "FACLAPIError",
    "FACLTimeoutError",
    "FACLConnectionError",
    "FACLBillingUnavailableError",
    # Auth utilities
    "generate_signature",
    "verify_signature",
    "get_signature_header",
    # Streaming utilities
    "SSEEventType",
    "parse_sse_line",
    "parse_sse_stream",
    # Types - Models
    "ModelInfo",
    "AutoModeInfo",
    "ModelsResponse",
    # Types - Streaming
    "StreamEvent",
    "StreamStartData",
    "StreamChunkData",
    "StreamCompleteData",
    "ModelFallbackData",
    "RateLimitedData",
    "ToolCallStartData",
    "ToolCallResultData",
    "ApprovalRequiredData",
    # Types - Conversations
    "ConversationInfo",
    "MessageInfo",
    "PaginationInfo",
    "ConversationsResponse",
    "MessagesResponse",
    # Types - Users
    "UserInfo",
    "MCPServerInfo",
    "UserAuthStatus",
    # Types - Billing
    "UsageDashboard",
    "UsageHistoryEntry",
    "UsageHistoryResponse",
    # Types - Tenant
    "TenantInfo",
    "TermsInfo",
    # Types - Prompts
    "PromptArgument",
    "PromptInfo",
    "PromptsResponse",
    # Types - Documents
    "DocumentInfo",
    "DocumentDetailInfo",
    "DocumentUploadResponse",
    "DocumentDeleteResponse",
    "StorageInfo",
    "DocumentsListResponse",
]

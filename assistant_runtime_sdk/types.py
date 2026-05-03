# Assistant Runtime SDK - Type Definitions
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Type definitions for Assistant Runtime API responses.

Uses TypedDict for better IDE support and documentation.
"""

from typing import TypedDict, List, Optional, Any


# =============================================================================
# Model Types
# =============================================================================


class ModelInfo(TypedDict):
    """Information about an available AI model."""

    model_id: str
    display_name: str
    provider: str
    tier: str
    multiplier: float
    context_length: Optional[int]
    max_output_tokens: Optional[int]
    is_auto_eligible: Optional[bool]
    fallback_priority: Optional[int]


class AutoModeInfo(TypedDict):
    """Auto-mode configuration information."""

    enabled: bool
    description: str
    model_id: str
    fallback_chain_length: int


class ModelsResponse(TypedDict):
    """Response from list_available_models endpoint."""

    success: bool
    models: List[ModelInfo]
    max_tier_rank: float
    default_model: Optional[str]
    auto_mode: Optional[AutoModeInfo]


# =============================================================================
# Streaming Types
# =============================================================================


class StreamEvent(TypedDict):
    """A single SSE event from the streaming API."""

    event: str
    data: dict


class StreamStartData(TypedDict):
    """Data from stream_start event."""

    session_id: str
    message_id: str
    timestamp: int
    model_id: Optional[str]


class StreamChunkData(TypedDict):
    """Data from stream_chunk event."""

    content: str
    chunk_index: Optional[int]


class StreamCompleteData(TypedDict):
    """Data from stream_complete event."""

    full_response: str
    tokens_used: int
    tokens_actual: int
    model_id: str
    session_id: str
    message_id: str


class ModelFallbackData(TypedDict):
    """Data from model_fallback event (auto-mode)."""

    original: str
    selected: str
    provider: str
    tier: str
    fallback_attempted: bool


class RateLimitedData(TypedDict):
    """Data from rate_limited event."""

    error: str
    error_code: str
    retry_after: float
    models_checked: List[str]


class ToolCallStartData(TypedDict):
    """Data from tool_call_start event."""

    tool_name: str
    tool_id: str
    arguments: dict


class ToolCallResultData(TypedDict):
    """Data from tool_call_result event."""

    tool_id: str
    tool_name: str
    result: Any
    success: bool
    duration_ms: Optional[int]


class ApprovalRequiredData(TypedDict):
    """Data from approval_required event (HITL)."""

    tool_name: str
    tool_id: str
    arguments: dict
    reason: Optional[str]
    timeout_seconds: Optional[int]


# =============================================================================
# Conversation Types
# =============================================================================


class ConversationInfo(TypedDict):
    """Information about a conversation."""

    conversation_id: str
    title: Optional[str]
    user_id: Optional[str]
    created_at: str
    updated_at: str
    message_count: int
    total_tokens: int
    is_deleted: bool


class MessageInfo(TypedDict):
    """Information about a message."""

    message_id: str
    conversation_id: str
    role: str
    content: str
    user_id: Optional[str]
    tokens_used: int
    created_at: str
    is_deleted: bool


class PaginationInfo(TypedDict):
    """Pagination information."""

    total: int
    limit: int
    offset: int
    has_more: bool


class ConversationsResponse(TypedDict):
    """Response from list_conversations endpoint."""

    conversations: List[ConversationInfo]
    pagination: PaginationInfo


class MessagesResponse(TypedDict):
    """Response from get_messages endpoint."""

    messages: List[MessageInfo]
    pagination: PaginationInfo


# =============================================================================
# User Types
# =============================================================================


class UserInfo(TypedDict):
    """Information about a user."""

    user_id: str
    display_name: Optional[str]
    status: str
    custom_instructions: Optional[str]
    last_activity: Optional[str]
    mcp_server_count: int


class MCPServerInfo(TypedDict):
    """Information about an MCP server."""

    server_name: str
    endpoint_url: str
    transport_type: str
    auth_type: str
    status: str
    enabled: bool
    last_connected: Optional[str]
    token_expiry: Optional[str]
    error_message: Optional[str]


class UserAuthStatus(TypedDict):
    """User authentication status."""

    user_exists: bool
    user_status: Optional[str]
    has_mcp_servers: bool
    active_server_count: int
    servers_with_expired_tokens: List[str]
    ready_for_streaming: bool


class UserListItem(TypedDict):
    """User information for list responses."""

    user_id: str
    display_name: Optional[str]
    status: str
    custom_instructions: Optional[str]
    last_activity: Optional[str]
    created_at: Optional[str]
    mcp_server_count: Optional[int]


class UsersListResponse(TypedDict):
    """Response from list_users endpoint."""

    users: List[UserListItem]
    pagination: PaginationInfo


class UserUpdateResponse(TypedDict):
    """Response from update_user endpoint."""

    success: bool
    user_id: str
    message: str


class UserDeregisterResponse(TypedDict):
    """Response from deregister_user endpoint."""

    success: bool
    user_id: str
    deleted_mcp_servers: int
    message: str


class UserLimitStatus(TypedDict):
    """User limit status for a tenant."""

    plan: str
    max_users: int
    active_users: int
    remaining: int
    is_unlimited: bool


# =============================================================================
# Billing Types
# =============================================================================


class UsageDashboard(TypedDict):
    """Usage dashboard data."""

    plan: str
    status: str
    payment_status: str
    quota: int
    used: int
    remaining: int
    usage_percentage: float
    billing_cycle_start: str
    next_billing_date: Optional[str]
    currency: str
    warnings: dict


class UsageHistoryEntry(TypedDict):
    """Single day's usage history."""

    date: str
    tokens_used: int
    tokens_actual: int


class UsageHistoryResponse(TypedDict):
    """Response from get_usage_history endpoint."""

    history: List[UsageHistoryEntry]


# =============================================================================
# Gateway Types
# =============================================================================


class GatewayPlanPricing(TypedDict):
    """Pricing for a single plan on a gateway."""

    monthly: Optional[float]
    annual: Optional[float]


class PlanPricing(TypedDict):
    """Gateway-specific plan pricing with currency."""

    currency: str  # "USD" or "INR"
    monthly: Optional[float]
    annual: Optional[float]


class PlanPricingByGateway(TypedDict):
    """Plan pricing organized by gateway."""

    stripe: PlanPricing
    razorpay: PlanPricing


class PlanInfo(TypedDict):
    """Information about a subscription plan with gateway-specific pricing."""

    name: str
    quota: int  # Monthly token quota (-1 for unlimited)
    max_tier_rank: float
    max_users: int  # -1 for unlimited
    features: List[str]
    pricing: PlanPricingByGateway


class PlanComparisonResponse(TypedDict):
    """Response from get_plan_comparison endpoint."""

    plans: List[PlanInfo]


class AvailablePlanInfo(TypedDict):
    """Plan information for upgrade/downgrade options."""

    name: str
    action: str  # "current", "upgrade", or "downgrade"
    quota: int
    max_tier_rank: float
    max_users: int
    features: List[str]
    pricing: PlanPricingByGateway


class GatewayInfo(TypedDict):
    """Information about a payment gateway."""

    name: str  # "stripe" or "razorpay"
    display_name: str
    currency: str  # "USD" or "INR"
    currency_symbol: str  # "$" or "₹"
    description: str
    is_recommended: bool
    plans: dict  # Plan name -> GatewayPlanPricing


class AvailableGatewaysResponse(TypedDict):
    """Response from get_available_gateways endpoint."""

    gateways: List[GatewayInfo]
    recommended_gateway: Optional[str]
    tenant_country: str


class CheckoutResponse(TypedDict):
    """Response from initiate_checkout endpoint."""

    checkout_url: str
    session_id: str
    gateway: str  # "stripe" or "razorpay"


class UpgradePlanResponse(TypedDict):
    """Response from upgrade_plan endpoint."""

    success: bool
    checkout_url: Optional[str]
    message: str


# =============================================================================
# Tenant Types
# =============================================================================


class TenantInfo(TypedDict):
    """Tenant information."""

    tenant_id: str
    site_url: str
    status: str
    subscription: dict
    terms_accepted: bool
    terms_version: Optional[str]


class TermsInfo(TypedDict):
    """Terms and conditions information."""

    version: str
    effective_date: str
    terms_of_service: str
    privacy_policy: str
    data_processing_agreement: str
    summary: str
    grace_period_days: int


# =============================================================================
# Prompt Types
# =============================================================================


class PromptArgument(TypedDict):
    """Prompt template argument definition."""

    name: str
    description: Optional[str]
    required: bool


class PromptInfo(TypedDict):
    """Information about a prompt template."""

    name: str
    title: Optional[str]
    description: Optional[str]
    arguments: List[PromptArgument]
    server: str


class PromptsResponse(TypedDict):
    """Response from list_prompts endpoint."""

    prompts: List[PromptInfo]
    servers_queried: List[str]
    errors: List[str]


# =============================================================================
# Document Types
# =============================================================================


class DocumentInfo(TypedDict):
    """Summary info for a RAG document."""

    document_id: str
    file_name: str
    file_size_mb: float
    document_type: str
    embedding_status: str
    total_chunks: int
    created_at: Optional[str]
    processed_at: Optional[str]
    visibility: str
    uploaded_by: str
    is_owner: bool


class DocumentDetailInfo(TypedDict):
    """Detailed info including processing errors."""

    document_id: str
    file_name: str
    file_size_mb: float
    document_type: str
    embedding_status: str
    total_chunks: int
    created_at: Optional[str]
    processed_at: Optional[str]
    processing_error: Optional[str]
    visibility: str
    uploaded_by: str
    shared_with: Optional[List[dict]]


class DocumentUploadResponse(TypedDict):
    """Response from upload_document."""

    status: str
    document_id: str
    file_name: str
    file_size_mb: float
    visibility: str
    message: str


class DocumentAccessUpdateResponse(TypedDict):
    """Response from update_document_access."""

    status: str
    document_id: str
    visibility: str
    shared_with: List[str]


class DocumentDeleteResponse(TypedDict):
    """Response from delete_document."""

    status: str
    document_id: str
    file_size_mb: float


class StorageInfo(TypedDict):
    """Storage quota and usage stats."""

    quota_mb: float  # -1 for unlimited
    used_mb: float
    available_mb: float  # -1 if unlimited
    usage_percentage: float
    document_count: int


class DocumentsListResponse(TypedDict):
    """Response from list_documents."""

    documents: List[DocumentInfo]
    pagination: PaginationInfo
    storage: StorageInfo

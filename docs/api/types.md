# Type Definitions Reference

Complete reference for TypedDict definitions used by the Assistant Runtime SDK.

## Overview

The SDK uses Python's `TypedDict` for type hints, providing:

- IDE autocompletion
- Static type checking with mypy
- Self-documenting API responses

```python
from assistant_runtime_sdk import (
    ModelInfo,
    StreamEvent,
    ConversationInfo,
    # ... more types
)
```

---

## Model Types

### ModelInfo

Information about an available AI model.

```python
class ModelInfo(TypedDict):
    model_id: str              # Unique model identifier
    display_name: str          # Human-readable name
    provider: str              # Provider (anthropic, openai, gemini)
    tier: str                  # Tier name (Economy, Standard, Premium)
    multiplier: float          # Token cost multiplier
    context_length: Optional[int]     # Max context tokens
    max_output_tokens: Optional[int]  # Max output tokens
    is_auto_eligible: Optional[bool]  # Included in auto mode
    fallback_priority: Optional[int]  # Priority in fallback chain
```

**Example:**
```python
{
    "model_id": "claude-sonnet-4-20250514",
    "display_name": "Claude Sonnet 4",
    "provider": "anthropic",
    "tier": "Standard",
    "multiplier": 2.0,
    "context_length": 200000,
    "max_output_tokens": 64000,
    "is_auto_eligible": True,
    "fallback_priority": 10
}
```

### AutoModeInfo

Auto-mode configuration.

```python
class AutoModeInfo(TypedDict):
    enabled: bool              # Whether auto mode is available
    description: str           # Description of auto mode
    model_id: str              # Virtual model ID ("auto")
    fallback_chain_length: int # Number of models in chain
```

### ModelsResponse

Response from `list_available_models()`.

```python
class ModelsResponse(TypedDict):
    success: bool
    models: List[ModelInfo]
    max_tier_multiplier: float
    default_model: Optional[str]
    auto_mode: Optional[AutoModeInfo]
```

---

## Streaming Types

### StreamEvent

A single SSE event.

```python
class StreamEvent(TypedDict):
    event: str   # Event type name
    data: dict   # Event-specific data
```

### StreamStartData

Data from `stream_start` event.

```python
class StreamStartData(TypedDict):
    session_id: str
    message_id: str
    timestamp: int
    model_id: Optional[str]
```

### StreamChunkData

Data from `stream_chunk` event.

```python
class StreamChunkData(TypedDict):
    content: str                  # Text content
    chunk_index: Optional[int]    # Chunk sequence number
```

### StreamCompleteData

Data from `stream_complete` event.

```python
class StreamCompleteData(TypedDict):
    full_response: str    # Complete response text
    tokens_used: int      # Billable tokens
    tokens_actual: int    # Actual tokens (before multiplier)
    model_id: str         # Model that generated response
    session_id: str
    message_id: str
```

### ModelFallbackData

Data from `model_fallback` event (auto mode).

```python
class ModelFallbackData(TypedDict):
    original: str          # Requested model ("auto")
    selected: str          # Actually selected model
    provider: str          # Provider of selected model
    tier: str              # Tier of selected model
    fallback_attempted: bool  # True if primary was unavailable
```

### RateLimitedData

Data from `rate_limited` event.

```python
class RateLimitedData(TypedDict):
    error: str
    error_code: str
    retry_after: float      # Seconds to wait
    models_checked: List[str]  # Models that were rate limited
```

### ToolCallStartData

Data from `tool_call_start` event.

```python
class ToolCallStartData(TypedDict):
    tool_name: str
    tool_id: str
    arguments: dict
```

### ToolCallResultData

Data from `tool_call_result` event.

```python
class ToolCallResultData(TypedDict):
    tool_id: str
    tool_name: str
    result: Any
    success: bool
    duration_ms: Optional[int]
```

### ApprovalRequiredData

Data from `approval_required` event (HITL).

```python
class ApprovalRequiredData(TypedDict):
    tool_name: str
    tool_id: str
    arguments: dict
    reason: Optional[str]
    timeout_seconds: Optional[int]
```

---

## Conversation Types

### ConversationInfo

Information about a conversation.

```python
class ConversationInfo(TypedDict):
    conversation_id: str
    title: Optional[str]
    user_id: Optional[str]
    created_at: str          # ISO 8601 timestamp
    updated_at: str
    message_count: int
    total_tokens: int
    is_deleted: bool
```

### MessageInfo

Information about a message.

```python
class MessageInfo(TypedDict):
    message_id: str
    conversation_id: str
    role: str               # "user" or "assistant"
    content: str
    user_id: Optional[str]
    tokens_used: int
    created_at: str
    is_deleted: bool
```

### PaginationInfo

Pagination metadata.

```python
class PaginationInfo(TypedDict):
    total: int      # Total items
    limit: int      # Items per page
    offset: int     # Current offset
    has_more: bool  # More items available
```

### ConversationsResponse

Response from `list_conversations()`.

```python
class ConversationsResponse(TypedDict):
    conversations: List[ConversationInfo]
    pagination: PaginationInfo
```

### MessagesResponse

Response from `get_messages()`.

```python
class MessagesResponse(TypedDict):
    messages: List[MessageInfo]
    pagination: PaginationInfo
```

---

## User Types

### UserInfo

Information about a user.

```python
class UserInfo(TypedDict):
    user_id: str
    display_name: Optional[str]
    status: str                     # "active", "inactive"
    custom_instructions: Optional[str]
    last_activity: Optional[str]
    mcp_server_count: int
```

### MCPServerInfo

Information about an MCP server.

```python
class MCPServerInfo(TypedDict):
    server_name: str
    endpoint_url: str
    transport_type: str      # "SSE" or "STDIO"
    auth_type: str           # "OAuth", "API_KEY", "None"
    status: str              # "connected", "disconnected", "error"
    enabled: bool
    last_connected: Optional[str]
    token_expiry: Optional[str]
    error_message: Optional[str]
```

### UserAuthStatus

User authentication status.

```python
class UserAuthStatus(TypedDict):
    user_exists: bool
    user_status: Optional[str]
    has_mcp_servers: bool
    active_server_count: int
    servers_with_expired_tokens: List[str]
    ready_for_streaming: bool
```

---

## Billing Types

### UsageDashboard

Usage dashboard data.

```python
class UsageDashboard(TypedDict):
    plan: str                    # Plan name (e.g. "Free", "Team")
    status: str                  # "Active", "PastDue", "Cancelled"
    payment_status: str          # "active", "past_due", "unpaid", "cancelled"
    credit_quota: int            # Monthly credit quota (-1 = unlimited)
    credits_used: float          # Credits consumed this period
    remaining: float             # Credits remaining (-1 = unlimited)
    usage_percentage: float      # Percentage used (0-100)
    credit_balance: float        # Prepaid credit balance
    billing_cycle_start: str
    next_billing_date: Optional[str]
    currency: str                # "USD", "INR", etc.
    billing_unit: str            # Always "credits"
    warnings: dict               # Warning flags
```

**Warnings dict:**
```python
{
    "approaching_limit": bool,  # >80% used
    "limit_reached": bool,      # 100% used
    "payment_failed": bool      # Payment issue
}
```

### UsageHistoryEntry

Single day's usage.

```python
class UsageHistoryEntry(TypedDict):
    date: str           # "2025-01-15"
    tokens_used: int    # Billable tokens
    tokens_actual: int  # Actual tokens
```

### UsageHistoryResponse

Response from `get_usage_history()`.

```python
class UsageHistoryResponse(TypedDict):
    history: List[UsageHistoryEntry]
```

---

## Tenant Types

### TenantInfo

Tenant information.

```python
class TenantInfo(TypedDict):
    tenant_id: str
    site_url: str
    status: str              # "active", "suspended"
    subscription: dict       # Subscription details
    terms_accepted: bool
    terms_version: Optional[str]
```

### TermsInfo

Terms and conditions information.

```python
class TermsInfo(TypedDict):
    version: str
    effective_date: str
    terms_of_service: str    # Full ToS text
    privacy_policy: str      # Full privacy policy
    data_processing_agreement: str
    summary: str             # Brief summary
    grace_period_days: int   # Days to accept new terms
```

---

## Prompt Types

### PromptArgument

Prompt template argument definition.

```python
class PromptArgument(TypedDict):
    name: str
    description: Optional[str]
    required: bool
```

### PromptInfo

Information about a prompt template.

```python
class PromptInfo(TypedDict):
    name: str                      # Prompt identifier
    title: Optional[str]           # Display title
    description: Optional[str]     # Prompt description
    arguments: List[PromptArgument]
    server: str                    # MCP server name
```

### PromptsResponse

Response from `list_prompts()`.

```python
class PromptsResponse(TypedDict):
    prompts: List[PromptInfo]
    servers_queried: List[str]
    errors: List[str]        # Errors from specific servers
```

---

## Using Types

### Type Checking

```python
from assistant_runtime_sdk import AssistantRuntimeClient, ModelInfo

def process_model(model: ModelInfo) -> str:
    """Type-safe model processing."""
    return f"{model['display_name']} ({model['provider']})"

client = AssistantRuntimeClient(tenant_id="...", tenant_secret="...")
response = client.list_available_models()

if response:
    for model in response["models"]:
        print(process_model(model))
```

### With mypy

```bash
# Install mypy
pip install mypy

# Run type checking
mypy my_ar_app.py
```

### IDE Support

TypedDict provides excellent IDE support:

```python
# VS Code / PyCharm will autocomplete:
model["display_name"]  # ✓ Autocomplete works
model["invalid_key"]   # ✗ Warning from IDE
```

## See Also

- [AssistantRuntimeClient Reference](client.md)
- [Streaming Guide](../guides/streaming.md)
- [Python TypedDict Documentation](https://docs.python.org/3/library/typing.html#typing.TypedDict)

# AssistantRuntimeClient API Reference

Complete API reference for the synchronous `AssistantRuntimeClient` class.

## Class: AssistantRuntimeClient

```python
from assistant_runtime_sdk import AssistantRuntimeClient
```

### Constructor

```python
AssistantRuntimeClient(
    tenant_id: str,
    tenant_secret: str,
    ar_url: str = "https://ar.example.com",
    logger: Optional[logging.Logger] = None,
    timeout: float = 30.0
)
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tenant_id` | str | Yes | - | Unique tenant identifier from Assistant Runtime |
| `tenant_secret` | str | Yes | - | HMAC secret for request signing |
| `ar_url` | str | No | `https://ar.example.com` | Base URL of Assistant Runtime server |
| `logger` | Logger | No | None | Custom logger instance |
| `timeout` | float | No | 30.0 | Default request timeout in seconds |

**Example:**

```python
client = AssistantRuntimeClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-secret",
    ar_url="https://ar.example.com",
    timeout=60.0
)
```

---

## Streaming API

### stream_chat()

Stream a chat response from Assistant Runtime.

```python
def stream_chat(
    self,
    session_id: str,
    message: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
) -> Generator[Dict[str, Any], None, None]
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | str | Yes | Conversation session identifier |
| `message` | str | Yes | User's message to send |
| `user_id` | str | Yes | User identifier |
| `context` | dict | No | Page context for the AI |
| `model_id` | str | No | Model ID or "auto" for auto-selection |

**Yields:** `Dict[str, Any]` - SSE events with `event` and `data` keys

**Events:**

| Event | Description |
|-------|-------------|
| `stream_start` | Stream initialized |
| `stream_chunk` | Content chunk received |
| `stream_complete` | Stream finished successfully |
| `stream_error` | Error occurred |
| `thinking` | AI reasoning content |
| `tool_call_start` | Tool execution starting |
| `tool_call_result` | Tool execution complete |
| `approval_required` | Human approval needed |
| `tool_cancelled` | Tool was rejected |
| `model_fallback` | Auto mode selected model |
| `rate_limited` | All models rate limited |

**Example:**

```python
for event in client.stream_chat(
    session_id="session-123",
    message="Hello!",
    user_id="user@example.com",
    model_id="auto"
):
    if event["event"] == "stream_chunk":
        print(event["data"].get("content", ""), end="")
    elif event["event"] == "stream_complete":
        print(f"\nTokens: {event['data'].get('tokens_used')}")
```

---

## Model API

### list_available_models()

List available AI models for the tenant's subscription tier.

```python
def list_available_models(self) -> Optional[Dict[str, Any]]
```

**Returns:** `ModelsResponse` TypedDict or None on error

```python
{
    "success": True,
    "models": [
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
    ],
    "max_tier_multiplier": 2.0,
    "default_model": "claude-sonnet-4-20250514",
    "auto_mode": {
        "enabled": True,
        "description": "Automatic model selection",
        "model_id": "auto",
        "fallback_chain_length": 5
    }
}
```

### set_preferred_model()

Set the preferred AI model for the tenant.

```python
def set_preferred_model(self, model_id: str) -> bool
```

**Parameters:**
- `model_id`: The model ID to set as preferred

**Returns:** `True` if successful, `False` otherwise

---

## Tenant API

### get_tenant_info()

Get tenant information including subscription status.

```python
def get_tenant_info(self) -> Optional[Dict[str, Any]]
```

**Returns:** `TenantInfo` TypedDict

```python
{
    "tenant_id": "your-tenant-id",
    "site_url": "https://yoursite.frappe.cloud",
    "status": "active",
    "subscription": {
        "plan": "standard",
        "status": "active",
        "current_period_end": "2025-02-01"
    },
    "terms_accepted": True,
    "terms_version": "1.0"
}
```

### accept_terms()

Accept or re-accept Terms and Conditions.

```python
def accept_terms(
    self,
    terms_version: str,
    accepted_by: str
) -> Dict[str, Any]
```

**Parameters:**
- `terms_version`: Version of terms being accepted
- `accepted_by`: Email of person accepting

**Returns:** Confirmation dict

---

## Conversation API

### list_conversations()

List conversations for the tenant.

```python
def list_conversations(
    self,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False,
) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `user_id`: Filter by user (optional)
- `limit`: Maximum results (default 50)
- `offset`: Pagination offset
- `include_deleted`: Include soft-deleted conversations

**Returns:** `ConversationsResponse` TypedDict

```python
{
    "conversations": [
        {
            "conversation_id": "conv-123",
            "title": "Help with Python",
            "user_id": "user@example.com",
            "created_at": "2025-01-15T10:30:00Z",
            "updated_at": "2025-01-15T11:00:00Z",
            "message_count": 5,
            "total_tokens": 1500,
            "is_deleted": False
        }
    ],
    "pagination": {
        "total": 42,
        "limit": 50,
        "offset": 0,
        "has_more": False
    }
}
```

### get_conversation()

Get detailed conversation information.

```python
def get_conversation(
    self,
    conversation_id: str
) -> Optional[Dict[str, Any]]
```

### get_messages()

Get messages for a conversation.

```python
def get_messages(
    self,
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
) -> Optional[Dict[str, Any]]
```

**Returns:** `MessagesResponse` TypedDict

```python
{
    "messages": [
        {
            "message_id": "msg-123",
            "conversation_id": "conv-123",
            "role": "user",
            "content": "Hello!",
            "user_id": "user@example.com",
            "tokens_used": 10,
            "created_at": "2025-01-15T10:30:00Z",
            "is_deleted": False
        }
    ],
    "pagination": {...}
}
```

### create_message()

Create a new message in a conversation.

```python
def create_message(
    self,
    conversation_id: str,
    message_id: str,
    role: str,
    content: str,
    user_id: Optional[str] = None,
    tokens_used: int = 0,
) -> Dict[str, Any]
```

### update_conversation()

Update conversation metadata.

```python
def update_conversation(
    self,
    conversation_id: str,
    title: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]
```

### delete_conversation()

Soft delete a conversation.

```python
def delete_conversation(
    self,
    conversation_id: str
) -> Dict[str, Any]
```

### delete_message()

Soft delete a message.

```python
def delete_message(
    self,
    conversation_id: str,
    message_id: str
) -> Dict[str, Any]
```

---

## User API

### register_user()

Register a user with Assistant Runtime.

```python
def register_user(
    self,
    user_id: str,
    display_name: Optional[str] = None,
    custom_instructions: Optional[str] = None,
) -> Dict[str, Any]
```

**Parameters:**
- `user_id`: Unique user identifier (usually email)
- `display_name`: User's display name
- `custom_instructions`: Custom AI instructions for this user

**Returns:** `UserInfo` TypedDict

### get_user()

Get user details.

```python
def get_user(self, user_id: str) -> Optional[Dict[str, Any]]
```

**Returns:** `UserInfo` TypedDict

```python
{
    "user_id": "user@example.com",
    "display_name": "John Doe",
    "status": "active",
    "custom_instructions": "Be concise",
    "last_activity": "2025-01-15T10:30:00Z",
    "mcp_server_count": 2
}
```

### get_user_auth_status()

Check user authentication status and MCP readiness.

```python
def get_user_auth_status(self, user_id: str) -> Dict[str, Any]
```

**Returns:** `UserAuthStatus` TypedDict

```python
{
    "user_exists": True,
    "user_status": "active",
    "has_mcp_servers": True,
    "active_server_count": 2,
    "servers_with_expired_tokens": [],
    "ready_for_streaming": True
}
```

---

## MCP Server API

### add_user_mcp_server()

Add or update an MCP server for a user.

```python
def add_user_mcp_server(
    self,
    user_id: str,
    server_name: str,
    endpoint_url: str,
    transport_type: str = "SSE",
    auth_type: str = "OAuth",
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    token_expires_in: int = 3600,
) -> Dict[str, Any]
```

**Parameters:**
- `user_id`: User identifier
- `server_name`: Unique server name
- `endpoint_url`: MCP server endpoint URL
- `transport_type`: "SSE" or "STDIO"
- `auth_type`: "OAuth", "API_KEY", or "None"
- `access_token`: OAuth access token
- `refresh_token`: OAuth refresh token
- `token_expires_in`: Token expiry in seconds

### get_user_mcp_servers()

Get all MCP servers for a user.

```python
def get_user_mcp_servers(self, user_id: str) -> Dict[str, Any]
```

**Returns:**

```python
{
    "user_id": "user@example.com",
    "mcp_servers": [
        {
            "server_name": "erp-tools",
            "endpoint_url": "https://mcp.example.com/sse",
            "transport_type": "SSE",
            "auth_type": "OAuth",
            "status": "connected",
            "enabled": True,
            "last_connected": "2025-01-15T10:30:00Z",
            "token_expiry": "2025-01-15T14:30:00Z",
            "error_message": None
        }
    ]
}
```

### update_mcp_server_tokens()

Update OAuth tokens for an MCP server.

```python
def update_mcp_server_tokens(
    self,
    user_id: str,
    server_name: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    token_expires_in: int = 3600,
) -> Dict[str, Any]
```

### remove_user_mcp_server()

Remove an MCP server from a user.

```python
def remove_user_mcp_server(
    self,
    user_id: str,
    server_name: str
) -> Dict[str, Any]
```

---

## Billing API

### get_usage_dashboard()

Get comprehensive usage and billing data.

```python
def get_usage_dashboard(self) -> Optional[Dict[str, Any]]
```

**Returns:** `UsageDashboard` TypedDict

```python
{
    "plan": "standard",
    "status": "active",
    "payment_status": "paid",
    "quota": 1000000,
    "used": 250000,
    "remaining": 750000,
    "usage_percentage": 25.0,
    "billing_cycle_start": "2025-01-01",
    "next_billing_date": "2025-02-01",
    "currency": "USD",
    "warnings": {
        "approaching_limit": False,
        "limit_reached": False
    }
}
```

### get_usage_history()

Get historical usage data.

```python
def get_usage_history(self, days: int = 30) -> Optional[Dict[str, Any]]
```

**Returns:** `UsageHistoryResponse` TypedDict

```python
{
    "history": [
        {
            "date": "2025-01-15",
            "tokens_used": 50000,
            "tokens_actual": 45000
        }
    ]
}
```

### get_plan_comparison()

Get available subscription plans.

```python
def get_plan_comparison(self) -> Optional[Dict[str, Any]]
```

### initiate_checkout()

Create a checkout session for subscription.

```python
def initiate_checkout(
    self,
    plan: str,
    billing_cycle: str = "monthly"
) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `plan`: Plan name (e.g., "standard", "professional")
- `billing_cycle`: "monthly" or "yearly"

**Returns:** Checkout session details including redirect URL

### verify_checkout()

Verify payment completion.

```python
def verify_checkout(
    self,
    session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]
```

### upgrade_plan()

Upgrade subscription plan.

```python
def upgrade_plan(
    self,
    new_plan: str,
    billing_cycle: str = "monthly"
) -> Dict[str, Any]
```

### cancel_subscription()

Cancel subscription.

```python
def cancel_subscription(
    self,
    cancel_immediately: bool = False
) -> Dict[str, Any]
```

### get_payment_instrument()

Get the instrument on file for automatic payments.

```python
def get_payment_instrument(self) -> Optional[Dict[str, Any]]
```

**Returns:** the autopay instrument, plus an `update_mode` that tells the
caller what `update_payment_method()` will do next — `"settle"` (an unpaid
renewal exists), `"swap"` (nothing is owed), or `"portal"` (Stripe). The
shape is the same for both gateways; fields that only apply to Razorpay
(`mandate`, `max_amount`, `authorized_on`, `needs_reauth`, `vpa`, `bank`,
`card.issuer`) are `None` on Stripe rather than omitted.

```python
{
    "gateway": "razorpay",
    "autopay": {
        "mandate": "mandate_Ee5pAn9Sy1jaAA",
        "status": "active",
        "method": "upi",
        "label": "UPI Autopay",
        "display": "paul@okhdfcbank",
        "card": None,
        "vpa": "paul@okhdfcbank",
        "bank": None,
        "max_amount": 5000.0,
        "currency": "INR",
        "authorized_on": "2026-06-01",
        "next_charge_date": "2026-09-01",
        "needs_reauth": False,
        "suspended": False
    },
    "can_update": True,
    "update_mode": "settle",
    "amount_due": {"invoice": "inv_...", "amount": 3538.82, "currency": "INR"}
}
```

**Example:**

```python
info = client.get_payment_instrument()
print(info["autopay"]["display"])   # "paul@okhdfcbank"
if info["update_mode"] == "settle":
    print(f"Renewal due: {info['amount_due']['amount']}")
```

### update_payment_method()

Start a checkout that changes the instrument paying for the subscription.

```python
def update_payment_method(
    self,
    payment_method: Optional[str] = None,
    billing_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]
```

The server decides what this does based on whether anything is currently
owed — call `get_payment_instrument()` first if the caller needs to know in
advance:

- **Unpaid renewal**: the checkout settles that invoice at the amount it
  was billed for and registers the new instrument for autopay in the same
  authorization. The billing period does not move.
- **Nothing owed**: the checkout debits one currency unit to register the
  token, refunded automatically.
- **Stripe**: returns a Customer Portal URL instead of a checkout.

**Parameters:**
- `payment_method`: Razorpay only — `"upi"` or `"card"`, validated
  server-side. Defaults to `"upi"` for India, `"card"` for international.
- `billing_name`: Name to prefill in the checkout widget.

**Returns:** Razorpay — the checkout payload (`razorpay_key`,
`razorpay_order_id`, `amount`, `currency`, `prefill`, …) plus `update_mode`
and, when settling, `amount_due`. Stripe — `{"update_mode": "portal",
"portal_url": str}`.

**Example:**

```python
checkout = client.update_payment_method(payment_method="upi")
if checkout["update_mode"] == "portal":
    open_browser(checkout["portal_url"])
else:
    launch_razorpay_widget(checkout)
```

---

## Prompt API

### list_prompts()

List available prompt templates from MCP servers.

```python
def list_prompts(
    self,
    user_id: str,
    cursor: Optional[str] = None
) -> Optional[Dict[str, Any]]
```

**Returns:** `PromptsResponse` TypedDict

```python
{
    "prompts": [
        {
            "name": "summarize_document",
            "title": "Summarize Document",
            "description": "Create a summary of a document",
            "arguments": [
                {
                    "name": "document_id",
                    "description": "The document to summarize",
                    "required": True
                }
            ],
            "server": "erp-tools"
        }
    ],
    "servers_queried": ["erp-tools"],
    "errors": []
}
```

### get_prompt()

Get a rendered prompt with arguments.

```python
def get_prompt(
    self,
    prompt_name: str,
    user_id: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]
```

---

## Tools API

### list_tools()

List available tools from user's configured MCP servers with full input schemas.

```python
def list_tools(
    self,
    user_id: str,
    server: Optional[str] = None,
) -> Optional[Dict[str, Any]]
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | str | Yes | User identifier |
| `server` | str | No | Filter to specific MCP server |

**Returns:** `ToolsResponse` TypedDict

```python
{
    "tools": [
        {
            "name": "brave:web_search",
            "original_name": "web_search",
            "description": "Search the web using Brave Search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            },
            "server": "brave"
        }
    ],
    "servers_queried": ["brave"],
    "errors": null
}
```

**Example:**

```python
tools = client.list_tools("user@example.com")
for t in tools.get("tools", []):
    print(f"{t['name']}: {t['description']}")
```

---

## Standalone Functions

### get_terms()

Get current Assistant Runtime terms and conditions (no auth required).

```python
from assistant_runtime_sdk import get_terms

terms = get_terms("https://ar.example.com")
```

**Returns:** `TermsInfo` TypedDict

```python
{
    "version": "1.0",
    "effective_date": "2025-01-01",
    "terms_of_service": "...",
    "privacy_policy": "...",
    "data_processing_agreement": "...",
    "summary": "...",
    "grace_period_days": 30
}
```

### register_tenant()

Register a new tenant with Assistant Runtime.

```python
from assistant_runtime_sdk import register_tenant

result = register_tenant(
    ar_url="https://ar.example.com",
    site_url="https://mysite.frappe.cloud",
    terms_accepted=True,
    terms_version="1.0",
    accepted_by="admin@example.com"
)
```

**Returns:**

```python
{
    "tenant_id": "generated-tenant-id",
    "tenant_secret": "generated-secret",
    "message": "Tenant registered successfully"
}
```

---

## Constants

```python
# Default values
AssistantRuntimeClient.DEFAULT_AR_URL = "https://ar.example.com"
AssistantRuntimeClient.DEFAULT_TIMEOUT = 30.0
AssistantRuntimeClient.STREAM_CONNECT_TIMEOUT = 30.0
AssistantRuntimeClient.STREAM_READ_TIMEOUT = 300.0
```

## See Also

- [Getting Started Guide](../guides/getting-started.md)
- [Streaming Guide](../guides/streaming.md)
- [AsyncAssistantRuntimeClient Reference](async-client.md)
- [Type Definitions](types.md)

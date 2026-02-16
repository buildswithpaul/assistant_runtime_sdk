# FACL - Python SDK for Frappe Assistant Cloud

A Python SDK for integrating with [Frappe Assistant Cloud (FACL)](https://facl.frappe.cloud) - the AI-powered assistant backend for the Frappe ecosystem.

## Features

- **Sync and Async Clients** - Choose between `FACLClient` (requests) or `AsyncFACLClient` (aiohttp)
- **SSE Streaming** - Real-time streaming responses with tool execution
- **HMAC Authentication** - Secure request signing
- **Auto Model Selection** - Intelligent model routing with cross-provider fallback
- **Full API Coverage** - Chat, billing, conversations, user management, and more
- **Type Hints** - Full type annotations for better IDE support

## Installation

```bash
# Basic installation (sync client only)
pip install facl

# With async support
pip install facl[async]

# Development installation
pip install facl[dev]

# Everything
pip install facl[all]
```

## Quick Start

### Sync Client

```python
from facl import FACLClient

client = FACLClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-secret",
    facl_url="https://facl.frappe.cloud"
)

# List available models
models = client.list_available_models()
for model in models.get("models", []):
    print(f"{model['model_id']} - {model['display_name']}")

# Stream a chat response
for event in client.stream_chat(
    session_id="session-123",
    message="What can you help me with?",
    user_id="user@example.com",
    model_id="auto"  # Use auto-model selection
):
    if event["event"] == "stream_chunk":
        print(event["data"].get("content", ""), end="", flush=True)
    elif event["event"] == "stream_complete":
        print(f"\n\nTokens used: {event['data'].get('tokens_used')}")
```

### Async Client

```python
import asyncio
from facl import AsyncFACLClient

async def main():
    async with AsyncFACLClient(
        tenant_id="your-tenant-id",
        tenant_secret="your-secret"
    ) as client:
        async for event in client.stream_chat(
            session_id="session-123",
            message="Hello!",
            user_id="user@example.com"
        ):
            if event["event"] == "stream_chunk":
                print(event["data"].get("content", ""), end="")

asyncio.run(main())
```

### Custom Logger

```python
import logging
from facl import FACLClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("my_app.facl")

client = FACLClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-secret",
    logger=logger
)
```

## SSE Event Types

When streaming, you'll receive events with these types:

| Event | Description |
|-------|-------------|
| `stream_start` | Stream initialized |
| `stream_chunk` | Text chunk from LLM |
| `stream_complete` | Full response with metrics |
| `stream_error` | Error occurred |
| `thinking` | Reasoning/thinking content |
| `tool_call_start` | Tool execution beginning |
| `tool_call_result` | Tool execution complete |
| `approval_required` | HITL approval needed |
| `tool_cancelled` | Tool was rejected |
| `model_fallback` | Auto mode selected a model |
| `rate_limited` | All models rate limited |

## API Reference

### FACLClient / AsyncFACLClient

#### Chat & Streaming
- `stream_chat(session_id, message, user_id, context=None, model_id=None)` - Stream chat response

#### Models
- `list_available_models()` - List available AI models
- `set_preferred_model(model_id)` - Set preferred model

#### Tenant
- `get_tenant_info()` - Get tenant information
- `accept_terms(terms_version, accepted_by)` - Accept terms and conditions

#### Conversations
- `list_conversations(user_id=None, limit=50, offset=0)` - List conversations
- `get_conversation(conversation_id)` - Get conversation details
- `get_messages(conversation_id, limit=100, offset=0)` - Get messages
- `create_message(conversation_id, message_id, role, content, ...)` - Create message
- `update_conversation(conversation_id, title=None, user_id=None)` - Update conversation
- `delete_conversation(conversation_id)` - Soft delete conversation
- `delete_message(conversation_id, message_id)` - Soft delete message

#### Billing
- `get_plan_comparison()` - Get available plans
- `get_usage_dashboard()` - Get usage statistics
- `get_usage_history(days=30)` - Get historical usage
- `initiate_checkout(plan, billing_cycle="monthly")` - Start checkout
- `verify_checkout(session_id=None)` - Verify payment
- `upgrade_plan(new_plan, billing_cycle="monthly")` - Upgrade subscription
- `cancel_subscription(cancel_immediately=False)` - Cancel subscription

#### Users & MCP Servers
- `register_user(user_id, display_name=None, custom_instructions=None)` - Register user
- `get_user(user_id)` - Get user details
- `get_user_auth_status(user_id)` - Check auth status
- `add_user_mcp_server(user_id, server_name, endpoint_url, ...)` - Add MCP server
- `get_user_mcp_servers(user_id)` - List user's MCP servers
- `update_mcp_server_tokens(user_id, server_name, access_token, ...)` - Update tokens
- `remove_user_mcp_server(user_id, server_name)` - Remove MCP server

#### Prompts
- `list_prompts(user_id, cursor=None)` - List prompt templates
- `get_prompt(prompt_name, arguments=None, user_id=None)` - Get rendered prompt

#### Tools
- `list_tools(user_id, server=None)` - List MCP tools with input schemas

### Standalone Functions

```python
from facl import get_terms, register_tenant

# Get current terms (no auth required)
terms = get_terms("https://facl.frappe.cloud")

# Register a new tenant
result = register_tenant(
    facl_url="https://facl.frappe.cloud",
    site_url="https://mysite.frappe.cloud",
    terms_accepted=True,
    terms_version="1.0",
    accepted_by="admin@example.com"
)
```

## Exceptions

```python
from facl.exceptions import (
    FACLError,              # Base exception
    FACLAuthenticationError, # HMAC signature failed
    FACLRateLimitError,     # Rate limit exceeded (has retry_after)
    FACLStreamError,        # SSE streaming error
    FACLConfigurationError, # Invalid configuration
)
```

## Frappe Integration

For Frappe applications, create a thin adapter:

```python
import frappe
from facl import FACLClient

class FrappeLogger:
    def error(self, msg, *args, **kwargs):
        frappe.log_error(msg, kwargs.get('category', 'FACL'))

def get_facl_client():
    settings = frappe.get_single("FACO Settings")
    if settings.registration_status != "Registered":
        return None

    return FACLClient(
        tenant_id=settings.tenant_id,
        tenant_secret=settings.get_password("tenant_secret"),
        facl_url=settings.facl_url,
        logger=FrappeLogger()
    )
```

## License

GNU Affero General Public License v3.0

Copyright (C) 2025 Paul Clinton

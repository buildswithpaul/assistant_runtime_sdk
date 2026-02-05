# AsyncFACLClient API Reference

Complete API reference for the asynchronous `AsyncFACLClient` class.

## Class: AsyncFACLClient

```python
from facl import AsyncFACLClient
```

### Constructor

```python
AsyncFACLClient(
    tenant_id: str,
    tenant_secret: str,
    facl_url: str = "https://facl.frappe.cloud",
    logger: Optional[logging.Logger] = None,
    timeout: float = 30.0,
    session: Optional[aiohttp.ClientSession] = None
)
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tenant_id` | str | Yes | - | Unique tenant identifier |
| `tenant_secret` | str | Yes | - | HMAC secret for signing |
| `facl_url` | str | No | `https://facl.frappe.cloud` | FACL server URL |
| `logger` | Logger | No | None | Custom logger instance |
| `timeout` | float | No | 30.0 | Request timeout in seconds |
| `session` | ClientSession | No | None | Existing aiohttp session to reuse |

**Raises:**
- `ImportError`: If aiohttp is not installed

**Example:**

```python
from facl import AsyncFACLClient

async with AsyncFACLClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-secret"
) as client:
    models = await client.list_available_models()
```

---

## Context Manager

### \_\_aenter\_\_()

Enter async context - creates session if needed.

```python
async def __aenter__(self) -> "AsyncFACLClient"
```

**Returns:** The client instance

### \_\_aexit\_\_()

Exit async context - closes session if owned by client.

```python
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None
```

**Example:**

```python
# Recommended: Use as context manager
async with AsyncFACLClient(tenant_id, secret) as client:
    # Session is managed automatically
    result = await client.list_available_models()
# Session is closed automatically
```

---

## Streaming API

### stream_chat()

Stream a chat response asynchronously.

```python
async def stream_chat(
    self,
    session_id: str,
    message: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | str | Yes | Conversation session identifier |
| `message` | str | Yes | User's message to send |
| `user_id` | str | Yes | User identifier |
| `context` | dict | No | Page context for the AI |
| `model_id` | str | No | Model ID or "auto" |

**Yields:** `Dict[str, Any]` - SSE events with `event` and `data` keys

**Example:**

```python
async with AsyncFACLClient(tenant_id, secret) as client:
    async for event in client.stream_chat(
        session_id="session-123",
        message="Hello!",
        user_id="user@example.com",
        model_id="auto"
    ):
        if event["event"] == "stream_chunk":
            print(event["data"].get("content", ""), end="")
```

---

## Model API

### list_available_models()

List available AI models.

```python
async def list_available_models(self) -> Optional[Dict[str, Any]]
```

**Returns:** `ModelsResponse` TypedDict

### get_available_models()

Deprecated. Use `list_available_models()` instead.

```python
async def get_available_models(self) -> Optional[Dict[str, Any]]
```

### set_preferred_model()

Set the preferred AI model.

```python
async def set_preferred_model(self, model_id: str) -> bool
```

**Returns:** `True` if successful

---

## Tenant API

### get_tenant_info()

Get tenant information.

```python
async def get_tenant_info(self) -> Optional[Dict[str, Any]]
```

### accept_terms()

Accept Terms and Conditions.

```python
async def accept_terms(
    self,
    terms_version: str,
    accepted_by: str
) -> Dict[str, Any]
```

---

## Conversation API

### list_conversations()

List conversations.

```python
async def list_conversations(
    self,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False,
) -> Optional[Dict[str, Any]]
```

### get_conversation()

Get conversation details.

```python
async def get_conversation(
    self,
    conversation_id: str
) -> Optional[Dict[str, Any]]
```

### get_messages()

Get messages for a conversation.

```python
async def get_messages(
    self,
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
) -> Optional[Dict[str, Any]]
```

---

## User API

### register_user()

Register a user with FACL.

```python
async def register_user(
    self,
    user_id: str,
    display_name: Optional[str] = None,
    custom_instructions: Optional[str] = None,
) -> Dict[str, Any]
```

### get_user()

Get user details.

```python
async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]
```

### get_user_auth_status()

Check user authentication status.

```python
async def get_user_auth_status(self, user_id: str) -> Dict[str, Any]
```

---

## MCP Server API

### add_user_mcp_server()

Add or update an MCP server.

```python
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
) -> Dict[str, Any]
```

### get_user_mcp_servers()

Get all MCP servers for a user.

```python
async def get_user_mcp_servers(self, user_id: str) -> Dict[str, Any]
```

### remove_user_mcp_server()

Remove an MCP server.

```python
async def remove_user_mcp_server(
    self,
    user_id: str,
    server_name: str
) -> Dict[str, Any]
```

---

## Billing API

### get_usage_dashboard()

Get usage and billing data.

```python
async def get_usage_dashboard(self) -> Optional[Dict[str, Any]]
```

### get_usage_history()

Get historical usage.

```python
async def get_usage_history(self, days: int = 30) -> Optional[Dict[str, Any]]
```

### initiate_checkout()

Create checkout session.

```python
async def initiate_checkout(
    self,
    plan: str,
    billing_cycle: str = "monthly"
) -> Optional[Dict[str, Any]]
```

### verify_checkout()

Verify payment completion.

```python
async def verify_checkout(
    self,
    session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]
```

---

## Prompt API

### list_prompts()

List available prompts.

```python
async def list_prompts(
    self,
    user_id: str,
    cursor: Optional[str] = None
) -> Optional[Dict[str, Any]]
```

### get_prompt()

Get a rendered prompt.

```python
async def get_prompt(
    self,
    prompt_name: str,
    user_id: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]
```

---

## Concurrent Operations

### Multiple API Calls

```python
import asyncio

async with AsyncFACLClient(tenant_id, secret) as client:
    # Run multiple requests concurrently
    models, tenant, usage = await asyncio.gather(
        client.list_available_models(),
        client.get_tenant_info(),
        client.get_usage_dashboard()
    )
```

### Multiple Users

```python
async def check_users(client, user_ids):
    tasks = [client.get_user_auth_status(uid) for uid in user_ids]
    return await asyncio.gather(*tasks, return_exceptions=True)

async with AsyncFACLClient(tenant_id, secret) as client:
    results = await check_users(client, ["user1@example.com", "user2@example.com"])
```

---

## Session Management

### Using External Session

```python
import aiohttp

async def with_custom_session():
    # Create custom session
    connector = aiohttp.TCPConnector(limit=100)
    session = aiohttp.ClientSession(connector=connector)

    try:
        # Pass session to client
        client = AsyncFACLClient(
            tenant_id="...",
            tenant_secret="...",
            session=session  # Reuse session
        )

        # Use client...
        result = await client.list_available_models()

    finally:
        # Close session manually
        await session.close()
```

### Connection Pooling

```python
async def high_throughput():
    connector = aiohttp.TCPConnector(
        limit=100,           # Max total connections
        limit_per_host=30,   # Max per host
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        client = AsyncFACLClient(
            tenant_id="...",
            tenant_secret="...",
            session=session
        )

        # High-throughput operations
        tasks = [client.get_user(f"user{i}") for i in range(100)]
        results = await asyncio.gather(*tasks)
```

---

## Error Handling

```python
from facl import (
    AsyncFACLClient,
    FACLConnectionError,
    FACLTimeoutError,
    FACLRateLimitError,
)

async def safe_call(client, method, *args, **kwargs):
    try:
        return await method(*args, **kwargs)
    except FACLRateLimitError as e:
        await asyncio.sleep(e.retry_after)
        return await method(*args, **kwargs)
    except FACLConnectionError as e:
        print(f"Connection error: {e}")
        return None
    except FACLTimeoutError as e:
        print(f"Timeout: {e}")
        return None
```

---

## Constants

```python
# Inherited from BaseFACLClient
AsyncFACLClient.DEFAULT_FACL_URL = "https://facl.frappe.cloud"
AsyncFACLClient.DEFAULT_TIMEOUT = 30.0
AsyncFACLClient.STREAM_CONNECT_TIMEOUT = 30.0
AsyncFACLClient.STREAM_READ_TIMEOUT = 300.0
```

## See Also

- [Async Usage Guide](../guides/async-usage.md)
- [FACLClient Reference](client.md)
- [Error Handling Guide](../guides/error-handling.md)

# Assistant Runtime SDK

Python SDK for **FAC Cloud** — the AI assistant backend powering chat,
streaming tool execution, memory, billing and workflows.

## Features

- **Sync and async clients** — `AssistantRuntimeClient` (requests) or `AsyncAssistantRuntimeClient` (aiohttp)
- **SSE streaming** — real-time responses with live tool execution
- **HMAC authentication** — signed requests, no bearer tokens to leak
- **Auto model selection** — routing with cross-provider fallback
- **Broad API coverage** — chat, conversations, billing, memory, documents, workflows, users
- **Full type hints** — annotated throughout for IDE support

## Installation

```bash
pip install assistant-runtime-sdk           # sync client
pip install "assistant-runtime-sdk[async]"  # with async support
pip install "assistant-runtime-sdk[all]"    # everything, including dev tools
```

Requires Python 3.10+.

> The distribution is named `assistant-runtime-sdk`; the import name is
> `assistant_runtime_sdk`. PyPI normalises underscores to hyphens, so both
> spellings resolve on install.

## Quick start

### Sync client

```python
from assistant_runtime_sdk import AssistantRuntimeClient

client = AssistantRuntimeClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-secret",
    ar_url="https://api.fac-cloud.com",
)

models = client.list_available_models()
for model in models.get("models", []):
    print(f"{model['model_id']} - {model['display_name']}")

for event in client.stream_chat(
    session_id="session-123",
    message="What can you help me with?",
    user_id="user@example.com",
    model_id="auto",
):
    if event["event"] == "stream_chunk":
        print(event["data"].get("content", ""), end="", flush=True)
    elif event["event"] == "stream_complete":
        print(f"\n\nTokens used: {event['data'].get('tokens_used')}")
```

### Async client

```python
import asyncio
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

async def main():
    async with AsyncAssistantRuntimeClient(
        tenant_id="your-tenant-id",
        tenant_secret="your-secret",
        ar_url="https://api.fac-cloud.com",
    ) as client:
        async for event in client.stream_chat(
            session_id="session-123",
            message="Hello!",
            user_id="user@example.com",
        ):
            if event["event"] == "stream_chunk":
                print(event["data"].get("content", ""), end="")

asyncio.run(main())
```

### Custom logger

```python
import logging
from assistant_runtime_sdk import AssistantRuntimeClient

logging.basicConfig(level=logging.DEBUG)

client = AssistantRuntimeClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-secret",
    logger=logging.getLogger("my_app.assistant"),
)
```

## SSE event types

| Event | Description |
|-------|-------------|
| `stream_start` | Stream initialised |
| `stream_chunk` | Text chunk from the model |
| `stream_complete` | Full response with metrics |
| `stream_error` | Error occurred |
| `thinking` | Reasoning content |
| `tool_call_start` | Tool execution beginning |
| `tool_call_result` | Tool execution complete |
| `approval_required` | Human approval needed |
| `tool_cancelled` | Tool was rejected |
| `model_fallback` | Auto mode selected a different model |
| `rate_limited` | All models rate limited |

## API reference

`AssistantRuntimeClient` and `AsyncAssistantRuntimeClient` expose the same
surface. A representative selection:

**Chat** — `stream_chat(session_id, message, user_id, context=None, model_id=None, attachments=None, ...)`

**Models** — `list_available_models()`, `get_available_models()`, `set_preferred_model(model_id)`

**Tenant** — `get_tenant_info()`, `get_terms_status()`, `accept_terms(...)`, `heartbeat()`

**Conversations** — `list_conversations()`, `get_conversation()`, `get_messages()`,
`create_message()`, `update_conversation()`, `delete_conversation()`, `delete_message()`

**Billing** — `get_plan_comparison()`, `get_usage_dashboard()`, `get_usage_history()`,
`get_credit_balance()`, `initiate_checkout()`, `create_hosted_checkout()`,
`verify_checkout()`, `upgrade_plan()`, `cancel_subscription()`, `get_invoices()`,
`get_payment_instrument()`, `update_payment_method()`

**Users & seats** — `register_user()`, `get_user()`, `list_users()`, `invite_user()`,
`add_user_seat()`, `set_user_credit_limit()`, `get_user_auth_status()`

**MCP servers & tools** — `get_user_mcp_servers()`, `add_user_mcp_server()`,
`update_mcp_server_tokens()`, `remove_user_mcp_server()`, `list_tools()`, `set_tool_preference()`

**Memory & documents** — `list_memories()`, `update_memory()`, `delete_memory()`,
`upload_document()`, `list_documents()`, `get_document_content()`, `get_storage_info()`

**Workflows** — `list_workflows()`, `create_workflow()`, `execute_workflow()`,
`list_workflow_runs()`, `set_workflow_schedule()`

**Prompts** — `list_prompts(user_id)`, `get_prompt(prompt_name, arguments=None)`

See [`docs/`](docs/) for the full reference.

### Standalone functions

```python
from assistant_runtime_sdk import get_terms, register_tenant

terms = get_terms("https://api.fac-cloud.com")

result = register_tenant(
    ar_url="https://api.fac-cloud.com",
    site_url="https://mysite.example.com",
    owner_email="admin@example.com",
    application_id="your-application-id",
    terms_accepted=True,
    terms_version="1.0",
    accepted_by="admin@example.com",
)
```

## Exceptions

```python
from assistant_runtime_sdk import (
    ARError,                    # base exception
    ARAuthenticationError,      # HMAC signature rejected
    ARRateLimitError,           # rate limited (carries retry_after)
    ARStreamError,              # SSE streaming failure
    ARConfigurationError,       # invalid configuration
    ARConnectionError,          # transport failure
    ARTimeoutError,             # request timed out
    ARAPIError,                 # non-2xx API response
    ARBillingUnavailableError,  # billing companion not installed
)
```

## Using it from a Frappe app

The SDK is plain Python with no Frappe dependency. To use it inside a Frappe
application, wrap it in a thin adapter that supplies credentials and a logger:

```python
import frappe
from assistant_runtime_sdk import AssistantRuntimeClient

class FrappeLogger:
    def error(self, msg, *args, **kwargs):
        frappe.log_error(msg, kwargs.get("category", "Assistant Runtime"))

def get_client(settings):
    return AssistantRuntimeClient(
        tenant_id=settings.tenant_id,
        tenant_secret=settings.get_password("tenant_secret"),
        ar_url=settings.ar_url,
        logger=FrappeLogger(),
    )
```

## Releasing

See [docs/guides/releasing.md](docs/guides/releasing.md).

## License

GNU Affero General Public License v3.0

Copyright (C) 2025 Paul Clinton

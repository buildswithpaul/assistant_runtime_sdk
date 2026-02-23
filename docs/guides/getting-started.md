# Getting Started with Assistant Runtime SDK

This guide walks you through installing and using the Assistant Runtime SDK to integrate AI capabilities into your Python application.

## Prerequisites

- Python 3.10 or higher
- An Assistant Runtime tenant account (tenant_id and tenant_secret)
- Network access to your Assistant Runtime server

## Installation

### Basic Installation

For most use cases, install the base package:

```bash
pip install assistant_runtime_sdk
```

This installs the synchronous client using the `requests` library.

### With Async Support

If you need async/await support:

```bash
pip install assistant_runtime_sdk[async]
```

This adds `aiohttp` for the `AsyncAssistantRuntimeClient`.

### Development Installation

For development with testing tools:

```bash
pip install assistant_runtime_sdk[dev]
```

### From Source

```bash
git clone https://github.com/anthropics/assistant-runtime-sdk.git
cd assistant-runtime-sdk
pip install -e ".[all]"
```

## Basic Usage

### 1. Import the Client

```python
from assistant_runtime_sdk import AssistantRuntimeClient
```

### 2. Create a Client Instance

```python
client = AssistantRuntimeClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-tenant-secret",
    ar_url="https://ar.example.com"  # Optional, this is the default
)
```

### 3. List Available Models

```python
models = client.list_available_models()

if models:
    print("Available models:")
    for model in models.get("models", []):
        print(f"  - {model['model_id']}: {model['display_name']}")

    # Check auto mode
    auto_mode = models.get("auto_mode")
    if auto_mode and auto_mode.get("enabled"):
        print(f"\nAuto mode available with {auto_mode['fallback_chain_length']} models")
```

### 4. Stream a Chat Response

```python
# Start a conversation
for event in client.stream_chat(
    session_id="my-session-123",
    message="Hello! What can you help me with?",
    user_id="user@example.com",
    model_id="auto"  # Use automatic model selection
):
    event_type = event["event"]
    data = event["data"]

    if event_type == "stream_start":
        print(f"Started with model: {data.get('model_id')}")

    elif event_type == "stream_chunk":
        print(data.get("content", ""), end="", flush=True)

    elif event_type == "stream_complete":
        print(f"\n\nTokens used: {data.get('tokens_used')}")

    elif event_type == "stream_error":
        print(f"Error: {data.get('error')}")
```

## Understanding SSE Events

When streaming, you'll receive various event types:

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `stream_start` | Stream initialized | `session_id`, `message_id`, `model_id` |
| `stream_chunk` | Text content chunk | `content`, `chunk_index` |
| `stream_complete` | Stream finished | `full_response`, `tokens_used`, `model_id` |
| `stream_error` | Error occurred | `error`, `error_code` |
| `thinking` | Reasoning content | `content` |
| `tool_call_start` | Tool execution starting | `tool_name`, `tool_id`, `arguments` |
| `tool_call_result` | Tool execution complete | `tool_id`, `result`, `success` |
| `model_fallback` | Auto mode selected model | `original`, `selected`, `provider` |
| `rate_limited` | All models rate limited | `retry_after`, `models_checked` |

## Configuration Options

### Client Parameters

```python
client = AssistantRuntimeClient(
    tenant_id="your-tenant-id",      # Required: Your Assistant Runtime tenant ID
    tenant_secret="your-secret",      # Required: HMAC signing secret
    ar_url="https://ar.example.com",  # Optional: Assistant Runtime server URL
    timeout=30.0,                     # Optional: Request timeout in seconds
    logger=my_logger,                 # Optional: Custom logger instance
)
```

### Environment Variables

You can also configure via environment variables:

```python
import os
from assistant_runtime_sdk import AssistantRuntimeClient

client = AssistantRuntimeClient(
    tenant_id=os.environ["AR_TENANT_ID"],
    tenant_secret=os.environ["AR_TENANT_SECRET"],
    ar_url=os.environ.get("AR_URL", "https://ar.example.com"),
)
```

## Next Steps

- [Authentication Guide](authentication.md) - Learn about HMAC signing
- [Streaming Guide](streaming.md) - Deep dive into SSE events
- [Async Usage](async-usage.md) - Using the async client
- [Error Handling](error-handling.md) - Handling errors gracefully
- [API Reference](../api/client.md) - Complete API documentation

## Troubleshooting

### Connection Errors

If you get connection errors:

1. Verify your `ar_url` is correct
2. Check network connectivity
3. Ensure your tenant is registered and active

### Authentication Errors

If you get 401/403 errors:

1. Verify your `tenant_id` and `tenant_secret`
2. Check that your tenant subscription is active
3. Ensure server time is synchronized (HMAC uses timestamps)

### Rate Limiting

If you get rate limited:

1. Use `model_id="auto"` for automatic fallback
2. Implement exponential backoff
3. Check `retry_after` in the error response

```python
from assistant_runtime_sdk import ARRateLimitError

try:
    response = client.some_api_call()
except ARRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
```

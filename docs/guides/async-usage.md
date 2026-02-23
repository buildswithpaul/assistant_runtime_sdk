# Async Usage Guide

The Assistant Runtime SDK provides an asynchronous client (`AsyncAssistantRuntimeClient`) for applications using Python's async/await pattern. This guide covers everything you need to know about async usage.

## Installation

The async client requires `aiohttp`:

```bash
pip install assistant_runtime_sdk[async]
```

## Basic Usage

### Context Manager Pattern (Recommended)

```python
import asyncio
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

async def main():
    async with AsyncAssistantRuntimeClient(
        tenant_id="your-tenant-id",
        tenant_secret="your-secret",
        ar_url="https://ar.example.com"
    ) as client:
        # Client is ready to use
        models = await client.list_available_models()
        print(f"Found {len(models.get('models', []))} models")

asyncio.run(main())
```

The context manager automatically:
- Creates an `aiohttp.ClientSession` on enter
- Closes the session cleanly on exit

### Manual Session Management

For advanced use cases, you can manage the session yourself:

```python
import aiohttp
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

async def main():
    # Create your own session with custom settings
    connector = aiohttp.TCPConnector(limit=100)
    session = aiohttp.ClientSession(connector=connector)

    try:
        client = AsyncAssistantRuntimeClient(
            tenant_id="your-tenant-id",
            tenant_secret="your-secret",
            session=session  # Reuse existing session
        )

        # Use the client...
        models = await client.list_available_models()

    finally:
        await session.close()

asyncio.run(main())
```

## Async Streaming

### Basic Async Stream

```python
import asyncio
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

async def stream_chat():
    async with AsyncAssistantRuntimeClient(
        tenant_id="your-tenant-id",
        tenant_secret="your-secret"
    ) as client:
        async for event in client.stream_chat(
            session_id="session-123",
            message="Explain async programming",
            user_id="user@example.com",
            model_id="auto"
        ):
            if event["event"] == "stream_chunk":
                print(event["data"].get("content", ""), end="", flush=True)

            elif event["event"] == "stream_complete":
                data = event["data"]
                print(f"\n\nTokens: {data.get('tokens_used')}")

asyncio.run(stream_chat())
```

### Handling All Events

```python
async def handle_async_stream(client, session_id, message, user_id):
    """Process all SSE events asynchronously."""

    full_response = ""

    async for event in client.stream_chat(
        session_id=session_id,
        message=message,
        user_id=user_id,
        model_id="auto"
    ):
        event_type = event["event"]
        data = event["data"]

        if event_type == "stream_start":
            print(f"Started: {data.get('model_id')}")

        elif event_type == "model_fallback":
            print(f"Using model: {data.get('selected')}")

        elif event_type == "stream_chunk":
            content = data.get("content", "")
            full_response += content
            print(content, end="", flush=True)

        elif event_type == "tool_call_start":
            print(f"\n[Tool] {data.get('tool_name')}...")

        elif event_type == "tool_call_result":
            status = "OK" if data.get("success") else "FAILED"
            print(f"[Tool] {data.get('tool_name')}: {status}")

        elif event_type == "stream_complete":
            print(f"\n\nComplete: {data.get('tokens_used')} tokens")

        elif event_type == "stream_error":
            print(f"\nError: {data.get('error')}")
            break

    return full_response
```

## Concurrent Requests

### Multiple API Calls in Parallel

```python
import asyncio
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

async def fetch_all_data():
    async with AsyncAssistantRuntimeClient(
        tenant_id="your-tenant-id",
        tenant_secret="your-secret"
    ) as client:
        # Run multiple requests concurrently
        models, tenant_info, usage = await asyncio.gather(
            client.list_available_models(),
            client.get_tenant_info(),
            client.get_usage_dashboard()
        )

        print(f"Models: {len(models.get('models', []))}")
        print(f"Tenant: {tenant_info.get('tenant_id')}")
        print(f"Usage: {usage.get('used')}/{usage.get('quota')}")

asyncio.run(fetch_all_data())
```

### Multiple Users Concurrently

```python
async def check_multiple_users(client, user_ids):
    """Check auth status for multiple users concurrently."""

    tasks = [
        client.get_user_auth_status(user_id)
        for user_id in user_ids
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for user_id, result in zip(user_ids, results):
        if isinstance(result, Exception):
            print(f"{user_id}: Error - {result}")
        else:
            ready = result.get("ready_for_streaming", False)
            print(f"{user_id}: {'Ready' if ready else 'Not ready'}")

async def main():
    async with AsyncAssistantRuntimeClient(tenant_id="...", tenant_secret="...") as client:
        await check_multiple_users(client, [
            "user1@example.com",
            "user2@example.com",
            "user3@example.com"
        ])

asyncio.run(main())
```

## Integration Patterns

### With FastAPI

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

app = FastAPI()

# Create client at startup
@app.on_event("startup")
async def startup():
    app.state.ar_client = AsyncAssistantRuntimeClient(
        tenant_id="your-tenant-id",
        tenant_secret="your-secret"
    )
    await app.state.ar_client.__aenter__()

@app.on_event("shutdown")
async def shutdown():
    await app.state.ar_client.__aexit__(None, None, None)

@app.post("/chat")
async def chat(session_id: str, message: str, user_id: str):
    async def generate():
        async for event in app.state.ar_client.stream_chat(
            session_id=session_id,
            message=message,
            user_id=user_id
        ):
            yield f"event: {event['event']}\n"
            yield f"data: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@app.get("/models")
async def get_models():
    return await app.state.ar_client.list_available_models()
```

### With aiohttp Web Server

```python
from aiohttp import web
from assistant_runtime_sdk import AsyncAssistantRuntimeClient
import json

async def create_app():
    app = web.Application()

    # Create client
    app["ar_client"] = AsyncAssistantRuntimeClient(
        tenant_id="your-tenant-id",
        tenant_secret="your-secret"
    )

    async def on_startup(app):
        await app["ar_client"].__aenter__()

    async def on_cleanup(app):
        await app["ar_client"].__aexit__(None, None, None)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    async def stream_handler(request):
        data = await request.json()

        response = web.StreamResponse(
            headers={"Content-Type": "text/event-stream"}
        )
        await response.prepare(request)

        async for event in app["ar_client"].stream_chat(
            session_id=data["session_id"],
            message=data["message"],
            user_id=data["user_id"]
        ):
            line = f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
            await response.write(line.encode())

        return response

    app.router.add_post("/chat", stream_handler)
    return app

if __name__ == "__main__":
    web.run_app(create_app())
```

### With Django (Async Views)

```python
# views.py
from django.http import StreamingHttpResponse
from assistant_runtime_sdk import AsyncAssistantRuntimeClient
import asyncio
import json

async def chat_stream(request):
    session_id = request.POST.get("session_id")
    message = request.POST.get("message")
    user_id = request.POST.get("user_id")

    async def event_generator():
        async with AsyncAssistantRuntimeClient(
            tenant_id="your-tenant-id",
            tenant_secret="your-secret"
        ) as client:
            async for event in client.stream_chat(
                session_id=session_id,
                message=message,
                user_id=user_id
            ):
                yield f"event: {event['event']}\n"
                yield f"data: {json.dumps(event['data'])}\n\n"

    return StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream"
    )
```

## Error Handling

### Async Exception Handling

```python
from assistant_runtime_sdk import (
    AsyncAssistantRuntimeClient,
    ARConnectionError,
    ARTimeoutError,
    ARAPIError,
    ARRateLimitError
)

async def safe_api_call(client, method, *args, **kwargs):
    """Wrapper with error handling for async API calls."""
    try:
        return await method(*args, **kwargs)

    except ARConnectionError as e:
        print(f"Connection failed: {e}")
        return None

    except ARTimeoutError as e:
        print(f"Request timed out: {e}")
        return None

    except ARRateLimitError as e:
        print(f"Rate limited. Retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return await method(*args, **kwargs)  # Retry

    except ARAPIError as e:
        print(f"API error ({e.status_code}): {e}")
        return None

# Usage
async def main():
    async with AsyncAssistantRuntimeClient(tenant_id="...", tenant_secret="...") as client:
        models = await safe_api_call(client, client.list_available_models)
        if models:
            print(f"Found {len(models.get('models', []))} models")
```

### Streaming Error Handling

```python
async def handle_stream_errors(client, session_id, message, user_id):
    """Stream with comprehensive error handling."""
    try:
        async for event in client.stream_chat(session_id, message, user_id):
            if event["event"] == "stream_error":
                error_code = event["data"].get("error_code")
                error_msg = event["data"].get("error")

                if error_code == "QUOTA_EXCEEDED":
                    raise Exception("Token quota exceeded")
                elif error_code == "MODEL_UNAVAILABLE":
                    raise Exception("Model not available")
                else:
                    raise Exception(f"Stream error: {error_msg}")

            elif event["event"] == "rate_limited":
                retry_after = event["data"].get("retry_after", 60)
                raise Exception(f"Rate limited. Retry after {retry_after}s")

            # Process normal events...
            yield event

    except asyncio.CancelledError:
        print("Stream was cancelled")
        raise

    except Exception as e:
        print(f"Stream failed: {e}")
        raise
```

## Performance Optimization

### Connection Pooling

```python
import aiohttp
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

async def high_throughput_operations():
    # Configure connection pool
    connector = aiohttp.TCPConnector(
        limit=100,           # Max connections
        limit_per_host=30,   # Max per host
        ttl_dns_cache=300,   # DNS cache TTL
    )

    timeout = aiohttp.ClientTimeout(
        total=60,
        connect=10,
        sock_read=30
    )

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    ) as session:
        client = AsyncAssistantRuntimeClient(
            tenant_id="your-tenant-id",
            tenant_secret="your-secret",
            session=session
        )

        # High-throughput operations...
        tasks = [
            client.get_user(f"user{i}@example.com")
            for i in range(100)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Semaphore for Rate Control

```python
async def rate_limited_operations(client, user_ids, max_concurrent=10):
    """Process users with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_user(user_id):
        async with semaphore:
            return await client.get_user_auth_status(user_id)

    tasks = [process_user(uid) for uid in user_ids]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## Testing Async Code

### With pytest-asyncio

```python
import pytest
from assistant_runtime_sdk import AsyncAssistantRuntimeClient

@pytest.fixture
async def client():
    async with AsyncAssistantRuntimeClient(
        tenant_id="test-tenant",
        tenant_secret="test-secret",
        ar_url="http://localhost:8000"  # Mock server
    ) as client:
        yield client

@pytest.mark.asyncio
async def test_list_models(client):
    models = await client.list_available_models()
    assert models is not None
    assert "models" in models

@pytest.mark.asyncio
async def test_stream_chat(client):
    events = []
    async for event in client.stream_chat(
        session_id="test-session",
        message="Hello",
        user_id="test@example.com"
    ):
        events.append(event)

    assert len(events) > 0
    assert any(e["event"] == "stream_complete" for e in events)
```

## API Reference

### AsyncAssistantRuntimeClient Constructor

```python
AsyncAssistantRuntimeClient(
    tenant_id: str,              # Required: Tenant ID
    tenant_secret: str,          # Required: HMAC secret
    ar_url: str = "https://ar.example.com",  # Assistant Runtime server URL
    logger: Logger = None,       # Optional logger
    timeout: float = 30.0,       # Request timeout
    session: ClientSession = None  # Optional aiohttp session
)
```

### Context Manager Methods

```python
async def __aenter__(self) -> AsyncAssistantRuntimeClient:
    """Enter context - creates session if needed."""

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """Exit context - closes session if we own it."""
```

### Async Generator for Streaming

```python
async def stream_chat(
    self,
    session_id: str,
    message: str,
    user_id: str,
    context: Optional[Dict] = None,
    model_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream chat response asynchronously."""
```

See the [AsyncAssistantRuntimeClient API Reference](../api/async-client.md) for complete documentation.

## Next Steps

- [Error Handling](error-handling.md) - Complete error handling patterns
- [API Reference](../api/async-client.md) - Full AsyncAssistantRuntimeClient documentation
- [Examples](../examples/) - Working code examples

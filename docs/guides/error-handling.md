# Error Handling Guide

This guide covers how to handle errors when using the FACL SDK, including the exception hierarchy, common error patterns, and best practices.

## Exception Hierarchy

The SDK defines a clear exception hierarchy:

```
FACLError (base)
├── FACLAuthenticationError   # HMAC signature issues
├── FACLRateLimitError        # Rate limiting (has retry_after)
├── FACLStreamError           # SSE streaming errors
├── FACLConfigurationError    # Invalid configuration
├── FACLAPIError              # HTTP/API errors (has status_code)
├── FACLTimeoutError          # Request timeouts
└── FACLConnectionError       # Network connectivity issues
```

## Importing Exceptions

```python
from facl import (
    FACLError,
    FACLAuthenticationError,
    FACLRateLimitError,
    FACLStreamError,
    FACLConfigurationError,
    FACLAPIError,
    FACLTimeoutError,
    FACLConnectionError,
)
```

## Exception Details

### FACLError

Base exception for all SDK errors.

```python
from facl import FACLError

try:
    result = client.some_api_call()
except FACLError as e:
    print(f"FACL error: {e}")
```

### FACLAuthenticationError

Raised when HMAC signature validation fails.

```python
from facl import FACLAuthenticationError

try:
    result = client.list_available_models()
except FACLAuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Check tenant_id and tenant_secret
```

**Common causes:**
- Wrong `tenant_secret`
- Clock skew between client and server
- Incorrect parameter encoding

### FACLRateLimitError

Raised when rate limits are exceeded. Includes retry information.

```python
from facl import FACLRateLimitError

try:
    result = client.list_available_models()
except FACLRateLimitError as e:
    print(f"Rate limited: {e}")
    print(f"Retry after: {e.retry_after} seconds")
    print(f"Models checked: {e.models_checked}")

    # Wait and retry
    import time
    time.sleep(e.retry_after)
    result = client.list_available_models()  # Retry
```

**Attributes:**
- `retry_after`: Seconds to wait before retrying (float)
- `models_checked`: List of models that were rate limited

### FACLStreamError

Raised when SSE streaming encounters an error.

```python
from facl import FACLStreamError

try:
    for event in client.stream_chat(session_id, message, user_id):
        process(event)
except FACLStreamError as e:
    print(f"Stream error: {e}")
```

**Common causes:**
- Connection dropped mid-stream
- Invalid SSE format from server
- Server-side error during streaming

### FACLConfigurationError

Raised for invalid client configuration.

```python
from facl import FACLConfigurationError, AsyncFACLClient

try:
    # AsyncFACLClient requires context manager or session
    client = AsyncFACLClient(tenant_id="...", tenant_secret="...")
    await client.list_available_models()  # Error!
except FACLConfigurationError as e:
    print(f"Configuration error: {e}")
    # "No active session. Use AsyncFACLClient as a context manager"
```

**Common causes:**
- Missing required parameters
- Invalid URL format
- AsyncFACLClient used without context manager

### FACLAPIError

Raised for HTTP API errors. Includes status code.

```python
from facl import FACLAPIError

try:
    result = client.get_conversation("invalid-id")
except FACLAPIError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")

    if e.status_code == 404:
        print("Conversation not found")
    elif e.status_code == 403:
        print("Access denied")
```

**Attributes:**
- `status_code`: HTTP status code (int or None)

### FACLTimeoutError

Raised when a request times out.

```python
from facl import FACLTimeoutError

try:
    # Long-running operation
    for event in client.stream_chat(session_id, long_message, user_id):
        process(event)
except FACLTimeoutError as e:
    print(f"Timeout: {e}")
    # Consider increasing timeout or shorter messages
```

### FACLConnectionError

Raised when network connection fails.

```python
from facl import FACLConnectionError

try:
    result = client.list_available_models()
except FACLConnectionError as e:
    print(f"Connection failed: {e}")
    # Check network, server URL, firewall
```

## Error Handling Patterns

### Basic Try-Except

```python
from facl import FACLClient, FACLError

client = FACLClient(tenant_id="...", tenant_secret="...")

try:
    models = client.list_available_models()
    print(f"Found {len(models.get('models', []))} models")
except FACLError as e:
    print(f"Error: {e}")
```

### Comprehensive Error Handling

```python
from facl import (
    FACLClient,
    FACLAuthenticationError,
    FACLRateLimitError,
    FACLAPIError,
    FACLTimeoutError,
    FACLConnectionError,
    FACLError,
)
import time

def safe_api_call(client, method, *args, max_retries=3, **kwargs):
    """Make API call with comprehensive error handling."""

    for attempt in range(max_retries):
        try:
            return method(*args, **kwargs)

        except FACLAuthenticationError as e:
            # Don't retry auth errors
            raise RuntimeError(f"Authentication failed: {e}") from e

        except FACLRateLimitError as e:
            if attempt < max_retries - 1:
                print(f"Rate limited. Waiting {e.retry_after}s...")
                time.sleep(e.retry_after)
                continue
            raise

        except FACLTimeoutError as e:
            if attempt < max_retries - 1:
                print(f"Timeout. Retrying ({attempt + 1}/{max_retries})...")
                continue
            raise

        except FACLConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Connection error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise

        except FACLAPIError as e:
            if e.status_code and 500 <= e.status_code < 600:
                # Server error - retry
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
            raise

        except FACLError as e:
            # Unknown FACL error - don't retry
            raise

    raise RuntimeError("Max retries exceeded")

# Usage
client = FACLClient(tenant_id="...", tenant_secret="...")
result = safe_api_call(client, client.list_available_models)
```

### Stream Error Handling

```python
from facl import FACLClient, FACLStreamError, FACLConnectionError

def stream_with_error_handling(client, session_id, message, user_id):
    """Stream chat with comprehensive error handling."""

    try:
        for event in client.stream_chat(session_id, message, user_id):
            event_type = event["event"]
            data = event["data"]

            # Handle in-stream errors
            if event_type == "stream_error":
                error_code = data.get("error_code", "UNKNOWN")
                error_msg = data.get("error", "Unknown error")

                if error_code == "QUOTA_EXCEEDED":
                    raise Exception("Your token quota has been exceeded")
                elif error_code == "MODEL_UNAVAILABLE":
                    raise Exception("The requested model is not available")
                elif error_code == "INVALID_REQUEST":
                    raise Exception(f"Invalid request: {error_msg}")
                else:
                    raise Exception(f"Stream error: {error_msg}")

            elif event_type == "rate_limited":
                retry_after = data.get("retry_after", 60)
                models = data.get("models_checked", [])
                raise Exception(
                    f"All models rate limited ({models}). "
                    f"Retry after {retry_after}s"
                )

            # Process normal events
            if event_type == "stream_chunk":
                yield data.get("content", "")
            elif event_type == "stream_complete":
                return

    except FACLStreamError as e:
        raise Exception(f"Stream failed: {e}") from e

    except FACLConnectionError as e:
        raise Exception(f"Connection lost during stream: {e}") from e

# Usage
try:
    for content in stream_with_error_handling(client, "sess", "Hello", "user"):
        print(content, end="", flush=True)
except Exception as e:
    print(f"\nError: {e}")
```

### Async Error Handling

```python
import asyncio
from facl import (
    AsyncFACLClient,
    FACLRateLimitError,
    FACLConnectionError,
    FACLTimeoutError,
)

async def resilient_async_call(client, method, *args, max_retries=3, **kwargs):
    """Async API call with retry logic."""

    for attempt in range(max_retries):
        try:
            return await method(*args, **kwargs)

        except FACLRateLimitError as e:
            if attempt < max_retries - 1:
                print(f"Rate limited. Waiting {e.retry_after}s...")
                await asyncio.sleep(e.retry_after)
                continue
            raise

        except (FACLConnectionError, FACLTimeoutError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Error: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            raise

    raise RuntimeError("Max retries exceeded")

# Usage
async def main():
    async with AsyncFACLClient(tenant_id="...", tenant_secret="...") as client:
        models = await resilient_async_call(client, client.list_available_models)
        print(models)

asyncio.run(main())
```

## Error Response Codes

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Verify tenant_id and tenant_secret |
| 403 | Forbidden | Check permissions/subscription |
| 404 | Not Found | Resource doesn't exist |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Retry with backoff |
| 502/503 | Service Unavailable | Retry later |

### Stream Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `QUOTA_EXCEEDED` | Token quota used up | Upgrade plan or wait for reset |
| `MODEL_UNAVAILABLE` | Model not accessible | Use different model or auto |
| `INVALID_REQUEST` | Bad request params | Fix request parameters |
| `TOOL_ERROR` | Tool execution failed | Check tool configuration |
| `CONTEXT_TOO_LONG` | Message too long | Shorten message |
| `TIMEOUT` | Processing timeout | Retry or simplify request |

## Best Practices

### 1. Always Use Specific Exceptions

```python
# Good: Specific handling
try:
    result = client.api_call()
except FACLRateLimitError as e:
    handle_rate_limit(e)
except FACLAuthenticationError as e:
    handle_auth_error(e)
except FACLError as e:
    handle_other_error(e)

# Avoid: Catching all exceptions
try:
    result = client.api_call()
except Exception as e:  # Too broad
    print(f"Error: {e}")
```

### 2. Implement Exponential Backoff

```python
import time
import random

def with_backoff(func, max_retries=5, base_delay=1):
    """Retry with exponential backoff and jitter."""

    for attempt in range(max_retries):
        try:
            return func()
        except (FACLConnectionError, FACLTimeoutError) as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Attempt {attempt + 1} failed. Retrying in {delay:.1f}s...")
            time.sleep(delay)
```

### 3. Log Errors with Context

```python
import logging

logger = logging.getLogger(__name__)

def api_call_with_logging(client, operation, *args, **kwargs):
    """Make API call with detailed error logging."""

    try:
        return operation(*args, **kwargs)

    except FACLError as e:
        logger.error(
            f"FACL {operation.__name__} failed: {e}",
            extra={
                "operation": operation.__name__,
                "args": args,
                "kwargs": kwargs,
                "error_type": type(e).__name__,
            },
            exc_info=True
        )
        raise
```

### 4. Handle Partial Streaming Failures

```python
def robust_stream(client, session_id, message, user_id):
    """Stream that handles partial failures gracefully."""

    accumulated = []
    last_message_id = None

    try:
        for event in client.stream_chat(session_id, message, user_id):
            if event["event"] == "stream_start":
                last_message_id = event["data"].get("message_id")

            elif event["event"] == "stream_chunk":
                accumulated.append(event["data"].get("content", ""))
                yield event["data"].get("content", "")

            elif event["event"] == "stream_complete":
                return

    except FACLConnectionError:
        # Connection lost - return what we have
        partial = "".join(accumulated)
        if partial:
            yield f"\n[Connection lost. Partial response: {len(partial)} chars]"
        raise

    except FACLStreamError:
        # Stream error - return what we have
        partial = "".join(accumulated)
        if partial:
            yield f"\n[Stream error. Partial response preserved.]"
        raise
```

### 5. Use Context Managers for Cleanup

```python
from contextlib import contextmanager
from facl import FACLClient

@contextmanager
def facl_session(tenant_id, tenant_secret, **kwargs):
    """Context manager with automatic cleanup."""

    client = FACLClient(tenant_id, tenant_secret, **kwargs)
    try:
        yield client
    except FACLError as e:
        # Log error before re-raising
        print(f"Session error: {e}")
        raise
    finally:
        # Any cleanup if needed
        pass

# Usage
with facl_session("tenant", "secret") as client:
    models = client.list_available_models()
```

## Debugging Tips

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("facl")

client = FACLClient(
    tenant_id="...",
    tenant_secret="...",
    logger=logger
)
```

### Check Request Details

```python
# The client logs request details at DEBUG level
# Look for:
# - URL being called
# - Parameters being sent
# - Signature being generated
# - Response status codes
```

### Verify Authentication

```python
from facl import generate_signature, verify_signature

# Generate a test signature
params = {"tenant_id": "test", "message": "hello"}
sig = generate_signature("test", "secret", params)
print(f"Generated: {sig}")

# Verify it works
is_valid = verify_signature(sig, "test", "secret", params)
print(f"Valid: {is_valid}")
```

## Next Steps

- [API Reference](../api/client.md) - Complete error documentation
- [Streaming Guide](streaming.md) - Handling stream errors
- [Examples](../examples/) - Working error handling examples

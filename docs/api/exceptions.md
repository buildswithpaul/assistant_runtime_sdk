# Exceptions Reference

Complete reference for Assistant Runtime SDK exceptions.

## Exception Hierarchy

```
ARError (base)
├── ARAuthenticationError
├── ARRateLimitError
├── ARStreamError
├── ARConfigurationError
├── ARAPIError
├── ARTimeoutError
└── ARConnectionError
```

## Importing

```python
from assistant_runtime_sdk import (
    ARError,
    ARAuthenticationError,
    ARRateLimitError,
    ARStreamError,
    ARConfigurationError,
    ARAPIError,
    ARTimeoutError,
    ARConnectionError,
)
```

---

## ARError

Base exception for all Assistant Runtime SDK errors.

```python
class ARError(Exception):
    """Base exception for Assistant Runtime SDK errors."""
    pass
```

**Usage:**

```python
try:
    result = client.api_call()
except ARError as e:
    # Catches any AR error
    print(f"AR error: {e}")
```

---

## ARAuthenticationError

Raised when HMAC signature validation fails.

```python
class ARAuthenticationError(ARError):
    """HMAC signature validation failed."""
    pass
```

**Causes:**
- Invalid `tenant_secret`
- Clock skew between client and server
- Incorrect parameter encoding

**Example:**

```python
try:
    client.list_available_models()
except ARAuthenticationError as e:
    print("Authentication failed - check tenant credentials")
```

---

## ARRateLimitError

Raised when rate limits are exceeded.

```python
class ARRateLimitError(ARError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        models_checked: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.models_checked = models_checked or []
```

**Attributes:**
- `retry_after` (float): Seconds to wait before retrying
- `models_checked` (List[str]): Models that were rate limited

**Example:**

```python
try:
    for event in client.stream_chat(...):
        process(event)
except ARRateLimitError as e:
    print(f"Rate limited. Retry in {e.retry_after} seconds")
    print(f"Models checked: {e.models_checked}")
    time.sleep(e.retry_after)
    # Retry...
```

---

## ARStreamError

Raised when SSE streaming encounters an error.

```python
class ARStreamError(ARError):
    """SSE streaming error."""
    pass
```

**Causes:**
- Connection dropped during streaming
- Invalid SSE format from server
- Server-side error during streaming

**Example:**

```python
try:
    for event in client.stream_chat(...):
        process(event)
except ARStreamError as e:
    print(f"Stream failed: {e}")
```

---

## ARConfigurationError

Raised for invalid client configuration.

```python
class ARConfigurationError(ARError):
    """Invalid configuration."""
    pass
```

**Causes:**
- Missing required parameters
- Invalid URL format
- AsyncAssistantRuntimeClient used without context manager

**Example:**

```python
from assistant_runtime_sdk import AsyncAssistantRuntimeClient, ARConfigurationError

# This will raise ARConfigurationError
client = AsyncAssistantRuntimeClient(tenant_id="...", tenant_secret="...")
try:
    await client.list_available_models()  # No session!
except ARConfigurationError as e:
    print(e)  # "No active session. Use as context manager..."
```

---

## ARAPIError

Raised for HTTP API errors.

```python
class ARAPIError(ARError):
    """HTTP/API error."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None
    ):
        super().__init__(message)
        self.status_code = status_code
```

**Attributes:**
- `status_code` (int): HTTP status code (400, 403, 404, 500, etc.)

**Common Status Codes:**

| Code | Meaning |
|------|---------|
| 400 | Bad Request - invalid parameters |
| 401 | Unauthorized - invalid credentials |
| 403 | Forbidden - insufficient permissions |
| 404 | Not Found - resource doesn't exist |
| 500 | Server Error - Assistant Runtime server issue |

**Example:**

```python
try:
    result = client.get_conversation("invalid-id")
except ARAPIError as e:
    if e.status_code == 404:
        print("Conversation not found")
    elif e.status_code == 403:
        print("Access denied")
    else:
        print(f"API error ({e.status_code}): {e}")
```

---

## ARTimeoutError

Raised when a request times out.

```python
class ARTimeoutError(ARError):
    """Request timeout."""
    pass
```

**Causes:**
- Network latency
- Server overloaded
- Long-running operation

**Example:**

```python
try:
    for event in client.stream_chat(...):
        process(event)
except ARTimeoutError as e:
    print("Request timed out - try with shorter message")
```

---

## ARConnectionError

Raised when network connection fails.

```python
class ARConnectionError(ARError):
    """Network connection error."""
    pass
```

**Causes:**
- No network connectivity
- DNS resolution failure
- Server unreachable
- Firewall blocking

**Example:**

```python
try:
    result = client.list_available_models()
except ARConnectionError as e:
    print(f"Connection failed: {e}")
    print("Check network and server URL")
```

---

## Error Handling Patterns

### Comprehensive Handler

```python
from assistant_runtime_sdk import (
    AssistantRuntimeClient,
    ARAuthenticationError,
    ARRateLimitError,
    ARAPIError,
    ARTimeoutError,
    ARConnectionError,
    ARError,
)
import time

def safe_api_call(func, *args, max_retries=3, **kwargs):
    """Make API call with comprehensive error handling."""

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except ARAuthenticationError:
            # Don't retry auth errors
            raise

        except ARRateLimitError as e:
            if attempt < max_retries - 1:
                time.sleep(e.retry_after or 60)
                continue
            raise

        except ARTimeoutError:
            if attempt < max_retries - 1:
                continue
            raise

        except ARConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise

        except ARAPIError as e:
            if e.status_code and e.status_code >= 500:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
            raise

    raise RuntimeError("Max retries exceeded")
```

### Async Handler

```python
import asyncio
from assistant_runtime_sdk import AsyncAssistantRuntimeClient, ARRateLimitError

async def resilient_call(client, method, *args, **kwargs):
    """Async call with retry logic."""

    for attempt in range(3):
        try:
            return await method(*args, **kwargs)
        except ARRateLimitError as e:
            if attempt < 2:
                await asyncio.sleep(e.retry_after or 60)
                continue
            raise

    raise RuntimeError("Max retries exceeded")
```

### Stream Error Handler

```python
def stream_with_recovery(client, session_id, message, user_id):
    """Stream with partial failure recovery."""

    accumulated = []

    try:
        for event in client.stream_chat(session_id, message, user_id):
            if event["event"] == "stream_chunk":
                accumulated.append(event["data"].get("content", ""))
            elif event["event"] == "stream_complete":
                return "".join(accumulated)

    except (ARStreamError, ARConnectionError):
        # Return partial response
        partial = "".join(accumulated)
        if partial:
            return f"{partial}\n[Connection lost - partial response]"
        raise

    return "".join(accumulated)
```

## See Also

- [Error Handling Guide](../guides/error-handling.md)
- [AssistantRuntimeClient Reference](client.md)
- [Streaming Guide](../guides/streaming.md)

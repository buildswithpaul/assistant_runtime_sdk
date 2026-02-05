# Exceptions Reference

Complete reference for FACL SDK exceptions.

## Exception Hierarchy

```
FACLError (base)
├── FACLAuthenticationError
├── FACLRateLimitError
├── FACLStreamError
├── FACLConfigurationError
├── FACLAPIError
├── FACLTimeoutError
└── FACLConnectionError
```

## Importing

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

---

## FACLError

Base exception for all FACL SDK errors.

```python
class FACLError(Exception):
    """Base exception for FACL SDK errors."""
    pass
```

**Usage:**

```python
try:
    result = client.api_call()
except FACLError as e:
    # Catches any FACL error
    print(f"FACL error: {e}")
```

---

## FACLAuthenticationError

Raised when HMAC signature validation fails.

```python
class FACLAuthenticationError(FACLError):
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
except FACLAuthenticationError as e:
    print("Authentication failed - check tenant credentials")
```

---

## FACLRateLimitError

Raised when rate limits are exceeded.

```python
class FACLRateLimitError(FACLError):
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
except FACLRateLimitError as e:
    print(f"Rate limited. Retry in {e.retry_after} seconds")
    print(f"Models checked: {e.models_checked}")
    time.sleep(e.retry_after)
    # Retry...
```

---

## FACLStreamError

Raised when SSE streaming encounters an error.

```python
class FACLStreamError(FACLError):
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
except FACLStreamError as e:
    print(f"Stream failed: {e}")
```

---

## FACLConfigurationError

Raised for invalid client configuration.

```python
class FACLConfigurationError(FACLError):
    """Invalid configuration."""
    pass
```

**Causes:**
- Missing required parameters
- Invalid URL format
- AsyncFACLClient used without context manager

**Example:**

```python
from facl import AsyncFACLClient, FACLConfigurationError

# This will raise FACLConfigurationError
client = AsyncFACLClient(tenant_id="...", tenant_secret="...")
try:
    await client.list_available_models()  # No session!
except FACLConfigurationError as e:
    print(e)  # "No active session. Use as context manager..."
```

---

## FACLAPIError

Raised for HTTP API errors.

```python
class FACLAPIError(FACLError):
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
| 500 | Server Error - FACL server issue |

**Example:**

```python
try:
    result = client.get_conversation("invalid-id")
except FACLAPIError as e:
    if e.status_code == 404:
        print("Conversation not found")
    elif e.status_code == 403:
        print("Access denied")
    else:
        print(f"API error ({e.status_code}): {e}")
```

---

## FACLTimeoutError

Raised when a request times out.

```python
class FACLTimeoutError(FACLError):
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
except FACLTimeoutError as e:
    print("Request timed out - try with shorter message")
```

---

## FACLConnectionError

Raised when network connection fails.

```python
class FACLConnectionError(FACLError):
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
except FACLConnectionError as e:
    print(f"Connection failed: {e}")
    print("Check network and server URL")
```

---

## Error Handling Patterns

### Comprehensive Handler

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

def safe_api_call(func, *args, max_retries=3, **kwargs):
    """Make API call with comprehensive error handling."""

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except FACLAuthenticationError:
            # Don't retry auth errors
            raise

        except FACLRateLimitError as e:
            if attempt < max_retries - 1:
                time.sleep(e.retry_after or 60)
                continue
            raise

        except FACLTimeoutError:
            if attempt < max_retries - 1:
                continue
            raise

        except FACLConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise

        except FACLAPIError as e:
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
from facl import AsyncFACLClient, FACLRateLimitError

async def resilient_call(client, method, *args, **kwargs):
    """Async call with retry logic."""

    for attempt in range(3):
        try:
            return await method(*args, **kwargs)
        except FACLRateLimitError as e:
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

    except (FACLStreamError, FACLConnectionError):
        # Return partial response
        partial = "".join(accumulated)
        if partial:
            return f"{partial}\n[Connection lost - partial response]"
        raise

    return "".join(accumulated)
```

## See Also

- [Error Handling Guide](../guides/error-handling.md)
- [FACLClient Reference](client.md)
- [Streaming Guide](../guides/streaming.md)

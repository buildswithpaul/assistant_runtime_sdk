# Utilities Reference

Reference for authentication and streaming utility functions.

## Authentication Utilities

### generate_signature()

Generate HMAC-SHA256 signature for FACL API request.

```python
from facl import generate_signature

signature = generate_signature(
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
    timestamp: Optional[int] = None,
) -> str
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tenant_id` | str | Yes | - | Tenant identifier |
| `tenant_secret` | str | Yes | - | HMAC secret |
| `params` | dict | Yes | - | Request parameters |
| `for_query_string` | bool | No | False | Convert values to strings |
| `timestamp` | int | No | None | Override timestamp (for testing) |

**Returns:** Signature string in format `"timestamp:signature"`

**Example:**

```python
from facl import generate_signature

params = {"tenant_id": "my-tenant", "message": "Hello"}
signature = generate_signature(
    tenant_id="my-tenant",
    tenant_secret="my-secret",
    params=params,
    for_query_string=True
)
# Returns: "1704067200:a1b2c3d4e5f6..."
```

---

### verify_signature()

Verify HMAC-SHA256 signature from FACL request.

```python
from facl import verify_signature

is_valid = verify_signature(
    signature_header: str,
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
    max_age_seconds: int = 300,
) -> bool
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `signature_header` | str | Yes | - | X-FACL-Signature header value |
| `tenant_id` | str | Yes | - | Expected tenant ID |
| `tenant_secret` | str | Yes | - | HMAC secret |
| `params` | dict | Yes | - | Request parameters to verify |
| `for_query_string` | bool | No | False | Treat as query string |
| `max_age_seconds` | int | No | 300 | Max signature age |

**Returns:** `True` if valid, `False` otherwise

**Example:**

```python
from facl import verify_signature

# Verify incoming webhook
is_valid = verify_signature(
    signature_header=request.headers["X-FACL-Signature"],
    tenant_id="my-tenant",
    tenant_secret="my-secret",
    params=request.json,
    for_query_string=False,
    max_age_seconds=300
)

if not is_valid:
    return {"error": "Invalid signature"}, 401
```

---

### get_signature_header()

Generate headers dict with FACL signature.

```python
from facl import get_signature_header

headers = get_signature_header(
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
) -> Dict[str, str]
```

**Returns:** Dict with `X-FACL-Signature` key

**Example:**

```python
from facl import get_signature_header
import requests

params = {"message": "Hello"}
headers = get_signature_header("my-tenant", "my-secret", params)
# headers = {"X-FACL-Signature": "1704067200:..."}

response = requests.get(url, params=params, headers=headers)
```

---

## Streaming Utilities

### SSEEventType

Enum of SSE event types.

```python
from facl import SSEEventType

class SSEEventType(str, Enum):
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_COMPLETE = "stream_complete"
    STREAM_ERROR = "stream_error"
    THINKING = "thinking"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"
    APPROVAL_REQUIRED = "approval_required"
    TOOL_CANCELLED = "tool_cancelled"
    MODEL_FALLBACK = "model_fallback"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "SSEEventType"
```

**Example:**

```python
from facl import SSEEventType

# Compare with string
if event["event"] == SSEEventType.STREAM_CHUNK:
    handle_chunk(event["data"])

# Get enum from string
event_type = SSEEventType.from_string("stream_chunk")
# Returns SSEEventType.STREAM_CHUNK

# Unknown events
event_type = SSEEventType.from_string("custom_event")
# Returns SSEEventType.UNKNOWN
```

---

### parse_sse_line()

Parse a single SSE line.

```python
from facl import parse_sse_line

result = parse_sse_line(line: str) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `line`: Raw SSE line

**Returns:** Parsed dict or None for empty/comment lines

```python
{
    "type": "event_name" | "data" | "id" | "retry" | "comment",
    "value": <parsed value>
}
```

**Example:**

```python
from facl import parse_sse_line

# Parse event line
result = parse_sse_line("event: stream_chunk")
# {"type": "event_name", "value": "stream_chunk"}

# Parse data line with JSON
result = parse_sse_line('data: {"content": "Hello"}')
# {"type": "data", "value": {"content": "Hello"}}

# Parse data line with plain text
result = parse_sse_line("data: plain text")
# {"type": "data", "value": "plain text"}

# Empty line
result = parse_sse_line("")
# None

# Comment line
result = parse_sse_line(": heartbeat")
# None
```

---

### parse_sse_stream()

Parse an SSE stream from an iterator.

```python
from facl import parse_sse_stream

events = parse_sse_stream(
    lines: Iterator[str]
) -> Iterator[Dict[str, Any]]
```

**Parameters:**
- `lines`: Iterator of SSE lines

**Yields:** Event dicts with `event` and `data` keys

**Example:**

```python
from facl import parse_sse_stream

# From raw lines
lines = [
    "event: stream_start",
    'data: {"session_id": "123"}',
    "",
    "event: stream_chunk",
    'data: {"content": "Hello"}',
]

for event in parse_sse_stream(iter(lines)):
    print(f"{event['event']}: {event['data']}")

# Output:
# stream_start: {'session_id': '123'}
# stream_chunk: {'content': 'Hello'}
```

---

### is_terminal_event()

Check if an event type indicates stream end.

```python
from facl.streaming import is_terminal_event

is_terminal_event(event_type: str) -> bool
```

**Terminal events:**
- `stream_complete`
- `stream_error`
- `rate_limited`

**Example:**

```python
from facl.streaming import is_terminal_event

for event in client.stream_chat(...):
    process(event)

    if is_terminal_event(event["event"]):
        print("Stream ended")
        break
```

---

### extract_stream_metrics()

Extract metrics from stream_complete event.

```python
from facl.streaming import extract_stream_metrics

metrics = extract_stream_metrics(
    complete_event: Dict[str, Any]
) -> Dict[str, Any]
```

**Returns:**

```python
{
    "tokens_used": int,
    "tokens_actual": int,
    "model_id": Optional[str],
    "message_id": Optional[str],
    "session_id": Optional[str],
    "full_response": str,
}
```

**Example:**

```python
from facl.streaming import extract_stream_metrics

for event in client.stream_chat(...):
    if event["event"] == "stream_complete":
        metrics = extract_stream_metrics(event)
        print(f"Tokens: {metrics['tokens_used']}")
        print(f"Model: {metrics['model_id']}")
```

---

### format_sse_event()

Format data as SSE event string (for servers).

```python
from facl.streaming import format_sse_event

sse_string = format_sse_event(
    event_type: str,
    data: Any,
    event_id: Optional[str] = None
) -> str
```

**Example:**

```python
from facl.streaming import format_sse_event

sse = format_sse_event("stream_chunk", {"content": "Hello"})
# Returns:
# event: stream_chunk
# data: {"content": "Hello"}
#
# (with trailing newlines)

# With event ID
sse = format_sse_event("stream_chunk", {"content": "Hello"}, event_id="msg-1")
# Returns:
# id: msg-1
# event: stream_chunk
# data: {"content": "Hello"}
#
```

---

## Usage Patterns

### Custom SSE Client

```python
import requests
from facl import parse_sse_stream, get_signature_header

def custom_stream(url, params, tenant_id, tenant_secret):
    """Custom SSE streaming with raw requests."""

    headers = get_signature_header(tenant_id, tenant_secret, params)

    with requests.get(url, params=params, headers=headers, stream=True) as r:
        r.raise_for_status()

        def line_generator():
            for line in r.iter_lines(decode_unicode=True):
                yield line

        for event in parse_sse_stream(line_generator()):
            yield event
```

### SSE Server (Flask)

```python
from flask import Flask, Response
from facl.streaming import format_sse_event

app = Flask(__name__)

@app.route("/stream")
def stream():
    def generate():
        yield format_sse_event("stream_start", {"session": "123"})

        for chunk in ["Hello", " ", "World"]:
            yield format_sse_event("stream_chunk", {"content": chunk})

        yield format_sse_event("stream_complete", {"tokens": 10})

    return Response(generate(), mimetype="text/event-stream")
```

## See Also

- [Authentication Guide](../guides/authentication.md)
- [Streaming Guide](../guides/streaming.md)
- [FACLClient Reference](client.md)

# Streaming Guide

Assistant Runtime uses Server-Sent Events (SSE) for real-time streaming of AI responses. This guide covers everything you need to know about working with SSE streams.

## Overview

When you call `stream_chat()`, Assistant Runtime returns responses as a stream of events rather than a single response. This enables:

- **Real-time display**: Show text as it's generated
- **Tool execution visibility**: See when tools are being called
- **Progress indication**: Know when thinking/processing is happening
- **Early termination**: Stop processing on errors without waiting

## Basic Streaming

### Simple Chat Stream

```python
from assistant_runtime_sdk import AssistantRuntimeClient

client = AssistantRuntimeClient(tenant_id="...", tenant_secret="...")

for event in client.stream_chat(
    session_id="session-123",
    message="Explain quantum computing",
    user_id="user@example.com"
):
    if event["event"] == "stream_chunk":
        print(event["data"].get("content", ""), end="", flush=True)
```

### Handling All Event Types

```python
def handle_stream(client, session_id, message, user_id):
    """Process all SSE event types from Assistant Runtime."""

    full_response = ""

    for event in client.stream_chat(session_id, message, user_id, model_id="auto"):
        event_type = event["event"]
        data = event["data"]

        if event_type == "stream_start":
            print(f"[Started] Model: {data.get('model_id')}")
            print(f"[Session] {data.get('session_id')}")

        elif event_type == "model_fallback":
            # Auto mode selected a model
            if data.get("fallback_attempted"):
                print(f"[Fallback] {data.get('original')} -> {data.get('selected')}")
            else:
                print(f"[Model] Using {data.get('selected')} ({data.get('provider')})")

        elif event_type == "thinking":
            # AI is reasoning (extended thinking models)
            print(f"[Thinking] {data.get('content', '')[:50]}...")

        elif event_type == "stream_chunk":
            # Main content chunk
            content = data.get("content", "")
            full_response += content
            print(content, end="", flush=True)

        elif event_type == "tool_call_start":
            # Tool execution beginning
            print(f"\n[Tool] Calling {data.get('tool_name')}...")
            print(f"  Args: {data.get('arguments')}")

        elif event_type == "tool_call_result":
            # Tool execution complete
            success = "OK" if data.get("success") else "FAILED"
            print(f"[Tool] {data.get('tool_name')} - {success}")
            if data.get("duration_ms"):
                print(f"  Duration: {data.get('duration_ms')}ms")

        elif event_type == "approval_required":
            # Human-in-the-loop approval needed
            print(f"\n[APPROVAL NEEDED] {data.get('tool_name')}")
            print(f"  Reason: {data.get('reason')}")
            print(f"  Timeout: {data.get('timeout_seconds')}s")

        elif event_type == "tool_cancelled":
            # Tool was rejected
            print(f"[Cancelled] Tool {data.get('tool_name')} was rejected")

        elif event_type == "stream_complete":
            # Stream finished successfully
            print(f"\n\n[Complete] Tokens: {data.get('tokens_used')}")
            print(f"  Model: {data.get('model_id')}")

        elif event_type == "stream_error":
            # Error occurred
            print(f"\n[Error] {data.get('error')}")
            print(f"  Code: {data.get('error_code')}")

        elif event_type == "rate_limited":
            # All models rate limited
            print(f"\n[Rate Limited] Retry after {data.get('retry_after')}s")
            print(f"  Models checked: {data.get('models_checked')}")

    return full_response
```

## Event Types Reference

### Core Events

| Event | When | Key Data Fields |
|-------|------|-----------------|
| `stream_start` | Stream begins | `session_id`, `message_id`, `model_id`, `timestamp` |
| `stream_chunk` | Content received | `content`, `chunk_index` |
| `stream_complete` | Stream ends | `full_response`, `tokens_used`, `tokens_actual`, `model_id` |
| `stream_error` | Error occurs | `error`, `error_code` |

### AI Events

| Event | When | Key Data Fields |
|-------|------|-----------------|
| `thinking` | AI reasoning | `content` (reasoning text) |

### Tool Events

| Event | When | Key Data Fields |
|-------|------|-----------------|
| `tool_call_start` | Tool invoked | `tool_name`, `tool_id`, `arguments` |
| `tool_call_result` | Tool finished | `tool_id`, `tool_name`, `result`, `success`, `duration_ms` |
| `approval_required` | HITL needed | `tool_name`, `tool_id`, `arguments`, `reason`, `timeout_seconds` |
| `tool_cancelled` | Tool rejected | `tool_name`, `tool_id` |

### Auto Mode Events

| Event | When | Key Data Fields |
|-------|------|-----------------|
| `model_fallback` | Model selected | `original`, `selected`, `provider`, `tier`, `fallback_attempted` |
| `rate_limited` | All exhausted | `error`, `error_code`, `retry_after`, `models_checked` |

## Using SSE Utilities

The SDK provides utilities for parsing SSE streams:

### SSEEventType Enum

```python
from assistant_runtime_sdk import SSEEventType

# Use enum for type checking
if event["event"] == SSEEventType.STREAM_CHUNK:
    handle_chunk(event["data"])

# Get all event types
print(list(SSEEventType))
```

### Parse Raw SSE Lines

```python
from assistant_runtime_sdk import parse_sse_line, parse_sse_stream

# Parse single line
line = 'data: {"content": "Hello"}'
result = parse_sse_line(line)
# {'type': 'data', 'value': {'content': 'Hello'}}

# Parse stream of lines
lines = [
    "event: stream_chunk",
    'data: {"content": "Hello"}',
    "",
    "event: stream_chunk",
    'data: {"content": " World"}',
]

for event in parse_sse_stream(iter(lines)):
    print(event)
# {'event': 'stream_chunk', 'data': {'content': 'Hello'}}
# {'event': 'stream_chunk', 'data': {'content': ' World'}}
```

### Check Terminal Events

```python
from assistant_runtime_sdk.streaming import is_terminal_event

# Check if stream should end
if is_terminal_event(event["event"]):
    print("Stream ended")
    break
```

### Extract Metrics

```python
from assistant_runtime_sdk.streaming import extract_stream_metrics

if event["event"] == "stream_complete":
    metrics = extract_stream_metrics(event)
    print(f"Tokens: {metrics['tokens_used']}")
    print(f"Model: {metrics['model_id']}")
```

## Streaming with Context

You can provide page context to help the AI understand the user's environment:

```python
context = {
    "current_doctype": "Sales Order",
    "current_docname": "SO-2024-00001",
    "page_url": "/app/sales-order/SO-2024-00001",
    "selected_fields": ["customer", "grand_total"],
}

for event in client.stream_chat(
    session_id="session-123",
    message="What's the status of this order?",
    user_id="user@example.com",
    context=context
):
    # Process events...
```

## Model Selection

### Specific Model

```python
for event in client.stream_chat(
    session_id="session-123",
    message="Hello",
    user_id="user@example.com",
    model_id="claude-sonnet-4-20250514"  # Specific model
):
    pass
```

### Auto Mode (Recommended)

```python
for event in client.stream_chat(
    session_id="session-123",
    message="Hello",
    user_id="user@example.com",
    model_id="auto"  # Automatic selection with fallback
):
    if event["event"] == "model_fallback":
        data = event["data"]
        if data.get("fallback_attempted"):
            print(f"Fell back from {data['original']} to {data['selected']}")
```

## Error Handling in Streams

```python
from assistant_runtime_sdk import AssistantRuntimeClient, ARStreamError, ARConnectionError

client = AssistantRuntimeClient(tenant_id="...", tenant_secret="...")

try:
    for event in client.stream_chat(session_id, message, user_id):
        if event["event"] == "stream_error":
            # Handle application-level error
            error_code = event["data"].get("error_code")
            if error_code == "QUOTA_EXCEEDED":
                print("Credit quota exceeded")
            elif error_code == "MODEL_UNAVAILABLE":
                print("Model not available")
            else:
                print(f"Error: {event['data'].get('error')}")
            break

        elif event["event"] == "rate_limited":
            # All models rate limited
            retry_after = event["data"].get("retry_after", 60)
            print(f"Rate limited. Retry in {retry_after}s")
            break

        # Handle normal events...

except ARConnectionError as e:
    # Network-level error
    print(f"Connection failed: {e}")

except ARStreamError as e:
    # SSE parsing error
    print(f"Stream error: {e}")
```

## Building a Chat UI

### Accumulating Response

```python
def stream_to_ui(client, session_id, message, user_id, ui_callback):
    """Stream response to a UI callback."""

    accumulated_text = ""
    current_tool = None

    for event in client.stream_chat(session_id, message, user_id, model_id="auto"):
        event_type = event["event"]
        data = event["data"]

        if event_type == "stream_start":
            ui_callback("status", "AI is typing...")

        elif event_type == "stream_chunk":
            content = data.get("content", "")
            accumulated_text += content
            ui_callback("text", accumulated_text)

        elif event_type == "thinking":
            ui_callback("status", "Thinking...")

        elif event_type == "tool_call_start":
            current_tool = data.get("tool_name")
            ui_callback("status", f"Using {current_tool}...")

        elif event_type == "tool_call_result":
            ui_callback("status", "Processing results...")

        elif event_type == "stream_complete":
            ui_callback("complete", {
                "text": accumulated_text,
                "tokens": data.get("tokens_used"),
                "model": data.get("model_id")
            })

        elif event_type == "stream_error":
            ui_callback("error", data.get("error"))

    return accumulated_text
```

### With Token Counter

```python
class StreamHandler:
    def __init__(self):
        self.chunks = []
        self.tools_called = []
        self.tokens_used = 0
        self.model_id = None

    def process_event(self, event):
        event_type = event["event"]
        data = event["data"]

        if event_type == "stream_chunk":
            self.chunks.append(data.get("content", ""))

        elif event_type == "tool_call_result":
            self.tools_called.append({
                "name": data.get("tool_name"),
                "success": data.get("success"),
                "duration_ms": data.get("duration_ms")
            })

        elif event_type == "stream_complete":
            self.tokens_used = data.get("tokens_used", 0)
            self.model_id = data.get("model_id")

    @property
    def full_response(self):
        return "".join(self.chunks)

# Usage
handler = StreamHandler()
for event in client.stream_chat(session_id, message, user_id):
    handler.process_event(event)

print(f"Response: {handler.full_response}")
print(f"Tokens: {handler.tokens_used}")
print(f"Tools: {handler.tools_called}")
```

## Performance Tips

### 1. Use Flush for Real-time Display

```python
for event in client.stream_chat(...):
    if event["event"] == "stream_chunk":
        print(event["data"].get("content", ""), end="", flush=True)
        #                                              ^^^^^^^^^^^^
        # flush=True ensures immediate display
```

### 2. Process Events Efficiently

```python
# Good: Direct processing
for event in client.stream_chat(...):
    if event["event"] == "stream_chunk":
        display(event["data"]["content"])

# Avoid: Collecting all then processing
events = list(client.stream_chat(...))  # Defeats streaming purpose
for event in events:
    display(event)
```

### 3. Handle Timeouts Gracefully

```python
from assistant_runtime_sdk import AssistantRuntimeClient, ARTimeoutError

client = AssistantRuntimeClient(tenant_id="...", tenant_secret="...", timeout=60.0)

try:
    for event in client.stream_chat(...):
        process(event)
except ARTimeoutError:
    print("Stream timed out - consider shorter messages or different model")
```

## Next Steps

- [Async Usage](async-usage.md) - Streaming with async/await
- [Error Handling](error-handling.md) - Complete error handling guide
- [API Reference](../api/client.md) - Full stream_chat documentation

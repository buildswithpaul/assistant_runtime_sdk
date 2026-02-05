# Assistant Runtime SDK - Streaming Utilities
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Server-Sent Events (SSE) parsing utilities for Assistant Runtime streaming responses.
"""

import json
from enum import Enum
from typing import Optional, Dict, Any, Iterator, Tuple


class SSEEventType(str, Enum):
    """SSE event types used by Assistant Runtime streaming API."""

    # Core streaming events
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_COMPLETE = "stream_complete"
    STREAM_ERROR = "stream_error"

    # AI response events
    THINKING = "thinking"

    # Tool execution events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"

    # Human-in-the-loop events
    APPROVAL_REQUIRED = "approval_required"
    TOOL_CANCELLED = "tool_cancelled"

    # Auto-model events
    MODEL_FALLBACK = "model_fallback"

    # Rate limiting events
    RATE_LIMITED = "rate_limited"

    # Unknown event (fallback)
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "SSEEventType":
        """Convert string to SSEEventType, returning UNKNOWN if not found."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


def parse_sse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single SSE line.

    Args:
        line: Raw SSE line (e.g., "event: stream_chunk" or "data: {...}")

    Returns:
        Parsed event dict with 'type' and 'value', or None for empty/comment lines

    Example:
        >>> parse_sse_line("event: stream_chunk")
        {'type': 'event_name', 'value': 'stream_chunk'}
        >>> parse_sse_line("data: {\"content\": \"Hello\"}")
        {'type': 'data', 'value': {'content': 'Hello'}}
        >>> parse_sse_line(": heartbeat")
        None
    """
    line = line.strip()

    # Skip empty lines and comments (heartbeats)
    if not line or line.startswith(":"):
        return None

    if line.startswith("event:"):
        return {"type": "event_name", "value": line[6:].strip()}
    elif line.startswith("data:"):
        data_str = line[5:].strip()
        if data_str:
            try:
                return {"type": "data", "value": json.loads(data_str)}
            except json.JSONDecodeError:
                # Return raw string if not valid JSON
                return {"type": "data", "value": data_str}
    elif line.startswith("id:"):
        return {"type": "id", "value": line[3:].strip()}
    elif line.startswith("retry:"):
        try:
            return {"type": "retry", "value": int(line[6:].strip())}
        except ValueError:
            return None

    return None


def parse_sse_stream(lines: Iterator[str]) -> Iterator[Dict[str, Any]]:
    """
    Parse an SSE stream from an iterator of lines.

    Yields complete events as dicts with 'event' and 'data' keys.

    Args:
        lines: Iterator of SSE lines (from response.iter_lines() or similar)

    Yields:
        Event dicts: {'event': 'stream_chunk', 'data': {...}}

    Example:
        >>> for event in parse_sse_stream(response.iter_lines()):
        ...     print(event['event'], event['data'])
    """
    current_event: Optional[str] = None

    for line in lines:
        if line is None:
            continue

        # Handle both str and bytes
        if isinstance(line, bytes):
            line = line.decode("utf-8")

        parsed = parse_sse_line(line)
        if not parsed:
            continue

        if parsed["type"] == "event_name":
            current_event = parsed["value"]
        elif parsed["type"] == "data":
            yield {"event": current_event or "message", "data": parsed["value"]}
            current_event = None


def format_sse_event(event_type: str, data: Any, event_id: Optional[str] = None) -> str:
    """
    Format data as an SSE event string.

    Useful for servers that need to send SSE responses.

    Args:
        event_type: Event type name
        data: Event data (will be JSON serialized)
        event_id: Optional event ID

    Returns:
        Formatted SSE event string

    Example:
        >>> print(format_sse_event("stream_chunk", {"content": "Hello"}))
        event: stream_chunk
        data: {"content": "Hello"}

    """
    lines = []

    if event_id:
        lines.append(f"id: {event_id}")

    lines.append(f"event: {event_type}")

    if isinstance(data, str):
        lines.append(f"data: {data}")
    else:
        lines.append(f"data: {json.dumps(data)}")

    lines.append("")  # Empty line to end event
    return "\n".join(lines) + "\n"


def is_terminal_event(event_type: str) -> bool:
    """
    Check if an event type indicates the stream has ended.

    Args:
        event_type: The event type string

    Returns:
        True if this is a terminal event (stream_complete, stream_error, rate_limited)

    Example:
        >>> is_terminal_event("stream_chunk")
        False
        >>> is_terminal_event("stream_complete")
        True
    """
    terminal_events = {
        SSEEventType.STREAM_COMPLETE.value,
        SSEEventType.STREAM_ERROR.value,
        SSEEventType.RATE_LIMITED.value,
    }
    return event_type in terminal_events


def extract_stream_metrics(complete_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metrics from a stream_complete event.

    Args:
        complete_event: The data from a stream_complete event

    Returns:
        Dict with normalized metrics (tokens_used, model_id, duration_ms, etc.)

    Example:
        >>> metrics = extract_stream_metrics(event['data'])
        >>> print(f"Used {metrics.get('tokens_used', 0)} tokens")
    """
    data = complete_event.get("data", complete_event) if isinstance(complete_event, dict) else {}

    return {
        "tokens_used": data.get("tokens_used", 0),
        "tokens_actual": data.get("tokens_actual", 0),
        "model_id": data.get("model_id"),
        "message_id": data.get("message_id"),
        "session_id": data.get("session_id"),
        "full_response": data.get("full_response", ""),
    }

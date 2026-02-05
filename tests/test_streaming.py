# FACL SDK - Streaming Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""Unit tests for SSE streaming utilities."""

import pytest
from facl.streaming import (
    SSEEventType,
    parse_sse_line,
    parse_sse_stream,
)


class TestSSEEventType:
    """Tests for SSEEventType enum."""

    def test_event_type_values(self):
        """Test that event types have correct string values."""
        assert SSEEventType.STREAM_START.value == "stream_start"
        assert SSEEventType.STREAM_CHUNK.value == "stream_chunk"
        assert SSEEventType.STREAM_COMPLETE.value == "stream_complete"
        assert SSEEventType.STREAM_ERROR.value == "stream_error"
        assert SSEEventType.THINKING.value == "thinking"
        assert SSEEventType.TOOL_CALL_START.value == "tool_call_start"
        assert SSEEventType.TOOL_CALL_RESULT.value == "tool_call_result"
        assert SSEEventType.APPROVAL_REQUIRED.value == "approval_required"
        assert SSEEventType.TOOL_CANCELLED.value == "tool_cancelled"
        assert SSEEventType.MODEL_FALLBACK.value == "model_fallback"
        assert SSEEventType.RATE_LIMITED.value == "rate_limited"

    def test_event_type_is_string(self):
        """Test that event types can be used as strings."""
        # SSEEventType inherits from str, so it can be compared with strings
        assert SSEEventType.STREAM_CHUNK == "stream_chunk"
        assert SSEEventType.STREAM_CHUNK.value == "stream_chunk"
        # When used in f-strings, use .value for string representation
        assert f"event: {SSEEventType.STREAM_CHUNK.value}" == "event: stream_chunk"


class TestParseSSELine:
    """Tests for parse_sse_line function."""

    def test_parse_event_line(self):
        """Test parsing event: line."""
        result = parse_sse_line("event: stream_chunk")

        assert result is not None
        assert result["type"] == "event_name"
        assert result["value"] == "stream_chunk"

    def test_parse_data_line_json(self):
        """Test parsing data: line with JSON payload."""
        result = parse_sse_line('data: {"content": "Hello"}')

        assert result is not None
        assert result["type"] == "data"
        assert result["value"] == {"content": "Hello"}

    def test_parse_data_line_plain_text(self):
        """Test parsing data: line with plain text (non-JSON)."""
        result = parse_sse_line("data: plain text message")

        assert result is not None
        assert result["type"] == "data"
        # Non-JSON data is returned as raw string
        assert result["value"] == "plain text message"

    def test_parse_id_line(self):
        """Test parsing id: line."""
        result = parse_sse_line("id: msg-12345")

        assert result is not None
        assert result["type"] == "id"
        assert result["value"] == "msg-12345"

    def test_parse_retry_line(self):
        """Test parsing retry: line."""
        result = parse_sse_line("retry: 3000")

        assert result is not None
        assert result["type"] == "retry"
        assert result["value"] == 3000

    def test_parse_comment_line(self):
        """Test parsing comment line (starts with :)."""
        # Comments (including heartbeats) are skipped - returns None
        result = parse_sse_line(": this is a comment")
        assert result is None

        result = parse_sse_line(": heartbeat")
        assert result is None

    def test_parse_empty_line(self):
        """Test that empty lines return None."""
        assert parse_sse_line("") is None
        assert parse_sse_line("   ") is None

    def test_parse_unknown_field(self):
        """Test parsing unknown field."""
        # Unknown fields (not event:, data:, id:, retry:) are skipped
        result = parse_sse_line("unknown: value")
        assert result is None


class TestParseSSEStream:
    """Tests for parse_sse_stream function."""

    def test_parse_simple_stream(self):
        """Test parsing a simple SSE stream."""
        lines = [
            "event: stream_start",
            'data: {"session_id": "123"}',
            "",
            "event: stream_chunk",
            'data: {"content": "Hello"}',
            "",
        ]

        events = list(parse_sse_stream(iter(lines)))

        assert len(events) == 2
        assert events[0]["event"] == "stream_start"
        assert events[0]["data"]["session_id"] == "123"
        assert events[1]["event"] == "stream_chunk"
        assert events[1]["data"]["content"] == "Hello"

    def test_parse_stream_without_empty_lines(self):
        """Test parsing stream where events are delimited by event: lines."""
        lines = [
            "event: stream_chunk",
            'data: {"content": "A"}',
            "event: stream_chunk",
            'data: {"content": "B"}',
        ]

        events = list(parse_sse_stream(iter(lines)))

        assert len(events) == 2
        assert events[0]["data"]["content"] == "A"
        assert events[1]["data"]["content"] == "B"

    def test_parse_stream_ignores_comments(self):
        """Test that comments are ignored in stream."""
        lines = [
            ": keep-alive",
            "event: stream_chunk",
            'data: {"content": "test"}',
        ]

        events = list(parse_sse_stream(iter(lines)))

        assert len(events) == 1
        assert events[0]["data"]["content"] == "test"

    def test_parse_stream_handles_data_only(self):
        """Test parsing data without preceding event line."""
        lines = [
            'data: {"content": "no event"}',
        ]

        events = list(parse_sse_stream(iter(lines)))

        assert len(events) == 1
        # Data without event line defaults to "message" event type
        assert events[0]["event"] == "message"
        assert events[0]["data"]["content"] == "no event"

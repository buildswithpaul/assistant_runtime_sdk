#!/usr/bin/env python3
"""
Streaming Chat Example - FACL SDK

This example demonstrates comprehensive handling of all SSE event types
during a streaming chat session.

Usage:
    python streaming_chat.py

Environment Variables:
    FACL_TENANT_ID: Your FACL tenant ID
    FACL_TENANT_SECRET: Your FACL tenant secret
"""

import os
import json
from facl import FACLClient, SSEEventType


class ChatHandler:
    """Handler for streaming chat events."""

    def __init__(self):
        self.full_response = ""
        self.tokens_used = 0
        self.model_id = None
        self.tools_called = []
        self.thinking_content = []

    def handle_event(self, event: dict) -> bool:
        """
        Handle a single SSE event.

        Returns False when stream should end.
        """
        event_type = event["event"]
        data = event["data"]

        # Dispatch to specific handler
        handler = getattr(self, f"on_{event_type}", self.on_unknown)
        return handler(data)

    def on_stream_start(self, data: dict) -> bool:
        """Handle stream_start event."""
        print(f"[Started] Session: {data.get('session_id')}")
        print(f"[Model] {data.get('model_id')}")
        print()
        return True

    def on_model_fallback(self, data: dict) -> bool:
        """Handle model_fallback event (auto mode)."""
        self.model_id = data.get("selected")
        if data.get("fallback_attempted"):
            print(f"[Fallback] Using {data['selected']} instead of {data['original']}")
        return True

    def on_thinking(self, data: dict) -> bool:
        """Handle thinking event (extended thinking models)."""
        content = data.get("content", "")
        self.thinking_content.append(content)
        # Optionally show thinking indicator
        print("[Thinking...]", end="\r")
        return True

    def on_stream_chunk(self, data: dict) -> bool:
        """Handle stream_chunk event - main content."""
        content = data.get("content", "")
        self.full_response += content
        print(content, end="", flush=True)
        return True

    def on_tool_call_start(self, data: dict) -> bool:
        """Handle tool_call_start event."""
        tool_name = data.get("tool_name")
        args = data.get("arguments", {})
        print(f"\n[Tool] Calling {tool_name}...")
        print(f"  Arguments: {json.dumps(args, indent=2)}")
        return True

    def on_tool_call_result(self, data: dict) -> bool:
        """Handle tool_call_result event."""
        tool_name = data.get("tool_name")
        success = data.get("success", False)
        duration = data.get("duration_ms", 0)

        status = "OK" if success else "FAILED"
        print(f"[Tool] {tool_name}: {status} ({duration}ms)")

        self.tools_called.append({
            "name": tool_name,
            "success": success,
            "duration_ms": duration,
        })
        return True

    def on_approval_required(self, data: dict) -> bool:
        """Handle approval_required event (HITL)."""
        tool_name = data.get("tool_name")
        reason = data.get("reason", "No reason provided")
        timeout = data.get("timeout_seconds", 60)

        print(f"\n[APPROVAL REQUIRED]")
        print(f"  Tool: {tool_name}")
        print(f"  Reason: {reason}")
        print(f"  Timeout: {timeout}s")
        print(f"  Arguments: {json.dumps(data.get('arguments', {}), indent=2)}")

        # In a real app, you would prompt the user here
        return True

    def on_tool_cancelled(self, data: dict) -> bool:
        """Handle tool_cancelled event."""
        tool_name = data.get("tool_name")
        print(f"\n[Cancelled] Tool {tool_name} was rejected")
        return True

    def on_stream_complete(self, data: dict) -> bool:
        """Handle stream_complete event."""
        self.tokens_used = data.get("tokens_used", 0)
        self.model_id = data.get("model_id")

        print(f"\n\n{'='*50}")
        print(f"[Complete]")
        print(f"  Tokens used: {self.tokens_used}")
        print(f"  Tokens actual: {data.get('tokens_actual', 0)}")
        print(f"  Model: {self.model_id}")
        if self.tools_called:
            print(f"  Tools called: {len(self.tools_called)}")
        print(f"{'='*50}")

        return False  # End stream

    def on_stream_error(self, data: dict) -> bool:
        """Handle stream_error event."""
        error = data.get("error", "Unknown error")
        error_code = data.get("error_code", "UNKNOWN")

        print(f"\n[Error] {error}")
        print(f"  Code: {error_code}")

        return False  # End stream

    def on_rate_limited(self, data: dict) -> bool:
        """Handle rate_limited event."""
        retry_after = data.get("retry_after", 60)
        models_checked = data.get("models_checked", [])

        print(f"\n[Rate Limited]")
        print(f"  Retry after: {retry_after}s")
        print(f"  Models checked: {', '.join(models_checked)}")

        return False  # End stream

    def on_unknown(self, data: dict) -> bool:
        """Handle unknown event types."""
        print(f"\n[Unknown event] {data}")
        return True


def main():
    # Get credentials
    tenant_id = os.environ.get("FACL_TENANT_ID")
    tenant_secret = os.environ.get("FACL_TENANT_SECRET")

    if not tenant_id or not tenant_secret:
        print("Error: Set FACL_TENANT_ID and FACL_TENANT_SECRET")
        return

    # Create client
    client = FACLClient(
        tenant_id=tenant_id,
        tenant_secret=tenant_secret,
    )

    # Example message that might trigger tools
    message = """
    Can you help me understand the current weather and suggest
    what I should wear today? Also, what time is it?
    """

    print("Starting comprehensive streaming example...")
    print(f"\nUser: {message.strip()}\n")
    print("Assistant: ", end="")

    # Create handler
    handler = ChatHandler()

    # Stream chat
    for event in client.stream_chat(
        session_id="streaming-example-001",
        message=message,
        user_id="example@user.com",
        model_id="auto",
    ):
        if not handler.handle_event(event):
            break  # Terminal event received

    # Print summary
    if handler.thinking_content:
        print(f"\nThinking content: {len(handler.thinking_content)} chunks")

    print(f"\nFull response length: {len(handler.full_response)} chars")


if __name__ == "__main__":
    main()

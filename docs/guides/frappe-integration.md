# Frappe Integration Guide

This guide shows how to integrate the Assistant Runtime SDK into Frappe Framework applications.

## Overview

While the Assistant Runtime SDK is framework-agnostic, it integrates seamlessly with Frappe applications. This guide covers:

- Creating a Frappe-aware client wrapper
- Using Frappe settings and logging
- Background job integration
- Realtime (Socket.IO) streaming

## Installation

Add `assistant_runtime_sdk` to your app's dependencies in `pyproject.toml`:

```toml
[project]
dependencies = [
    "assistant_runtime_sdk>=0.1.0",
    # ... other dependencies
]
```

Then install:

```bash
bench setup requirements
# or
pip install assistant_runtime_sdk
```

## Basic Integration

### Creating a Frappe Client Wrapper

Create a thin adapter that uses Frappe's settings and logging:

```python
# my_app/ar_client.py
import frappe
from assistant_runtime_sdk import AssistantRuntimeClient as BaseAssistantRuntimeClient
from assistant_runtime_sdk import get_terms as base_get_terms
from assistant_runtime_sdk import register_tenant as base_register_tenant


class FrappeLogger:
    """Adapter to use Frappe's logging with the Assistant Runtime SDK."""

    def error(self, msg, *args, **kwargs):
        category = kwargs.get("category", "AR")
        frappe.log_error(msg, category)

    def warning(self, msg, *args, **kwargs):
        frappe.logger().warning(msg)

    def info(self, msg, *args, **kwargs):
        frappe.logger().info(msg)

    def debug(self, msg, *args, **kwargs):
        frappe.logger().debug(msg)


def get_ar_client() -> BaseAssistantRuntimeClient | None:
    """Factory function to get a configured Assistant Runtime client from Frappe settings."""

    settings = frappe.get_single("My App Settings")

    if settings.registration_status != "Registered":
        frappe.throw("Assistant Runtime not configured. Please register first.")
        return None

    return BaseAssistantRuntimeClient(
        tenant_id=settings.tenant_id,
        tenant_secret=settings.get_password("tenant_secret"),
        ar_url=settings.ar_url or "https://ar.example.com",
        logger=FrappeLogger()
    )


# Re-export standalone functions
def get_terms(ar_url: str = None):
    """Get Assistant Runtime terms and conditions."""
    url = ar_url or frappe.get_single("My App Settings").ar_url
    return base_get_terms(url or "https://ar.example.com")


def register_tenant(**kwargs):
    """Register a new tenant with Assistant Runtime."""
    settings = frappe.get_single("My App Settings")
    return base_register_tenant(
        ar_url=settings.ar_url or "https://ar.example.com",
        **kwargs
    )
```

### Settings DocType

Create a DocType to store Assistant Runtime credentials:

```python
# my_app/doctype/my_app_settings/my_app_settings.py
import frappe
from frappe.model.document import Document


class MyAppSettings(Document):
    def validate(self):
        if self.tenant_secret:
            # Validate credentials by testing API
            from my_app.ar_client import get_ar_client
            try:
                client = BaseAssistantRuntimeClient(
                    tenant_id=self.tenant_id,
                    tenant_secret=self.get_password("tenant_secret"),
                    ar_url=self.ar_url
                )
                client.get_tenant_info()
            except Exception as e:
                frappe.throw(f"Invalid Assistant Runtime credentials: {e}")
```

## API Endpoint Integration

### Whitelisted API Methods

```python
# my_app/api.py
import frappe
from my_app.ar_client import get_ar_client


@frappe.whitelist()
def list_models():
    """List available AI models."""
    client = get_ar_client()
    if not client:
        frappe.throw("Assistant Runtime not configured")

    return client.list_available_models()


@frappe.whitelist()
def get_usage():
    """Get usage dashboard data."""
    client = get_ar_client()
    if not client:
        frappe.throw("Assistant Runtime not configured")

    return client.get_usage_dashboard()


@frappe.whitelist()
def send_message(session_id: str, message: str, context: dict = None):
    """Send a chat message and return the response."""
    client = get_ar_client()
    if not client:
        frappe.throw("Assistant Runtime not configured")

    user_id = frappe.session.user
    full_response = ""

    for event in client.stream_chat(
        session_id=session_id,
        message=message,
        user_id=user_id,
        context=context,
        model_id="auto"
    ):
        if event["event"] == "stream_chunk":
            full_response += event["data"].get("content", "")
        elif event["event"] == "stream_error":
            frappe.throw(event["data"].get("error", "Unknown error"))

    return {"response": full_response}
```

## Real-time Streaming with Socket.IO

### Server-Side Streaming

```python
# my_app/realtime.py
import frappe
from frappe.realtime import emit_via_redis
from my_app.ar_client import get_ar_client


def stream_to_user(session_id: str, message: str, user: str, socket_room: str):
    """Stream Assistant Runtime response to user via Socket.IO."""

    client = get_ar_client()
    if not client:
        emit_via_redis(socket_room, {
            "event": "error",
            "data": {"error": "Assistant Runtime not configured"}
        })
        return

    try:
        for event in client.stream_chat(
            session_id=session_id,
            message=message,
            user_id=user,
            model_id="auto"
        ):
            # Forward event to client via Socket.IO
            emit_via_redis(socket_room, {
                "event": event["event"],
                "data": event["data"]
            })

            if event["event"] in ("stream_complete", "stream_error"):
                break

    except Exception as e:
        emit_via_redis(socket_room, {
            "event": "error",
            "data": {"error": str(e)}
        })


@frappe.whitelist()
def start_stream(session_id: str, message: str):
    """Start a streaming chat in a background job."""

    user = frappe.session.user
    socket_room = f"ar_stream_{user}_{session_id}"

    # Enqueue background job for streaming
    frappe.enqueue(
        stream_to_user,
        session_id=session_id,
        message=message,
        user=user,
        socket_room=socket_room,
        queue="default",
        timeout=300,  # 5 minute timeout
        is_async=True
    )

    return {"room": socket_room}
```

### Client-Side (JavaScript)

```javascript
// my_app/public/js/chat.js
frappe.provide("my_app.chat");

my_app.chat.startStream = function(sessionId, message, callbacks) {
    return new Promise((resolve, reject) => {
        let fullResponse = "";

        // Start the stream
        frappe.call({
            method: "my_app.realtime.start_stream",
            args: {
                session_id: sessionId,
                message: message
            },
            callback: function(r) {
                const room = r.message.room;

                // Subscribe to Socket.IO room
                frappe.realtime.on(room, function(data) {
                    const event = data.event;
                    const eventData = data.data;

                    switch(event) {
                        case "stream_start":
                            if (callbacks.onStart) {
                                callbacks.onStart(eventData);
                            }
                            break;

                        case "stream_chunk":
                            const content = eventData.content || "";
                            fullResponse += content;
                            if (callbacks.onChunk) {
                                callbacks.onChunk(content, fullResponse);
                            }
                            break;

                        case "tool_call_start":
                            if (callbacks.onToolStart) {
                                callbacks.onToolStart(eventData);
                            }
                            break;

                        case "tool_call_result":
                            if (callbacks.onToolResult) {
                                callbacks.onToolResult(eventData);
                            }
                            break;

                        case "stream_complete":
                            frappe.realtime.off(room);
                            if (callbacks.onComplete) {
                                callbacks.onComplete(eventData, fullResponse);
                            }
                            resolve(fullResponse);
                            break;

                        case "stream_error":
                        case "error":
                            frappe.realtime.off(room);
                            const error = eventData.error || "Unknown error";
                            if (callbacks.onError) {
                                callbacks.onError(error);
                            }
                            reject(new Error(error));
                            break;
                    }
                });
            },
            error: function(err) {
                reject(err);
            }
        });
    });
};

// Usage example
my_app.chat.startStream("session-123", "Hello!", {
    onStart: (data) => console.log("Started with model:", data.model_id),
    onChunk: (chunk, full) => {
        // Update UI with chunk
        document.getElementById("response").textContent = full;
    },
    onToolStart: (data) => {
        frappe.show_alert(`Using tool: ${data.tool_name}`, 3);
    },
    onComplete: (data, response) => {
        console.log(`Complete. Tokens: ${data.tokens_used}`);
    },
    onError: (error) => {
        frappe.msgprint({
            title: "Error",
            indicator: "red",
            message: error
        });
    }
}).then(response => {
    console.log("Final response:", response);
});
```

## Background Jobs

### Long-Running Tasks

```python
# my_app/tasks.py
import frappe
from my_app.ar_client import get_ar_client


def process_bulk_queries(queries: list, user: str):
    """Process multiple queries in a background job."""

    client = get_ar_client()
    results = []

    for i, query in enumerate(queries):
        try:
            response = ""
            for event in client.stream_chat(
                session_id=f"bulk-{frappe.generate_hash(length=8)}",
                message=query["message"],
                user_id=user,
                context=query.get("context"),
                model_id="auto"
            ):
                if event["event"] == "stream_chunk":
                    response += event["data"].get("content", "")
                elif event["event"] == "stream_complete":
                    results.append({
                        "query": query["message"],
                        "response": response,
                        "tokens": event["data"].get("tokens_used")
                    })
                    break

            # Update progress
            frappe.publish_progress(
                percent=(i + 1) / len(queries) * 100,
                title="Processing Queries",
                description=f"Processed {i + 1} of {len(queries)}"
            )

        except Exception as e:
            results.append({
                "query": query["message"],
                "error": str(e)
            })

        # Commit after each query to avoid long transactions
        frappe.db.commit()

    return results


@frappe.whitelist()
def start_bulk_processing(queries: list):
    """Start bulk query processing in background."""

    job = frappe.enqueue(
        process_bulk_queries,
        queries=queries,
        user=frappe.session.user,
        queue="long",
        timeout=3600,  # 1 hour
        is_async=True
    )

    return {"job_id": job.id}
```

## User Registration

### Automatic User Registration with Assistant Runtime

```python
# my_app/hooks.py
# Add to on_login hook

def register_user_with_ar(login_manager):
    """Register user with Assistant Runtime on login."""

    from my_app.ar_client import get_ar_client

    try:
        client = get_ar_client()
        if not client:
            return

        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)

        client.register_user(
            user_id=user,
            display_name=user_doc.full_name,
            custom_instructions=None  # Can be set from user preferences
        )

    except Exception as e:
        frappe.log_error(f"Assistant Runtime user registration failed: {e}")
```

```python
# hooks.py
on_login = "my_app.hooks.register_user_with_ar"
```

## Error Handling in Frappe Context

```python
# my_app/utils.py
import frappe
from assistant_runtime_sdk import (
    ARError,
    ARAuthenticationError,
    ARRateLimitError,
    ARAPIError,
)


def handle_ar_error(func):
    """Decorator to handle Assistant Runtime errors in Frappe context."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except ARAuthenticationError as e:
            frappe.log_error(str(e), "AR Auth Error")
            frappe.throw(
                "AI service authentication failed. Please check settings.",
                title="Configuration Error"
            )

        except ARRateLimitError as e:
            frappe.log_error(str(e), "AR Rate Limit")
            frappe.throw(
                f"AI service is busy. Please try again in {e.retry_after} seconds.",
                title="Service Busy"
            )

        except ARAPIError as e:
            frappe.log_error(str(e), "Assistant Runtime API Error")
            if e.status_code == 403:
                frappe.throw(
                    "You don't have permission for this operation.",
                    title="Permission Denied"
                )
            else:
                frappe.throw(
                    "AI service error. Please try again later.",
                    title="Service Error"
                )

        except ARError as e:
            frappe.log_error(str(e), "AR Error")
            frappe.throw(
                "An error occurred with the AI service.",
                title="Error"
            )

    return wrapper


# Usage
@frappe.whitelist()
@handle_ar_error
def ai_query(message):
    client = get_ar_client()
    # ... use client
```

## Testing

### Unit Tests

```python
# my_app/tests/test_ar.py
import frappe
import unittest
from unittest.mock import patch, MagicMock


class TestARIntegration(unittest.TestCase):
    def setUp(self):
        self.test_user = "test@example.com"

    @patch("my_app.ar_client.BaseAssistantRuntimeClient")
    def test_list_models(self, mock_client):
        """Test listing models through Frappe API."""
        mock_instance = MagicMock()
        mock_instance.list_available_models.return_value = {
            "models": [{"model_id": "test-model"}]
        }
        mock_client.return_value = mock_instance

        from my_app.api import list_models
        result = list_models()

        self.assertIn("models", result)
        self.assertEqual(len(result["models"]), 1)

    @patch("my_app.ar_client.BaseAssistantRuntimeClient")
    def test_stream_chat(self, mock_client):
        """Test streaming chat."""
        mock_instance = MagicMock()
        mock_instance.stream_chat.return_value = iter([
            {"event": "stream_chunk", "data": {"content": "Hello"}},
            {"event": "stream_complete", "data": {"tokens_used": 10}},
        ])
        mock_client.return_value = mock_instance

        from my_app.api import send_message
        result = send_message("test-session", "Hi")

        self.assertEqual(result["response"], "Hello")
```

## Security Best Practices

1. **Store secrets securely**: Use Frappe's password field type
2. **Validate user access**: Check permissions before API calls
3. **Rate limit user requests**: Use Frappe's rate limiting
4. **Log errors appropriately**: Use frappe.log_error for tracking
5. **Sanitize user input**: Validate messages before sending to Assistant Runtime

```python
@frappe.whitelist()
def send_message(session_id: str, message: str):
    # Validate permissions
    if not frappe.has_permission("My DocType", "read"):
        frappe.throw("Permission denied")

    # Validate input
    if not message or len(message) > 10000:
        frappe.throw("Invalid message")

    # Rate limit
    rate_limit_key = f"ar_rate_{frappe.session.user}"
    if frappe.cache().get(rate_limit_key):
        frappe.throw("Too many requests. Please wait.")
    frappe.cache().set(rate_limit_key, 1, expires_in_sec=2)

    # Proceed with API call
    client = get_ar_client()
    # ...
```

## Next Steps

- [Getting Started](getting-started.md) - Basic SDK usage
- [Streaming Guide](streaming.md) - SSE event handling
- [API Reference](../api/client.md) - Complete API documentation

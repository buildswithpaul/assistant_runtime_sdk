#!/usr/bin/env python3
"""
Frappe Integration Example - FACL SDK

This example demonstrates how to integrate the FACL SDK with
Frappe Framework applications.

Note: This file is meant to be used within a Frappe application,
not as a standalone script.

Structure:
    my_app/
    ├── my_app/
    │   ├── facl_client.py    # This file
    │   ├── api.py            # Whitelisted API methods
    │   └── realtime.py       # Socket.IO streaming
    └── pyproject.toml        # Add facl dependency
"""

# =============================================================================
# facl_client.py - Client factory and adapters
# =============================================================================

import frappe
from facl import FACLClient as BaseFACLClient
from facl import (
    get_terms as base_get_terms,
    register_tenant as base_register_tenant,
    FACLError,
    FACLAuthenticationError,
    FACLRateLimitError,
)


class FrappeLogger:
    """Adapter to use Frappe's logging with the FACL SDK."""

    def error(self, msg, *args, **kwargs):
        category = kwargs.get("category", "FACL")
        frappe.log_error(msg, category)

    def warning(self, msg, *args, **kwargs):
        frappe.logger().warning(msg)

    def info(self, msg, *args, **kwargs):
        frappe.logger().info(msg)

    def debug(self, msg, *args, **kwargs):
        frappe.logger().debug(msg)


def get_facl_client() -> BaseFACLClient:
    """
    Factory function to get a configured FACL client.

    Returns:
        Configured FACLClient instance

    Raises:
        frappe.ValidationError: If FACL is not configured
    """
    settings = frappe.get_single("My App Settings")

    if settings.registration_status != "Registered":
        frappe.throw(
            "FACL is not configured. Please register first.",
            title="Configuration Error"
        )

    return BaseFACLClient(
        tenant_id=settings.tenant_id,
        tenant_secret=settings.get_password("tenant_secret"),
        facl_url=settings.facl_url or "https://facl.frappe.cloud",
        logger=FrappeLogger(),
    )


def get_terms(facl_url: str = None):
    """Get FACL terms and conditions."""
    url = facl_url or frappe.get_single("My App Settings").facl_url
    return base_get_terms(url or "https://facl.frappe.cloud")


def register_tenant(**kwargs):
    """Register a new tenant with FACL."""
    settings = frappe.get_single("My App Settings")
    return base_register_tenant(
        facl_url=settings.facl_url or "https://facl.frappe.cloud",
        **kwargs
    )


# =============================================================================
# api.py - Whitelisted API methods
# =============================================================================

@frappe.whitelist()
def list_models():
    """List available AI models."""
    client = get_facl_client()
    return client.list_available_models()


@frappe.whitelist()
def get_usage():
    """Get usage dashboard data."""
    client = get_facl_client()
    return client.get_usage_dashboard()


@frappe.whitelist()
def send_message(session_id: str, message: str, context: dict = None):
    """
    Send a chat message and return the complete response.

    Args:
        session_id: Conversation session ID
        message: User's message
        context: Optional page context

    Returns:
        dict with response and metadata
    """
    # Validate
    if not message or len(message) > 10000:
        frappe.throw("Invalid message")

    client = get_facl_client()
    user_id = frappe.session.user

    full_response = ""
    tokens_used = 0
    model_id = None

    try:
        for event in client.stream_chat(
            session_id=session_id,
            message=message,
            user_id=user_id,
            context=context,
            model_id="auto",
        ):
            if event["event"] == "stream_chunk":
                full_response += event["data"].get("content", "")

            elif event["event"] == "stream_complete":
                tokens_used = event["data"].get("tokens_used", 0)
                model_id = event["data"].get("model_id")

            elif event["event"] == "stream_error":
                frappe.throw(event["data"].get("error", "Unknown error"))

            elif event["event"] == "rate_limited":
                retry_after = event["data"].get("retry_after", 60)
                frappe.throw(f"Service busy. Please try again in {retry_after} seconds.")

    except FACLAuthenticationError:
        frappe.log_error("FACL authentication failed", "FACL Auth Error")
        frappe.throw("AI service configuration error. Contact administrator.")

    except FACLRateLimitError as e:
        frappe.throw(f"Service busy. Please try again in {e.retry_after} seconds.")

    except FACLError as e:
        frappe.log_error(str(e), "FACL Error")
        frappe.throw("AI service error. Please try again later.")

    return {
        "response": full_response,
        "tokens_used": tokens_used,
        "model_id": model_id,
    }


@frappe.whitelist()
def register_current_user():
    """Register the current user with FACL."""
    client = get_facl_client()
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)

    result = client.register_user(
        user_id=user,
        display_name=user_doc.full_name,
        custom_instructions=None,
    )

    return {
        "success": True,
        "user_id": result.get("user_id"),
    }


# =============================================================================
# realtime.py - Socket.IO streaming
# =============================================================================

def stream_to_user(session_id: str, message: str, user: str, socket_room: str):
    """
    Stream FACL response to user via Socket.IO.

    This function should be called via frappe.enqueue() for background execution.
    """
    from frappe.realtime import emit_via_redis

    try:
        client = get_facl_client()
    except Exception as e:
        emit_via_redis(socket_room, {
            "event": "error",
            "data": {"error": str(e)}
        })
        return

    try:
        for event in client.stream_chat(
            session_id=session_id,
            message=message,
            user_id=user,
            model_id="auto",
        ):
            # Forward event to client
            emit_via_redis(socket_room, {
                "event": event["event"],
                "data": event["data"]
            })

            # Stop on terminal events
            if event["event"] in ("stream_complete", "stream_error", "rate_limited"):
                break

    except Exception as e:
        emit_via_redis(socket_room, {
            "event": "error",
            "data": {"error": str(e)}
        })


@frappe.whitelist()
def start_stream(session_id: str, message: str):
    """
    Start a streaming chat in a background job.

    Returns:
        dict with socket room name to subscribe to
    """
    # Validate
    if not message or len(message) > 10000:
        frappe.throw("Invalid message")

    user = frappe.session.user
    socket_room = f"facl_stream_{user}_{session_id}"

    # Enqueue background job
    frappe.enqueue(
        stream_to_user,
        session_id=session_id,
        message=message,
        user=user,
        socket_room=socket_room,
        queue="default",
        timeout=300,
        is_async=True,
    )

    return {"room": socket_room}


# =============================================================================
# hooks.py - Frappe hooks integration
# =============================================================================

def on_login(login_manager):
    """
    Register user with FACL on login.

    Add to hooks.py:
        on_login = "my_app.facl_client.on_login"
    """
    try:
        client = get_facl_client()
        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)

        client.register_user(
            user_id=user,
            display_name=user_doc.full_name,
        )
    except Exception as e:
        # Don't block login on FACL errors
        frappe.log_error(f"FACL user registration failed: {e}", "FACL")


# =============================================================================
# JavaScript client-side integration
# =============================================================================
"""
// my_app/public/js/chat.js

frappe.provide("my_app.chat");

my_app.chat.sendMessage = function(sessionId, message, callbacks) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: "my_app.api.send_message",
            args: {
                session_id: sessionId,
                message: message
            },
            callback: function(r) {
                if (r.message) {
                    if (callbacks.onComplete) {
                        callbacks.onComplete(r.message);
                    }
                    resolve(r.message);
                }
            },
            error: function(err) {
                if (callbacks.onError) {
                    callbacks.onError(err);
                }
                reject(err);
            }
        });
    });
};

my_app.chat.startStream = function(sessionId, message, callbacks) {
    return new Promise((resolve, reject) => {
        let fullResponse = "";

        frappe.call({
            method: "my_app.realtime.start_stream",
            args: {
                session_id: sessionId,
                message: message
            },
            callback: function(r) {
                const room = r.message.room;

                frappe.realtime.on(room, function(data) {
                    const event = data.event;
                    const eventData = data.data;

                    switch(event) {
                        case "stream_chunk":
                            fullResponse += eventData.content || "";
                            if (callbacks.onChunk) {
                                callbacks.onChunk(eventData.content, fullResponse);
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

// Usage:
my_app.chat.startStream("session-123", "Hello!", {
    onChunk: (chunk, full) => {
        document.getElementById("response").textContent = full;
    },
    onComplete: (data, response) => {
        console.log("Complete:", data.tokens_used, "tokens");
    },
    onError: (error) => {
        frappe.msgprint({
            title: "Error",
            indicator: "red",
            message: error
        });
    }
});
"""

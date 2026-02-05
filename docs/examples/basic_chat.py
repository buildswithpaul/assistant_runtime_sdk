#!/usr/bin/env python3
"""
Basic Chat Example - FACL SDK

This example demonstrates the simplest way to use the FACL SDK
to send a message and receive a streaming response.

Usage:
    python basic_chat.py

Environment Variables:
    FACL_TENANT_ID: Your FACL tenant ID
    FACL_TENANT_SECRET: Your FACL tenant secret
    FACL_URL: FACL server URL (optional, defaults to https://facl.frappe.cloud)
"""

import os
from facl import FACLClient


def main():
    # Get credentials from environment
    tenant_id = os.environ.get("FACL_TENANT_ID")
    tenant_secret = os.environ.get("FACL_TENANT_SECRET")
    facl_url = os.environ.get("FACL_URL", "https://facl.frappe.cloud")

    if not tenant_id or not tenant_secret:
        print("Error: Set FACL_TENANT_ID and FACL_TENANT_SECRET environment variables")
        return

    # Create client
    client = FACLClient(
        tenant_id=tenant_id,
        tenant_secret=tenant_secret,
        facl_url=facl_url,
    )

    # Check available models
    print("Checking available models...")
    models = client.list_available_models()
    if models:
        model_count = len(models.get("models", []))
        print(f"Found {model_count} available models")

        auto_mode = models.get("auto_mode", {})
        if auto_mode.get("enabled"):
            print(f"Auto mode available with {auto_mode.get('fallback_chain_length')} models")
    else:
        print("Failed to get models")
        return

    # Start a chat
    print("\n" + "=" * 50)
    print("Starting chat...")
    print("=" * 50 + "\n")

    session_id = "example-session-001"
    user_id = "example@user.com"
    message = "Hello! What can you help me with today?"

    print(f"User: {message}\n")
    print("Assistant: ", end="", flush=True)

    # Stream the response
    for event in client.stream_chat(
        session_id=session_id,
        message=message,
        user_id=user_id,
        model_id="auto",  # Use auto-model selection
    ):
        event_type = event["event"]
        data = event["data"]

        if event_type == "stream_chunk":
            # Print content as it arrives
            content = data.get("content", "")
            print(content, end="", flush=True)

        elif event_type == "stream_complete":
            # Print final stats
            print(f"\n\n[Tokens used: {data.get('tokens_used')}]")
            print(f"[Model: {data.get('model_id')}]")

        elif event_type == "stream_error":
            print(f"\nError: {data.get('error')}")

        elif event_type == "model_fallback":
            if data.get("fallback_attempted"):
                print(f"\n[Fell back to {data.get('selected')}]", end="")


if __name__ == "__main__":
    main()

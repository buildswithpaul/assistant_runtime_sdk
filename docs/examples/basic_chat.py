#!/usr/bin/env python3
"""
Basic Chat Example - Assistant Runtime SDK

This example demonstrates the simplest way to use the Assistant Runtime SDK
to send a message and receive a streaming response.

Usage:
    python basic_chat.py

Environment Variables:
    AR_TENANT_ID: Your Assistant Runtime tenant ID
    AR_TENANT_SECRET: Your Assistant Runtime tenant secret
    AR_URL: Assistant Runtime server URL (optional, defaults to https://ar.example.com)
"""

import os
from assistant_runtime_sdk import AssistantRuntimeClient


def main():
    # Get credentials from environment
    tenant_id = os.environ.get("AR_TENANT_ID")
    tenant_secret = os.environ.get("AR_TENANT_SECRET")
    ar_url = os.environ.get("AR_URL", "https://ar.example.com")

    if not tenant_id or not tenant_secret:
        print("Error: Set AR_TENANT_ID and AR_TENANT_SECRET environment variables")
        return

    # Create client
    client = AssistantRuntimeClient(
        tenant_id=tenant_id,
        tenant_secret=tenant_secret,
        ar_url=ar_url,
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

#!/usr/bin/env python3
"""
Async Chat Example - FACL SDK

This example demonstrates using the AsyncFACLClient for asynchronous
chat streaming with concurrent operations.

Usage:
    python async_chat.py

Requirements:
    pip install facl[async]

Environment Variables:
    FACL_TENANT_ID: Your FACL tenant ID
    FACL_TENANT_SECRET: Your FACL tenant secret
"""

import os
import asyncio
from facl import AsyncFACLClient


async def stream_chat(client, session_id: str, message: str, user_id: str):
    """Stream a single chat message."""
    print(f"\n[Session {session_id}] User: {message}")
    print(f"[Session {session_id}] Assistant: ", end="", flush=True)

    full_response = ""

    async for event in client.stream_chat(
        session_id=session_id,
        message=message,
        user_id=user_id,
        model_id="auto",
    ):
        event_type = event["event"]
        data = event["data"]

        if event_type == "stream_chunk":
            content = data.get("content", "")
            full_response += content
            print(content, end="", flush=True)

        elif event_type == "stream_complete":
            tokens = data.get("tokens_used", 0)
            print(f"\n[Session {session_id}] Complete ({tokens} tokens)")

        elif event_type == "stream_error":
            print(f"\n[Session {session_id}] Error: {data.get('error')}")

    return full_response


async def concurrent_api_calls(client):
    """Demonstrate concurrent API calls."""
    print("\nRunning concurrent API calls...")

    # Run multiple API calls concurrently
    models_task = client.list_available_models()
    tenant_task = client.get_tenant_info()
    usage_task = client.get_usage_dashboard()

    models, tenant, usage = await asyncio.gather(
        models_task,
        tenant_task,
        usage_task,
        return_exceptions=True,
    )

    # Process results
    if isinstance(models, dict):
        print(f"  Models: {len(models.get('models', []))} available")
    else:
        print(f"  Models: Error - {models}")

    if isinstance(tenant, dict):
        print(f"  Tenant: {tenant.get('status', 'unknown')}")
    else:
        print(f"  Tenant: Error - {tenant}")

    if isinstance(usage, dict):
        print(f"  Usage: {usage.get('used', 0)}/{usage.get('quota', 0)} tokens")
    else:
        print(f"  Usage: Error - {usage}")


async def multiple_user_check(client, user_ids: list):
    """Check multiple users concurrently."""
    print(f"\nChecking {len(user_ids)} users concurrently...")

    tasks = [client.get_user_auth_status(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for user_id, result in zip(user_ids, results):
        if isinstance(result, dict):
            ready = result.get("ready_for_streaming", False)
            status = "Ready" if ready else "Not ready"
            print(f"  {user_id}: {status}")
        else:
            print(f"  {user_id}: Error - {result}")


async def parallel_chats(client, messages: list, user_id: str):
    """Run multiple chat sessions in parallel."""
    print("\nRunning parallel chat sessions...")

    tasks = [
        stream_chat(client, f"parallel-{i}", msg, user_id)
        for i, msg in enumerate(messages)
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    print("\n\nParallel chat results:")
    for i, response in enumerate(responses):
        if isinstance(response, str):
            preview = response[:100] + "..." if len(response) > 100 else response
            print(f"  Chat {i}: {preview}")
        else:
            print(f"  Chat {i}: Error - {response}")


async def rate_limited_operations(client, operations: int, max_concurrent: int = 5):
    """Demonstrate rate-limited concurrent operations."""
    print(f"\nRunning {operations} operations with max {max_concurrent} concurrent...")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_operation(i: int):
        async with semaphore:
            try:
                result = await client.list_available_models()
                return f"Op {i}: Success"
            except Exception as e:
                return f"Op {i}: Error - {e}"

    tasks = [limited_operation(i) for i in range(operations)]
    results = await asyncio.gather(*tasks)

    success = sum(1 for r in results if "Success" in r)
    print(f"  Completed: {success}/{operations} successful")


async def main():
    # Get credentials
    tenant_id = os.environ.get("FACL_TENANT_ID")
    tenant_secret = os.environ.get("FACL_TENANT_SECRET")

    if not tenant_id or not tenant_secret:
        print("Error: Set FACL_TENANT_ID and FACL_TENANT_SECRET")
        return

    # Use async context manager
    async with AsyncFACLClient(
        tenant_id=tenant_id,
        tenant_secret=tenant_secret,
    ) as client:

        print("=" * 60)
        print("FACL Async Client Examples")
        print("=" * 60)

        # Example 1: Simple async chat
        print("\n--- Example 1: Simple Async Chat ---")
        await stream_chat(
            client,
            session_id="async-example-001",
            message="What's 2 + 2?",
            user_id="example@user.com",
        )

        # Example 2: Concurrent API calls
        print("\n--- Example 2: Concurrent API Calls ---")
        await concurrent_api_calls(client)

        # Example 3: Multiple user check
        print("\n--- Example 3: Multiple User Check ---")
        await multiple_user_check(
            client,
            ["user1@example.com", "user2@example.com", "user3@example.com"],
        )

        # Example 4: Parallel chats (be careful with rate limits!)
        print("\n--- Example 4: Parallel Chats ---")
        await parallel_chats(
            client,
            messages=[
                "Say 'Hello' only",
                "Say 'World' only",
            ],
            user_id="example@user.com",
        )

        # Example 5: Rate-limited operations
        print("\n--- Example 5: Rate-Limited Operations ---")
        await rate_limited_operations(client, operations=10, max_concurrent=3)

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

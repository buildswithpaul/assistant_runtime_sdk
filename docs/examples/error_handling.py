#!/usr/bin/env python3
"""
Error Handling Example - Assistant Runtime SDK

This example demonstrates comprehensive error handling patterns
for the Assistant Runtime SDK.

Usage:
    python error_handling.py

Environment Variables:
    AR_TENANT_ID: Your Assistant Runtime tenant ID
    AR_TENANT_SECRET: Your Assistant Runtime tenant secret
"""

import os
import time
import random
from typing import Callable, Any
from assistant_runtime_sdk import (
    AssistantRuntimeClient,
    ARError,
    ARAuthenticationError,
    ARRateLimitError,
    ARStreamError,
    ARConfigurationError,
    ARAPIError,
    ARTimeoutError,
    ARConnectionError,
)


# =============================================================================
# Retry Decorators
# =============================================================================


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential: bool = True,
    jitter: bool = True,
):
    """
    Decorator for retrying failed API calls with exponential backoff.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential: Use exponential backoff
        jitter: Add random jitter to delays
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except ARAuthenticationError:
                    # Don't retry auth errors
                    raise

                except ARRateLimitError as e:
                    # Use server-provided retry_after
                    last_exception = e
                    if attempt < max_retries:
                        delay = e.retry_after or base_delay
                        print(f"Rate limited. Waiting {delay}s... (attempt {attempt + 1})")
                        time.sleep(delay)
                        continue
                    raise

                except (ARTimeoutError, ARConnectionError) as e:
                    # Retry with exponential backoff
                    last_exception = e
                    if attempt < max_retries:
                        if exponential:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                        else:
                            delay = base_delay

                        if jitter:
                            delay += random.uniform(0, delay * 0.1)

                        print(f"Error: {e}. Retrying in {delay:.1f}s... (attempt {attempt + 1})")
                        time.sleep(delay)
                        continue
                    raise

                except ARAPIError as e:
                    # Retry only server errors (5xx)
                    last_exception = e
                    if e.status_code and e.status_code >= 500:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) if exponential else base_delay
                            print(f"Server error. Retrying in {delay:.1f}s...")
                            time.sleep(delay)
                            continue
                    raise

            raise last_exception or RuntimeError("Max retries exceeded")

        return wrapper
    return decorator


# =============================================================================
# Safe API Call Wrapper
# =============================================================================


class SafeAPIClient:
    """Wrapper around AssistantRuntimeClient with built-in error handling."""

    def __init__(self, client: AssistantRuntimeClient):
        self.client = client

    @with_retry(max_retries=3)
    def list_models(self):
        """List models with retry logic."""
        return self.client.list_available_models()

    @with_retry(max_retries=3)
    def get_user(self, user_id: str):
        """Get user with retry logic."""
        return self.client.get_user(user_id)

    def stream_chat_safe(
        self,
        session_id: str,
        message: str,
        user_id: str,
        on_chunk: Callable[[str], None] = None,
        on_error: Callable[[str], None] = None,
        max_retries: int = 2,
    ):
        """
        Stream chat with error recovery.

        Args:
            session_id: Session identifier
            message: User message
            user_id: User identifier
            on_chunk: Callback for content chunks
            on_error: Callback for errors
            max_retries: Maximum retry attempts

        Returns:
            Tuple of (full_response, metadata)
        """
        accumulated = []
        metadata = {}

        for attempt in range(max_retries + 1):
            try:
                for event in self.client.stream_chat(
                    session_id=session_id,
                    message=message,
                    user_id=user_id,
                    model_id="auto",
                ):
                    event_type = event["event"]
                    data = event["data"]

                    if event_type == "stream_chunk":
                        content = data.get("content", "")
                        accumulated.append(content)
                        if on_chunk:
                            on_chunk(content)

                    elif event_type == "stream_complete":
                        metadata = {
                            "tokens_used": data.get("tokens_used", 0),
                            "model_id": data.get("model_id"),
                            "full_response": data.get("full_response", ""),
                        }
                        return "".join(accumulated), metadata

                    elif event_type == "stream_error":
                        error_msg = data.get("error", "Unknown error")
                        if on_error:
                            on_error(error_msg)
                        raise ARStreamError(error_msg)

                    elif event_type == "rate_limited":
                        retry_after = data.get("retry_after", 60)
                        raise ARRateLimitError(
                            "All models rate limited",
                            retry_after=retry_after,
                            models_checked=data.get("models_checked", []),
                        )

                # Stream ended without complete event
                return "".join(accumulated), metadata

            except (ARConnectionError, ARStreamError) as e:
                if attempt < max_retries:
                    print(f"Stream error: {e}. Retrying...")
                    # Keep accumulated content
                    continue
                else:
                    # Return partial response
                    partial = "".join(accumulated)
                    if partial:
                        return partial, {"partial": True, "error": str(e)}
                    raise

            except ARRateLimitError as e:
                if attempt < max_retries:
                    print(f"Rate limited. Waiting {e.retry_after}s...")
                    time.sleep(e.retry_after)
                    continue
                raise

        return "".join(accumulated), metadata


# =============================================================================
# Error Categorization
# =============================================================================


def categorize_error(error: Exception) -> dict:
    """
    Categorize a AR error for user-friendly handling.

    Returns:
        Dict with:
        - category: Error category for logging
        - user_message: Message safe to show users
        - retry_allowed: Whether retry makes sense
        - retry_delay: Suggested retry delay in seconds
    """
    if isinstance(error, ARAuthenticationError):
        return {
            "category": "auth",
            "user_message": "Service configuration error. Please contact support.",
            "retry_allowed": False,
            "retry_delay": None,
        }

    elif isinstance(error, ARRateLimitError):
        return {
            "category": "rate_limit",
            "user_message": f"Service is busy. Please try again in {error.retry_after or 60} seconds.",
            "retry_allowed": True,
            "retry_delay": error.retry_after or 60,
        }

    elif isinstance(error, ARTimeoutError):
        return {
            "category": "timeout",
            "user_message": "Request timed out. Please try a shorter message.",
            "retry_allowed": True,
            "retry_delay": 5,
        }

    elif isinstance(error, ARConnectionError):
        return {
            "category": "connection",
            "user_message": "Connection error. Please check your internet and try again.",
            "retry_allowed": True,
            "retry_delay": 10,
        }

    elif isinstance(error, ARAPIError):
        if error.status_code == 404:
            return {
                "category": "not_found",
                "user_message": "The requested resource was not found.",
                "retry_allowed": False,
                "retry_delay": None,
            }
        elif error.status_code == 403:
            return {
                "category": "forbidden",
                "user_message": "You don't have permission for this action.",
                "retry_allowed": False,
                "retry_delay": None,
            }
        elif error.status_code and error.status_code >= 500:
            return {
                "category": "server_error",
                "user_message": "Service temporarily unavailable. Please try again later.",
                "retry_allowed": True,
                "retry_delay": 30,
            }
        else:
            return {
                "category": "api_error",
                "user_message": "An error occurred. Please try again.",
                "retry_allowed": True,
                "retry_delay": 5,
            }

    elif isinstance(error, ARConfigurationError):
        return {
            "category": "config",
            "user_message": "Service is not properly configured.",
            "retry_allowed": False,
            "retry_delay": None,
        }

    elif isinstance(error, ARStreamError):
        return {
            "category": "stream",
            "user_message": "Stream interrupted. Please try again.",
            "retry_allowed": True,
            "retry_delay": 2,
        }

    else:
        return {
            "category": "unknown",
            "user_message": "An unexpected error occurred.",
            "retry_allowed": True,
            "retry_delay": 5,
        }


# =============================================================================
# Example Usage
# =============================================================================


def main():
    tenant_id = os.environ.get("AR_TENANT_ID")
    tenant_secret = os.environ.get("AR_TENANT_SECRET")

    if not tenant_id or not tenant_secret:
        print("Error: Set AR_TENANT_ID and AR_TENANT_SECRET")
        return

    # Create base client
    base_client = AssistantRuntimeClient(
        tenant_id=tenant_id,
        tenant_secret=tenant_secret,
    )

    # Wrap with safe client
    client = SafeAPIClient(base_client)

    print("=" * 60)
    print("Error Handling Examples")
    print("=" * 60)

    # Example 1: Retrying API calls
    print("\n--- Example 1: API Call with Retry ---")
    try:
        models = client.list_models()
        print(f"Found {len(models.get('models', []))} models")
    except ARError as e:
        error_info = categorize_error(e)
        print(f"Category: {error_info['category']}")
        print(f"User message: {error_info['user_message']}")

    # Example 2: Safe streaming
    print("\n--- Example 2: Safe Streaming ---")

    def on_chunk(content):
        print(content, end="", flush=True)

    def on_error(error):
        print(f"\nStream error: {error}")

    try:
        response, metadata = client.stream_chat_safe(
            session_id="error-handling-example",
            message="Say 'Hello World' only",
            user_id="example@user.com",
            on_chunk=on_chunk,
            on_error=on_error,
        )

        print(f"\n\nResponse length: {len(response)}")
        print(f"Metadata: {metadata}")

    except ARError as e:
        error_info = categorize_error(e)
        print(f"\nFailed: {error_info['user_message']}")
        if error_info['retry_allowed']:
            print(f"Retry suggested in {error_info['retry_delay']}s")

    # Example 3: Error categorization demo
    print("\n--- Example 3: Error Categorization ---")

    test_errors = [
        ARAuthenticationError("Invalid signature"),
        ARRateLimitError("Rate limit", retry_after=30),
        ARTimeoutError("Connection timeout"),
        ARConnectionError("DNS resolution failed"),
        ARAPIError("Not found", status_code=404),
        ARAPIError("Server error", status_code=500),
        ARStreamError("Connection dropped"),
    ]

    for error in test_errors:
        info = categorize_error(error)
        print(f"\n{type(error).__name__}:")
        print(f"  Category: {info['category']}")
        print(f"  Message: {info['user_message']}")
        print(f"  Retry: {info['retry_allowed']} (delay: {info['retry_delay']}s)")


if __name__ == "__main__":
    main()

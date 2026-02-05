# FACL SDK Documentation

Welcome to the FACL SDK documentation. This SDK provides a Python client for integrating with [Frappe Assistant Cloud (FACL)](https://facl.frappe.cloud) - the AI-powered assistant backend for the Frappe ecosystem.

## Overview

FACL SDK is a framework-agnostic Python library that enables any Python application to:

- Stream AI chat responses with real-time SSE events
- Execute tools via MCP (Model Context Protocol) servers
- Manage conversations, users, and billing
- Use automatic model selection with cross-provider fallback

## Features

| Feature | Description |
|---------|-------------|
| **Sync & Async Clients** | Choose `FACLClient` (requests) or `AsyncFACLClient` (aiohttp) |
| **SSE Streaming** | Real-time streaming with tool execution events |
| **HMAC Authentication** | Secure request signing for all API calls |
| **Auto Model Selection** | Intelligent routing with provider fallback |
| **Full API Coverage** | Chat, billing, conversations, users, prompts |
| **Type Hints** | Complete type annotations for IDE support |

## Installation

```bash
# Basic installation (sync client only)
pip install facl

# With async support
pip install facl[async]

# Development installation
pip install facl[dev]
```

## Quick Example

```python
from facl import FACLClient

client = FACLClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-secret",
    facl_url="https://facl.frappe.cloud"
)

# Stream a chat response
for event in client.stream_chat(
    session_id="session-123",
    message="What can you help me with?",
    user_id="user@example.com",
    model_id="auto"
):
    if event["event"] == "stream_chunk":
        print(event["data"].get("content", ""), end="", flush=True)
```

## Documentation Structure

### Guides

Step-by-step guides for common tasks:

- [Getting Started](guides/getting-started.md) - Installation and first steps
- [Authentication](guides/authentication.md) - HMAC signature authentication
- [Streaming](guides/streaming.md) - Real-time SSE streaming
- [Async Usage](guides/async-usage.md) - Using the async client
- [Error Handling](guides/error-handling.md) - Exception handling patterns
- [Frappe Integration](guides/frappe-integration.md) - Using with Frappe Framework

### API Reference

Complete API documentation:

- [FACLClient](api/client.md) - Synchronous client reference
- [AsyncFACLClient](api/async-client.md) - Asynchronous client reference
- [Types](api/types.md) - TypedDict definitions
- [Exceptions](api/exceptions.md) - Exception hierarchy
- [Utilities](api/utilities.md) - Auth and streaming utilities

### Examples

Working code examples:

- [examples/](examples/) - Complete example scripts

## Requirements

- Python 3.10+
- `requests` >= 2.28.0 (for sync client)
- `aiohttp` >= 3.8.0 (for async client, optional)

## License

GNU Affero General Public License v3.0

Copyright (C) 2025 Paul Clinton

## Support

- GitHub Issues: [Report a bug](https://github.com/anthropics/facl-sdk/issues)
- Documentation: [https://docs.facl.frappe.cloud](https://docs.facl.frappe.cloud)

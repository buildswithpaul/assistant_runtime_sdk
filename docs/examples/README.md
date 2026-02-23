# Assistant Runtime SDK Examples

This directory contains working code examples demonstrating how to use the Assistant Runtime SDK.

## Setup

Before running examples, set your environment variables:

```bash
export AR_TENANT_ID="your-tenant-id"
export AR_TENANT_SECRET="your-tenant-secret"
export AR_URL="https://ar.example.com"  # Optional
```

## Examples

### [basic_chat.py](basic_chat.py)

The simplest way to use the Assistant Runtime SDK - send a message and receive a streaming response.

```bash
python basic_chat.py
```

**Demonstrates:**
- Creating a client
- Listing available models
- Basic streaming chat
- Handling stream events

### [streaming_chat.py](streaming_chat.py)

Comprehensive handling of all SSE event types during streaming.

```bash
python streaming_chat.py
```

**Demonstrates:**
- Event-driven architecture
- Handling thinking events
- Tool execution events
- Error and rate limit handling
- Model fallback events

### [async_chat.py](async_chat.py)

Asynchronous chat streaming with concurrent operations.

```bash
pip install assistant_runtime_sdk[async]
python async_chat.py
```

**Demonstrates:**
- AsyncAssistantRuntimeClient usage
- Async context manager
- Concurrent API calls
- Parallel chat sessions
- Rate-limited operations with semaphores

### [frappe_integration.py](frappe_integration.py)

Integration patterns for Frappe Framework applications.

**Note:** This is reference code, not a standalone script.

**Demonstrates:**
- Creating a Frappe client wrapper
- Using Frappe settings for configuration
- Whitelisted API methods
- Socket.IO real-time streaming
- Background job integration
- JavaScript client-side code

### [error_handling.py](error_handling.py)

Comprehensive error handling patterns.

```bash
python error_handling.py
```

**Demonstrates:**
- Retry decorators with exponential backoff
- Safe API call wrappers
- Error categorization for user-friendly messages
- Partial response recovery
- Rate limit handling

## Running Examples

1. Install the SDK:
   ```bash
   pip install assistant_runtime_sdk[all]
   ```

2. Set environment variables (see Setup above)

3. Run any example:
   ```bash
   python examples/basic_chat.py
   ```

## Example Output

### basic_chat.py
```
Checking available models...
Found 5 available models
Auto mode available with 5 models

==================================================
Starting chat...
==================================================

User: Hello! What can you help me with today?
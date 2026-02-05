# Authentication Guide

FACL uses HMAC-SHA256 signatures to authenticate API requests. This guide explains how authentication works and how to use the SDK's authentication utilities.

## How FACL Authentication Works

Every request to FACL must include an `X-FACL-Signature` header containing:

```
{timestamp}:{signature}
```

Where:
- `timestamp` is the current Unix timestamp
- `signature` is an HMAC-SHA256 hash of the request parameters

### Signature Generation

The signature is computed as:

```
signature = HMAC-SHA256(
    key: tenant_secret,
    message: "{tenant_id}:{timestamp}:{params_json}"
)
```

Where `params_json` is the JSON-encoded request parameters, sorted by key.

## Using the SDK (Automatic)

The SDK handles authentication automatically. Just provide your credentials:

```python
from facl import FACLClient

client = FACLClient(
    tenant_id="your-tenant-id",
    tenant_secret="your-tenant-secret"
)

# All requests are automatically signed
models = client.list_available_models()
```

## Manual Signature Generation

For custom integrations or debugging, you can generate signatures manually:

### Basic Signature Generation

```python
from facl import generate_signature

# Generate signature for GET request (query string params)
params = {"tenant_id": "my-tenant", "message": "Hello"}
signature = generate_signature(
    tenant_id="my-tenant",
    tenant_secret="my-secret",
    params=params,
    for_query_string=True  # Converts values to strings
)

print(signature)  # "1704067200:a1b2c3d4e5f6..."
```

### For POST Requests with JSON Body

```python
from facl import generate_signature

# Generate signature for POST request (JSON body)
payload = {"tenant_id": "my-tenant", "data": {"count": 42}}
signature = generate_signature(
    tenant_id="my-tenant",
    tenant_secret="my-secret",
    params=payload,
    for_query_string=False  # Keep original types
)
```

### Getting Headers Dict

```python
from facl import get_signature_header

# Get headers ready to use with requests
headers = get_signature_header(
    tenant_id="my-tenant",
    tenant_secret="my-secret",
    params={"message": "Hello"}
)

# Use with requests library
import requests
response = requests.get(url, params=params, headers=headers)
```

## Signature Verification

If you're building a server that receives FACL callbacks:

```python
from facl import verify_signature

# Verify incoming request signature
is_valid = verify_signature(
    signature_header=request.headers["X-FACL-Signature"],
    tenant_id="expected-tenant",
    tenant_secret="shared-secret",
    params=request.json,
    for_query_string=False,  # True for query params
    max_age_seconds=300      # Reject signatures older than 5 minutes
)

if not is_valid:
    return {"error": "Invalid signature"}, 401
```

## Query String vs JSON Body

FACL signature generation differs based on request type:

### GET Requests (Query String)

When parameters are sent as query strings, all values become strings:

```python
# Original params
params = {"count": 42, "active": True}

# After query string conversion (what FACL server sees)
# count=42&active=True (all strings)

# Generate signature with for_query_string=True
signature = generate_signature(
    tenant_id, secret, params,
    for_query_string=True  # Converts 42 -> "42", True -> "True"
)
```

### POST Requests (JSON Body)

When parameters are sent as JSON, types are preserved:

```python
# Original params
payload = {"count": 42, "active": True}

# JSON body preserves types
# {"count": 42, "active": true}

# Generate signature with for_query_string=False
signature = generate_signature(
    tenant_id, secret, payload,
    for_query_string=False  # Keeps 42 as int, True as bool
)
```

## Security Best Practices

### 1. Protect Your Secret

Never expose your `tenant_secret`:

```python
# GOOD: Use environment variables
import os
client = FACLClient(
    tenant_id=os.environ["FACL_TENANT_ID"],
    tenant_secret=os.environ["FACL_TENANT_SECRET"]
)

# BAD: Hardcoded secrets
client = FACLClient(
    tenant_id="my-tenant",
    tenant_secret="my-secret-key"  # Don't do this!
)
```

### 2. Use Short Signature Lifetimes

When verifying signatures, use reasonable `max_age_seconds`:

```python
# Good: 5 minute window
is_valid = verify_signature(..., max_age_seconds=300)

# Risky: 1 hour window (replay attack risk)
is_valid = verify_signature(..., max_age_seconds=3600)
```

### 3. Sync Server Time

HMAC signatures include timestamps. Ensure your server time is synchronized:

```bash
# Linux: Check NTP sync
timedatectl status

# If not synced
sudo timedatectl set-ntp true
```

### 4. Rotate Secrets Periodically

Implement secret rotation:

```python
# Support multiple secrets during rotation
secrets = [os.environ["FACL_SECRET_NEW"], os.environ["FACL_SECRET_OLD"]]

for secret in secrets:
    if verify_signature(sig, tenant_id, secret, params):
        return True
return False
```

## Troubleshooting

### "Invalid Signature" Errors

1. **Check parameter ordering**: Params must be sorted by key
2. **Verify JSON encoding**: Use `json.dumps(params, sort_keys=True, separators=(", ", ": "))`
3. **Check timestamp**: Ensure server time is correct
4. **Verify secret**: Ensure you're using the correct tenant secret

### Debugging Signatures

```python
from facl import generate_signature
import json

params = {"tenant_id": "test", "message": "Hello"}

# Print what's being signed
params_json = json.dumps(params, sort_keys=True, separators=(", ", ": "))
print(f"Signing: test:{timestamp}:{params_json}")

signature = generate_signature("test", "secret", params)
print(f"Signature: {signature}")
```

### Clock Skew Issues

If you get "signature expired" errors:

```python
import time

# Check local vs expected time
local_time = int(time.time())
print(f"Local timestamp: {local_time}")

# The signature timestamp should be within max_age_seconds of this
```

## API Reference

### `generate_signature()`

```python
def generate_signature(
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
    timestamp: Optional[int] = None,
) -> str:
    """
    Generate HMAC-SHA256 signature for FACL API request.

    Args:
        tenant_id: Unique tenant identifier
        tenant_secret: HMAC secret for request signing
        params: Request parameters (will be sorted by key)
        for_query_string: If True, convert values to strings
        timestamp: Optional timestamp override (for testing)

    Returns:
        Signature in format "timestamp:signature"
    """
```

### `verify_signature()`

```python
def verify_signature(
    signature_header: str,
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
    max_age_seconds: int = 300,
) -> bool:
    """
    Verify HMAC-SHA256 signature from FACL request.

    Args:
        signature_header: The X-FACL-Signature header value
        tenant_id: Expected tenant identifier
        tenant_secret: HMAC secret
        params: Request parameters to verify
        for_query_string: If True, treat params as query string
        max_age_seconds: Maximum age of signature (default 5 minutes)

    Returns:
        True if signature is valid and not expired
    """
```

### `get_signature_header()`

```python
def get_signature_header(
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
) -> Dict[str, str]:
    """
    Generate headers dict with FACL signature.

    Returns:
        Dict with X-FACL-Signature header
    """
```

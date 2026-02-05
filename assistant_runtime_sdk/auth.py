# Assistant Runtime SDK - Authentication
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
HMAC-SHA256 authentication for Assistant Runtime API requests.

Assistant Runtime uses HMAC-SHA256 signatures to authenticate API requests.
The signature format is: {timestamp}:{signature}
Where signature = HMAC-SHA256(tenant_secret, "{tenant_id}:{timestamp}:{params_json}")
"""

import hmac
import hashlib
import json
import time
from typing import Dict, Any, Optional


def generate_signature(
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
    timestamp: Optional[int] = None,
) -> str:
    """
    Generate HMAC-SHA256 signature for Assistant Runtime API request.

    Args:
        tenant_id: Unique tenant identifier
        tenant_secret: HMAC secret for request signing
        params: Request parameters (will be sorted by key)
        for_query_string: If True, convert values to strings (for GET requests).
                         If False, keep original types (for POST JSON body).
        timestamp: Optional timestamp override (for testing). Uses current time if None.

    Returns:
        Signature header value in format "timestamp:signature"

    Example:
        >>> sig = generate_signature("tenant-123", "secret", {"message": "Hello"})
        >>> print(sig)  # "1704067200:a1b2c3d4..."
    """
    if timestamp is None:
        timestamp = int(time.time())
    timestamp_str = str(timestamp)

    if for_query_string:
        # For GET requests: convert all values to strings to match how
        # frappe.request.args returns all values as strings
        params_to_sign = {k: str(v) if not isinstance(v, str) else v for k, v in params.items()}
    else:
        # For POST requests with JSON body: keep original types
        # Assistant Runtime receives the parsed JSON with original types
        params_to_sign = params

    # JSON format must match Python's json.dumps with sort_keys and separators
    # Assistant Runtime uses: json.dumps(params, sort_keys=True, separators=(', ', ': '))
    params_json = json.dumps(params_to_sign, sort_keys=True, separators=(", ", ": "))

    # Build message: tenant_id:timestamp:params_json
    message = f"{tenant_id}:{timestamp_str}:{params_json}"

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        tenant_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{timestamp_str}:{signature}"


def verify_signature(
    signature_header: str,
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
    max_age_seconds: int = 300,
) -> bool:
    """
    Verify HMAC-SHA256 signature from Assistant Runtime request.

    Useful for servers receiving callbacks or webhooks from Assistant Runtime.

    Args:
        signature_header: The X-AR-Signature header value ("timestamp:signature")
        tenant_id: Unique tenant identifier
        tenant_secret: HMAC secret for request signing
        params: Request parameters to verify
        for_query_string: If True, treat params as query string (values as strings)
        max_age_seconds: Maximum age of signature in seconds (default 5 minutes)

    Returns:
        True if signature is valid and not expired, False otherwise

    Example:
        >>> is_valid = verify_signature(
        ...     "1704067200:a1b2c3d4...",
        ...     "tenant-123",
        ...     "secret",
        ...     {"callback": "data"}
        ... )
    """
    try:
        parts = signature_header.split(":", 1)
        if len(parts) != 2:
            return False

        timestamp_str, received_signature = parts
        timestamp = int(timestamp_str)

        # Check if signature is too old
        current_time = int(time.time())
        if abs(current_time - timestamp) > max_age_seconds:
            return False

        # Generate expected signature with same timestamp
        expected = generate_signature(
            tenant_id,
            tenant_secret,
            params,
            for_query_string=for_query_string,
            timestamp=timestamp,
        )

        # Compare signatures (timing-safe comparison)
        return hmac.compare_digest(expected, signature_header)

    except (ValueError, TypeError):
        return False


def get_signature_header(
    tenant_id: str,
    tenant_secret: str,
    params: Dict[str, Any],
    for_query_string: bool = False,
) -> Dict[str, str]:
    """
    Generate headers dict with Assistant Runtime signature for requests.

    Convenience function that returns a dict ready to merge with other headers.

    Args:
        tenant_id: Unique tenant identifier
        tenant_secret: HMAC secret
        params: Request parameters
        for_query_string: True for GET requests, False for POST JSON

    Returns:
        Dict with X-AR-Signature header

    Example:
        >>> headers = get_signature_header("tenant", "secret", {"msg": "hi"})
        >>> requests.get(url, params=params, headers={**headers, **other_headers})
    """
    signature = generate_signature(tenant_id, tenant_secret, params, for_query_string)
    return {"X-AR-Signature": signature}

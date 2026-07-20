# Assistant Runtime SDK - Sync/Async Parity Tests
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""
Meta-tests ensuring every public sync method has an async counterpart
with matching parameters. Catches drift automatically.
"""

import inspect

import pytest

from assistant_runtime_sdk import AssistantRuntimeClient
from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient


# Methods that only exist on sync client (module-level standalone functions,
# not class methods) or only on async client (lifecycle methods).
SYNC_ONLY = frozenset()
ASYNC_ONLY = frozenset({
    "__aenter__",
    "__aexit__",
    "_ensure_session",
    "_handle_error_response",
})

# Internal methods that don't need parity checks
INTERNAL_PREFIX = "_"


def _public_methods(cls):
    """Return set of public method names on a class (excluding inherited from base)."""
    return {
        name
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith(INTERNAL_PREFIX)
    }


def _all_methods(cls):
    """Return dict of name -> method for all non-dunder methods defined directly on cls."""
    result = {}
    for name in dir(cls):
        if name.startswith("__") and name.endswith("__"):
            continue
        obj = getattr(cls, name, None)
        if obj is None:
            continue
        # Only include methods defined directly on this class, not inherited
        if name in cls.__dict__ and callable(obj):
            result[name] = obj
    return result


class TestSyncAsyncParity:
    """Ensure sync and async clients have matching public APIs."""

    def test_all_sync_public_methods_exist_in_async(self):
        """Every public sync method must have an async counterpart."""
        sync_methods = _public_methods(AssistantRuntimeClient) - SYNC_ONLY
        async_methods = _public_methods(AsyncAssistantRuntimeClient) - ASYNC_ONLY

        missing = sync_methods - async_methods
        assert not missing, (
            f"Sync methods missing from async client: {sorted(missing)}"
        )

    def test_all_async_public_methods_exist_in_sync(self):
        """Every public async method must have a sync counterpart."""
        sync_methods = _public_methods(AssistantRuntimeClient) - SYNC_ONLY
        async_methods = _public_methods(AsyncAssistantRuntimeClient) - ASYNC_ONLY

        extra = async_methods - sync_methods
        assert not extra, (
            f"Async methods without sync counterpart: {sorted(extra)}"
        )

    def test_method_signatures_match(self):
        """Public method parameters must match between sync and async."""
        sync_methods = _all_methods(AssistantRuntimeClient)
        async_methods = _all_methods(AsyncAssistantRuntimeClient)

        mismatches = []

        for name, sync_method in sync_methods.items():
            if name.startswith(INTERNAL_PREFIX):
                continue
            if name in SYNC_ONLY:
                continue

            async_method = async_methods.get(name)
            if async_method is None:
                continue  # Caught by existence test above

            sync_sig = inspect.signature(sync_method)
            async_sig = inspect.signature(async_method)

            # Compare parameter names and defaults (ignore 'self')
            sync_params = [
                (p.name, p.default, p.kind)
                for p in sync_sig.parameters.values()
                if p.name != "self"
            ]
            async_params = [
                (p.name, p.default, p.kind)
                for p in async_sig.parameters.values()
                if p.name != "self"
            ]

            if sync_params != async_params:
                mismatches.append(
                    f"  {name}:\n"
                    f"    sync:  {[p[0] for p in sync_params]}\n"
                    f"    async: {[p[0] for p in async_params]}"
                )

        assert not mismatches, (
            "Parameter mismatches between sync and async:\n"
            + "\n".join(mismatches)
        )

    def test_constructor_signatures_match(self):
        """Sync and async __init__ must expose the same parameters.

        The sync client inherits BaseAssistantRuntimeClient.__init__; the async
        client overrides it. A param added to the base/sync ctor but forgotten in
        the async override silently makes that override unreachable on async
        (regression: voice_api_base was dropped from the async ctor, so async
        transcribe_audio could not override the voice base). The general
        signature parity test skips dunders, so __init__ needs its own check.
        """
        sync_params = [
            (p.name, p.default, p.kind)
            for p in inspect.signature(AssistantRuntimeClient.__init__).parameters.values()
            if p.name != "self"
        ]
        async_params = [
            (p.name, p.default, p.kind)
            for p in inspect.signature(AsyncAssistantRuntimeClient.__init__).parameters.values()
            if p.name not in ("self", "session")  # async-only: optional aiohttp session reuse
        ]

        assert sync_params == async_params, (
            "Constructor parameter mismatch between sync and async:\n"
            f"  sync:  {[p[0] for p in sync_params]}\n"
            f"  async: {[p[0] for p in async_params]}"
        )

    def test_upload_ticket_attachment_parity(self):
        """upload_ticket_attachment must exist on both clients with matching params."""
        assert hasattr(AssistantRuntimeClient, "upload_ticket_attachment")
        assert hasattr(AsyncAssistantRuntimeClient, "upload_ticket_attachment")

        sync_sig = inspect.signature(AssistantRuntimeClient.upload_ticket_attachment)
        async_sig = inspect.signature(AsyncAssistantRuntimeClient.upload_ticket_attachment)
        sync_params = [(p.name, p.default, p.kind) for p in sync_sig.parameters.values() if p.name != "self"]
        async_params = [(p.name, p.default, p.kind) for p in async_sig.parameters.values() if p.name != "self"]
        assert sync_params == async_params, (
            "upload_ticket_attachment signature mismatch:\n"
            f"  sync:  {[p[0] for p in sync_params]}\n"
            f"  async: {[p[0] for p in async_params]}"
        )

    def test_ticket_attachment_ids_param_present(self):
        """create_ticket and reply_to_ticket must both expose attachment_ids."""
        for cls in (AssistantRuntimeClient, AsyncAssistantRuntimeClient):
            for method_name in ("create_ticket", "reply_to_ticket"):
                params = inspect.signature(getattr(cls, method_name)).parameters
                assert "attachment_ids" in params, (
                    f"{cls.__name__}.{method_name} is missing attachment_ids"
                )

    def test_method_count_reasonable(self):
        """Sanity check: both clients should have a reasonable number of public methods."""
        sync_count = len(_public_methods(AssistantRuntimeClient))
        async_count = len(_public_methods(AsyncAssistantRuntimeClient))

        # Should have at least 50 public methods (we have ~70)
        assert sync_count >= 50, f"Sync client only has {sync_count} public methods"
        assert async_count >= 50, f"Async client only has {async_count} public methods"

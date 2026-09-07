"""Sync and async must expose the same routing-preference surface.

They share base.py's _prepare_* methods precisely so the two cannot drift;
this asserts neither client forgot to wire one up.
"""

import inspect
import unittest

from assistant_runtime_sdk.async_client import AsyncAssistantRuntimeClient
from assistant_runtime_sdk.client import AssistantRuntimeClient

METHODS = (
    "list_routing_preferences",
    "create_routing_preference",
    "set_routing_preference_status",
    "delete_routing_preference",
    "forecast_routing_preference",
)


class TestRoutingPreferenceMethods(unittest.TestCase):
    def test_both_clients_expose_every_method(self):
        for name in METHODS:
            self.assertTrue(hasattr(AssistantRuntimeClient, name), name)
            self.assertTrue(hasattr(AsyncAssistantRuntimeClient, name), name)

    def test_the_async_versions_are_actually_async(self):
        for name in METHODS:
            self.assertTrue(
                inspect.iscoroutinefunction(
                    getattr(AsyncAssistantRuntimeClient, name)), name)

    def test_the_signatures_match(self):
        for name in METHODS:
            sync = inspect.signature(getattr(AssistantRuntimeClient, name))
            asyn = inspect.signature(getattr(AsyncAssistantRuntimeClient, name))
            self.assertEqual(list(sync.parameters), list(asyn.parameters), name)

    def test_every_call_is_a_post(self):
        # match_value is text the user wrote; a GET would put it in the query
        # string and from there into access logs.
        for name in METHODS:
            src = inspect.getsource(getattr(AssistantRuntimeClient, name))
            self.assertIn("_request_post_json", src, name)

    def test_the_endpoints_point_at_the_ar_module(self):
        from assistant_runtime_sdk.base import BaseAssistantRuntimeClient

        for name in METHODS:
            prep = getattr(BaseAssistantRuntimeClient, f"_prepare_{name}")
            src = inspect.getsource(prep)
            self.assertIn(f'"routing_preferences.{name}"', src, name)


if __name__ == "__main__":
    unittest.main()

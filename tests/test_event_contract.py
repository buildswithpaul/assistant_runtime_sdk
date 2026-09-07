"""The SDK's event enum against what AR actually puts on the wire.

The SDK cannot import AR (different licence, different package), so the list
is pinned here with its provenance. An event missing from the enum is not a
cosmetic gap: from_string() returns UNKNOWN, and a consumer dispatching on
the enum drops that event in silence.
"""

import unittest

from assistant_runtime_sdk.streaming import SSEEventType
from assistant_runtime_sdk.types import (
    ModelFallbackData,
    ModelSelectedData,
    RoutingReceiptData,
    StreamCompleteData,
)

# Every format_sse_event("...") in AR/api/streaming.py, plus the two names
# terminal_event_name() can return (AR/utils/stream_cancel.py:82).
AR_WIRE_EVENTS = {
    "approval_required",
    "context_summarized",
    "model_selected",
    "plan_complete",
    "rate_limited",
    "routing_notice",
    "sources",
    "stream_cancelled",
    "stream_chunk",
    "stream_complete",
    "stream_error",
    "stream_start",
    "task_updated",
    "thinking",
    "thinking_complete",
    "tool_call_result",
    "tool_call_start",
    "tool_cancelled",
    "workflow_created",
}


class TestEventContract(unittest.TestCase):
    def test_every_ar_event_has_an_enum_member(self):
        missing = sorted(e for e in AR_WIRE_EVENTS
                         if SSEEventType.from_string(e) is SSEEventType.UNKNOWN)
        self.assertEqual(missing, [], f"consumers silently drop: {missing}")

    def test_the_auto_mode_event_is_the_one_ar_emits(self):
        self.assertEqual(SSEEventType.MODEL_SELECTED.value, "model_selected")

    def test_the_misnamed_member_survives_for_compatibility(self):
        # Published AGPL API: it may be deprecated, never deleted.
        self.assertEqual(SSEEventType.MODEL_FALLBACK.value, "model_fallback")


class TestReceiptTypes(unittest.TestCase):
    def test_stream_complete_carries_the_receipt_and_the_cost(self):
        for key in ("routing", "credits_used", "model_breakdown"):
            self.assertIn(key, StreamCompleteData.__annotations__)

    def test_the_receipt_type_names_the_sections_the_wire_sends(self):
        for key in ("v", "mode", "selected_model", "selected_tier", "bound_by",
                    "floor", "ceiling", "classification", "thinking", "credits",
                    "pick_reason", "notices", "band", "band_disclosed"):
            self.assertIn(key, RoutingReceiptData.__annotations__)

    def test_the_receipt_type_carries_no_price_key(self):
        # Sec 3.6 — the builder cannot emit one, and the type must not invite one.
        for key in RoutingReceiptData.__annotations__:
            for banned in ("price", "rate", "usd", "reviewed", "cost_per"):
                self.assertNotIn(banned, key.lower())

    def test_model_selected_carries_the_receipt(self):
        self.assertIn("routing", ModelSelectedData.__annotations__)

    def test_the_old_name_still_resolves(self):
        self.assertIs(ModelFallbackData, ModelSelectedData)


if __name__ == "__main__":
    unittest.main()

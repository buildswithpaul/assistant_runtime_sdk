import unittest
from unittest.mock import MagicMock, patch

from assistant_runtime_sdk import AssistantRuntimeClient


class TestGenerateCuratedSuggestions(unittest.TestCase):
    def _client(self):
        return AssistantRuntimeClient(
            ar_url="https://ar.example.com",
            tenant_id="T1",
            tenant_secret="s3cret",
            site_url="https://tenant.example.com",
        )

    @patch("assistant_runtime_sdk.client.requests.post")
    def test_posts_signed_payload_and_returns_message(self, mock_post):
        resp = MagicMock()
        resp.json.return_value = {"message": {"suggestions": [{"text": "Hi"}]}}
        resp.raise_for_status.return_value = None
        mock_post.return_value = resp

        out = self._client().generate_curated_suggestions(
            user_id="u@e.com", signals={"roles": ["Accounts Manager"]}
        )

        self.assertEqual(out["suggestions"][0]["text"], "Hi")
        url = mock_post.call_args.args[0] if mock_post.call_args.args else mock_post.call_args.kwargs["url"]
        self.assertIn("assistant_runtime.api.suggestions.generate_curated", url)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["tenant_id"], "T1")
        self.assertEqual(payload["user_id"], "u@e.com")
        self.assertEqual(payload["signals"], {"roles": ["Accounts Manager"]})

# Assistant Runtime SDK - version consistency
# Copyright (C) 2025 Paul Clinton
# AGPL-3.0 License

"""The version number is a claim about content.

pyproject.toml and __init__.py:__version__ must agree, and both must move in
the same change that adds a public method. A tree whose version equals the
last published tag while its code differs is the coupled-pair bug: FAC pins
that number exactly, pip resolves the published artifact, and the missing
method surfaces as AttributeError in production.
"""

import tomllib
import unittest
from pathlib import Path

import assistant_runtime_sdk

EXPECTED = "1.9.0"
ROOT = Path(__file__).resolve().parent.parent


class TestVersionConsistency(unittest.TestCase):
    def test_dunder_version_matches_expected(self):
        self.assertEqual(assistant_runtime_sdk.__version__, EXPECTED)

    def test_pyproject_matches_dunder_version(self):
        with open(ROOT / "pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
        self.assertEqual(data["project"]["version"], assistant_runtime_sdk.__version__)

    def test_the_connect_methods_this_version_claims_are_present(self):
        # The reason 1.9.0 exists. If this fails, the version number is lying.
        from assistant_runtime_sdk.client import AssistantRuntimeClient

        for name in (
            "begin_mcp_connect",
            "get_mcp_connect_session",
            "commit_mcp_connect",
            "abandon_mcp_connect",
            "begin_mcp_reauth",
        ):
            self.assertTrue(hasattr(AssistantRuntimeClient, name), name)


if __name__ == "__main__":
    unittest.main()

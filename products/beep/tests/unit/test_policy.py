from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import policy


PRODUCT_ROOT = Path(__file__).resolve().parents[2]


class PolicyTests(unittest.TestCase):
    def test_shipped_policy_is_valid(self) -> None:
        self.assertTrue(
            policy.validate_policy(PRODUCT_ROOT / "payload" / "etc" / "policy.yaml")
        )

    def test_malformed_policy_falls_back_to_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.yaml"
            path.write_text(
                "settings:\n"
                "  default_class: read_only\n"
                "rules:\n"
                "  - pattern: '['\n"
                "    class: read_only\n",
                encoding="utf-8",
            )
            self.assertFalse(policy.validate_policy(path))
            loaded = policy.load_policy(path)
            self.assertEqual(loaded.classify("unknown-command"), "destructive")

    def test_unknown_matching_class_is_destructive(self) -> None:
        self.assertEqual(policy._max_class(["not-a-policy-class"]), "destructive")


if __name__ == "__main__":
    unittest.main()

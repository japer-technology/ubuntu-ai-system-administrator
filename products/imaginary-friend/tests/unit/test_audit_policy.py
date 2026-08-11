from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from friend.audit import AuditLogger, redact
from friend.policy import decide


class AuditPolicyTests(unittest.TestCase):
    def test_audit_redacts_credentials_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.log"
            password = "do-not-record-this-password"
            session = "A" * 48
            password_key = "pass" + "word"
            AuditLogger(path).event(
                "test",
                **{
                    password_key: password,
                    "session_token": session,
                    "note": password_key + "=" + password,
                },
            )
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn(password, raw)
            self.assertNotIn(session, raw)
            value = json.loads(raw)
            self.assertEqual(value["password"], "***REDACTED***")
            self.assertEqual(value["session_token"], "***REDACTED***")

    def test_recursive_redaction(self) -> None:
        value = redact({"nested": [{"signing_key": "secret-value"}]})
        self.assertEqual(value["nested"][0]["signing_key"], "***REDACTED***")

    def test_policy_has_no_host_or_unknown_capability(self) -> None:
        self.assertTrue(decide("conversation", authenticated_owner=True).allowed)
        self.assertTrue(decide("workspace.read", authenticated_owner=True).allowed)
        self.assertFalse(decide("shell.run", authenticated_owner=True).allowed)
        self.assertFalse(decide("network.fetch", authenticated_owner=True).allowed)
        self.assertFalse(decide("totally.unknown", authenticated_owner=True).allowed)
        self.assertFalse(decide("conversation", authenticated_owner=False).allowed)

    def test_destructive_workspace_change_requires_path_confirmation(self) -> None:
        denied = decide(
            "workspace.change",
            authenticated_owner=True,
            destructive=True,
            confirmation_matches=False,
        )
        self.assertFalse(denied.allowed)
        self.assertTrue(denied.requires_confirmation)
        self.assertTrue(
            decide(
                "workspace.change",
                authenticated_owner=True,
                destructive=True,
                confirmation_matches=True,
            ).allowed
        )


if __name__ == "__main__":
    unittest.main()

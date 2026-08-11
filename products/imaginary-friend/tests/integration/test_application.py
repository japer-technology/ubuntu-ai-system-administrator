from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))

from openai_fixture import Fixture  # noqa: E402

from friend.application import Config, FriendApplication
from friend.auth import hash_password
from friend.database import Database
from friend.errors import AuthenticationError, AuthorizationError, ValidationError


class ApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.workspace.chmod(0o2770)
        self.database_path = self.root / "friend.db"
        self.audit_path = self.root / "audit.log"
        self.key_path = self.root / "session.key"
        self.key_path.write_bytes(b"k" * 32)
        self.fixture = Fixture()
        self.fixture.__enter__()
        database = Database(self.database_path)
        database.initialize(
            password_hash=hash_password("initial owner password"),
            model_base_url=self.fixture.base_url,
            model="fixture-friend",
            history_retention_days=30,
            audit_retention_days=90,
        )
        details = self.workspace.stat()
        self.workspace_id = database.register_workspace(
            canonical_root=str(self.workspace),
            root_device=details.st_dev,
            root_inode=details.st_ino,
        )
        with mock.patch("friend.application.grp.getgrnam") as share_group:
            share_group.return_value.gr_gid = self.workspace.stat().st_gid
            self.application = FriendApplication(
                Config(
                    owner_user="owner",
                    port=6767,
                    database_path=self.database_path,
                    audit_path=self.audit_path,
                    signing_key_path=self.key_path,
                    allowed_workspaces=(self.workspace,),
                )
            )

    def tearDown(self) -> None:
        self.fixture.__exit__(None, None, None)
        self.temporary.cleanup()

    def test_login_csrf_rotation_and_revocation(self) -> None:
        with self.assertRaises(AuthenticationError):
            self.application.login("wrong")
        login = self.application.login("initial owner password")
        token = login["session_token"]
        self.application.require_session(token)
        with self.assertRaises(AuthorizationError):
            self.application.require_csrf(token, "wrong")
        self.application.require_csrf(token, login["csrf_token"])
        refreshed = self.application.refresh_csrf(token)
        self.application.require_csrf(token, refreshed)
        self.application.rotate_password(
            "initial owner password", "replacement owner password"
        )
        with self.assertRaises(AuthenticationError):
            self.application.require_session(token)
        self.application.login("replacement owner password")

    def test_conversation_selected_file_and_export(self) -> None:
        self.application.write_file(
            self.workspace_id,
            "context.txt",
            "Selected private context.",
            expected_sha256=None,
            confirmation=None,
        )
        response = self.application.chat(
            "A private owner question.",
            selected_files=[
                {"workspace_id": self.workspace_id, "path": "context.txt"}
            ],
        )
        self.assertEqual(response["message"], "A private fixture reply.")
        self.assertTrue(response["history_persisted"])
        exported = self.application.export()
        self.assertEqual(len(exported["conversations"]), 1)
        serialized = json.dumps(exported)
        self.assertIn("A private owner question.", serialized)
        for forbidden in ("password_hash", "session_token", "workspace file contents"):
            self.assertNotIn(forbidden, serialized)
        audit = self.audit_path.read_text(encoding="utf-8")
        self.assertNotIn("A private owner question.", audit)
        self.assertNotIn("Selected private context.", audit)

    def test_workspace_mutations_require_exact_confirmation(self) -> None:
        created = self.application.write_file(
            self.workspace_id,
            "note.txt",
            "one",
            expected_sha256=None,
            confirmation=None,
        )
        with self.assertRaises(AuthorizationError):
            self.application.write_file(
                self.workspace_id,
                "note.txt",
                "two",
                expected_sha256=created["sha256"],
                confirmation="different.txt",
            )
        updated = self.application.write_file(
            self.workspace_id,
            "note.txt",
            "two",
            expected_sha256=created["sha256"],
            confirmation="note.txt",
        )
        self.assertEqual(updated["bytes"], 3)
        with self.assertRaises(AuthorizationError):
            self.application.delete_path(
                self.workspace_id, "note.txt", confirmation=None
            )
        self.application.delete_path(
            self.workspace_id, "note.txt", confirmation="note.txt"
        )

    def test_invalid_workspace_path_is_denied_and_audited(self) -> None:
        with self.assertRaises(ValidationError):
            self.application.read_file(self.workspace_id, "../outside")

        event = json.loads(
            self.audit_path.read_text(encoding="utf-8").splitlines()[-1]
        )
        self.assertEqual(event["event_type"], "policy_decision")
        self.assertEqual(event["decision"], "denied")
        self.assertEqual(event["relative_path"], "../outside")

        self.application.write_file(
            self.workspace_id,
            "move-me.txt",
            "content",
            expected_sha256=None,
            confirmation=None,
        )
        with self.assertRaises(ValidationError):
            self.application.move_path(
                self.workspace_id,
                "move-me.txt",
                "../outside",
                confirmation="move-me.txt",
            )
        event = json.loads(
            self.audit_path.read_text(encoding="utf-8").splitlines()[-1]
        )
        self.assertEqual(event["decision"], "denied")
        self.assertEqual(event["relative_path"], "../outside")

    def test_settings_reject_non_loopback_provider(self) -> None:
        with self.assertRaises(ValidationError):
            self.application.update_settings(
                {"model_base_url": "http://example.com/v1"}
            )

    def test_workspace_reenable_requires_complete_sharing_boundary(self) -> None:
        self.application.set_workspace_enabled(self.workspace_id, False)
        self.workspace.chmod(0o0770)
        with self.assertRaises(ValidationError):
            self.application.set_workspace_enabled(self.workspace_id, True)

        self.workspace.chmod(0o2770)
        self.application.set_workspace_enabled(self.workspace_id, True)

    def test_password_rotation_rejects_unsupported_password_text(self) -> None:
        for password in ("x" * 1025, "long enough\nbut multiline"):
            with self.assertRaises(ValidationError):
                self.application.rotate_password(
                    "initial owner password", password
                )
        self.application.login("initial owner password")

    def test_suspension_revokes_sessions_and_capabilities(self) -> None:
        login = self.application.login("initial owner password")
        self.application.suspend()
        with self.assertRaises(AuthenticationError):
            self.application.require_session(login["session_token"])
        with self.assertRaises(AuthorizationError):
            self.application.chat("hello")


if __name__ == "__main__":
    unittest.main()

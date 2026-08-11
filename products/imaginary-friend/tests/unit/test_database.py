from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from friend.auth import hash_password
from friend.database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = Database(self.root / "friend.db")
        self.database.initialize(
            password_hash=hash_password("initial owner password"),
            model_base_url="http://127.0.0.1:8080/v1",
            model="fixture-friend",
            history_retention_days=30,
            audit_retention_days=90,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_required_schema_and_export_exclusions(self) -> None:
        journal = self.root / "friend.db-journal"
        self.assertTrue(journal.is_file())
        self.assertEqual(oct(journal.stat().st_mode & 0o777), "0o600")
        required = {
            "conversations",
            "messages",
            "workspaces",
            "workspace_events",
            "sessions",
            "settings",
        }
        self.assertTrue(required.issubset(set(self.database.table_names())))
        conversation = self.database.create_conversation("Private title")
        self.database.add_message(conversation, "user", "Private message")
        exported = self.database.export()
        self.assertEqual(exported["export_version"], 1)
        text = self.database.export_json()
        self.assertIn("Private message", text)
        for forbidden in ("password_hash", "token_digest", "csrf_digest"):
            self.assertNotIn(forbidden, text)

    def test_password_rotation_revokes_sessions(self) -> None:
        self.database.create_session("token-digest", "csrf-digest", now=100)
        self.assertIsNotNone(self.database.active_session("token-digest", now=101))
        self.database.rotate_password(hash_password("replacement owner password"))
        self.assertIsNone(self.database.active_session("token-digest", now=101))

    def test_retention_prunes_expired_conversations_and_events(self) -> None:
        conversation = self.database.create_conversation("Expired")
        self.database.add_message(conversation, "user", "remove me")
        workspace = self.root / "workspace"
        workspace.mkdir()
        details = workspace.stat()
        workspace_id = self.database.register_workspace(
            canonical_root=str(workspace),
            root_device=details.st_dev,
            root_inode=details.st_ino,
        )
        self.database.workspace_event(workspace_id, "note.txt", "write", "ok")
        self.database.prune(now=10**12)
        self.assertEqual(self.database.list_conversations(), [])
        self.assertEqual(self.database.workspace_events(), [])

    def test_retention_change_recomputes_existing_conversation_expiry(self) -> None:
        with mock.patch("friend.database.time.time", return_value=100.0):
            conversation = self.database.create_conversation("Rolling retention")
            self.database.add_message(conversation, "user", "private")
            self.database.update_settings({"history_retention_days": 1})
            stored = self.database.conversation(conversation)
        self.assertEqual(stored["expires_at"], 86_500.0)
        self.database.prune(now=86_501.0)
        self.assertEqual(self.database.list_conversations(), [])

    def test_backup_drops_session_material(self) -> None:
        self.database.create_session("token-digest", "csrf-digest")
        backup_path = self.root / "backup.db"
        self.database.backup_to(backup_path)
        backup = Database(backup_path)
        self.assertIsNone(backup.active_session("token-digest"))

    def test_export_and_unbounded_listing_include_every_conversation(self) -> None:
        expected: set[str] = set()
        for index in range(105):
            conversation = self.database.create_conversation(f"Conversation {index}")
            self.database.add_message(conversation, "user", f"Message {index}")
            expected.add(conversation)

        listed = self.database.list_conversations(limit=None)
        exported = self.database.export()["conversations"]

        self.assertEqual({item["id"] for item in listed}, expected)
        self.assertEqual({item["id"] for item in exported}, expected)
        self.assertTrue(all(len(item["messages"]) == 1 for item in exported))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from friend.audit_retention import prune_rotated_audit
from friend.auth import hash_password
from friend.database import Database


class AuditRetentionTests(unittest.TestCase):
    def test_only_expired_rotation_files_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database_path = root / "friend.db"
            Database(database_path).initialize(
                password_hash=hash_password("initial owner password"),
                model_base_url="http://127.0.0.1:8080/v1",
                model="fixture-friend",
                history_retention_days=30,
                audit_retention_days=90,
            )
            log_root = root / "logs"
            log_root.mkdir()
            old = log_root / "audit.log.91.gz"
            recent = log_root / "audit.log.1"
            unrelated = log_root / "management-receipt.json"
            for path in (old, recent, unrelated):
                path.write_text("fixture", encoding="utf-8")
                os.chmod(path, 0o640)
            now = 1_900_000_000.0
            os.utime(old, (now - 91 * 86_400, now - 91 * 86_400))
            os.utime(recent, (now - 86_400, now - 86_400))
            os.utime(unrelated, (now - 365 * 86_400, now - 365 * 86_400))
            removed = prune_rotated_audit(database_path, log_root, now=now)
            self.assertEqual(removed, [old])
            self.assertFalse(old.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(unrelated.exists())

    def test_unsafe_rotation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database_path = root / "friend.db"
            Database(database_path).initialize(
                password_hash=hash_password("initial owner password"),
                model_base_url="http://127.0.0.1:8080/v1",
                model="fixture-friend",
                history_retention_days=30,
                audit_retention_days=90,
            )
            log_root = root / "logs"
            log_root.mkdir()
            target = root / "outside"
            target.write_text("do not remove", encoding="utf-8")
            (log_root / "audit.log.100").symlink_to(target)
            with self.assertRaises(ValueError):
                prune_rotated_audit(database_path, log_root, now=1_900_000_000.0)
            self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()

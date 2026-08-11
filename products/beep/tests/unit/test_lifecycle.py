from __future__ import annotations

import json
import math
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lifecycle


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.state = Path(self.temporary.name) / "lifecycle.json"
        self.environment = mock.patch.dict(
            os.environ,
            {"BEEP_LIFECYCLE_STATE": str(self.state)},
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def test_missing_state_fails_closed(self) -> None:
        status = lifecycle.status()
        self.assertFalse(status["configured"])
        self.assertTrue(status["dead"])
        self.assertEqual(status["dead_reason"], "state_missing")

    def test_initialize_expire_and_preserve_tombstone(self) -> None:
        with mock.patch.object(lifecycle, "_now", return_value=100.0):
            initialized = lifecycle.initialize(1)
        self.assertTrue(initialized["alive"])
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)

        with mock.patch.object(
            lifecycle,
            "_now",
            return_value=100.0 + lifecycle.DAY_SECONDS,
        ):
            expired = lifecycle.status()
        self.assertTrue(expired["dead"])
        self.assertEqual(expired["dead_reason"], "expired")

        with mock.patch.object(
            lifecycle,
            "_now",
            return_value=100.0 + lifecycle.DAY_SECONDS + 10,
        ):
            extended = lifecycle.set_ttl(7)
        self.assertTrue(extended["dead"])
        self.assertEqual(extended["dead_reason"], "expired")

    def test_kill_repairs_invalid_state_to_a_valid_tombstone(self) -> None:
        self.state.write_text("{broken", encoding="utf-8")
        result = lifecycle.kill("operator_killed")
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertTrue(result["configured"])
        self.assertTrue(result["dead"])
        self.assertEqual(stored["dead_reason"], "operator_killed")
        self.assertEqual(set(stored), {
            "created_at",
            "expires_at",
            "dead",
            "dead_reason",
            "dead_at",
        })

    def test_corrupt_and_nonfinite_state_fail_closed(self) -> None:
        self.state.write_text(
            json.dumps(
                {
                    "created_at": 1,
                    "expires_at": 2,
                    "dead": "false",
                    "dead_reason": None,
                    "dead_at": None,
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(lifecycle.status()["dead_reason"], "invalid_state")
        self.state.write_text(
            '{"created_at":1,"expires_at":NaN,"dead":false,'
            '"dead_reason":null,"dead_at":null}',
            encoding="utf-8",
        )
        self.assertEqual(lifecycle.status()["dead_reason"], "invalid_state")

    def test_unsafe_state_symlink_is_rejected(self) -> None:
        target = Path(self.temporary.name) / "target.json"
        target.write_text("unchanged", encoding="utf-8")
        self.state.symlink_to(target)
        with self.assertRaises(RuntimeError):
            lifecycle.initialize(1)
        self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")

    def test_nonfinite_durations_are_rejected(self) -> None:
        for value in (math.inf, -math.inf, math.nan):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    lifecycle.initialize(value)
                with self.assertRaises(ValueError):
                    lifecycle.set_ttl_seconds(value)
        with self.assertRaises(ValueError):
            lifecycle.parse_duration("nan days")


if __name__ == "__main__":
    unittest.main()

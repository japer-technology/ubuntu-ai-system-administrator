from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[2]
MANAGE = PRODUCT_ROOT / "scripts" / "manage.sh"
INSTALLER = PRODUCT_ROOT / "scripts" / "install.sh"


class ManagementTests(unittest.TestCase):
    def run_manage(
        self, *arguments: str, extra_environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment.update(extra_environment or {})
        return subprocess.run(
            [str(MANAGE), *arguments],
            cwd=PRODUCT_ROOT,
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_describe_is_valid_and_non_mutating(self) -> None:
        completed = self.run_manage("describe", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(value["product_id"], "imaginary-friend")
        self.assertEqual(value["phase"], "read")
        self.assertFalse(value["changed"])

    def test_installer_entrypoint_defaults_to_install(self) -> None:
        environment = dict(os.environ)
        environment["FRIEND_NONINTERACTIVE"] = "1"
        completed = subprocess.run(
            [str(INSTALLER), "--dry-run", "--json"],
            cwd=PRODUCT_ROOT,
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 64)
        value = json.loads(completed.stdout)
        self.assertEqual(value["operation"], "install")
        self.assertEqual(value["phase"], "plan")

    def test_unattended_missing_input_exits_64_with_json(self) -> None:
        completed = self.run_manage(
            "install",
            "--dry-run",
            "--json",
            extra_environment={"FRIEND_NONINTERACTIVE": "1"},
        )
        self.assertEqual(completed.returncode, 64)
        value = json.loads(completed.stdout)
        self.assertEqual(value["errors"][0]["code"], "MISSING_INPUT")
        self.assertEqual(value["phase"], "plan")

    def test_unknown_friend_environment_fails_closed(self) -> None:
        completed = self.run_manage(
            "describe",
            "--json",
            extra_environment={"FRIEND_RAW_PASSWORD": "not-a-secret"},
        )
        self.assertEqual(completed.returncode, 65)
        value = json.loads(completed.stdout)
        self.assertEqual(value["errors"][0]["code"], "UNKNOWN_INPUT")

    def test_dry_run_does_not_create_lifecycle_lock(self) -> None:
        lock = Path("/run/lock/imaginary-friend.lock")
        existed = lock.exists()
        self.run_manage(
            "install",
            "--dry-run",
            "--json",
            extra_environment={"FRIEND_NONINTERACTIVE": "1"},
        )
        self.assertEqual(lock.exists(), existed)


if __name__ == "__main__":
    unittest.main()

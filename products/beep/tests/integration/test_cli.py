from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[2]
MANAGER = PRODUCT_ROOT / "scripts" / "manage.sh"
INSTALLER = PRODUCT_ROOT / "scripts" / "install.sh"


def clean_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEEP_")
    }


class ManagementCLITests(unittest.TestCase):
    def run_manager(
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        completed = subprocess.run(
            [str(MANAGER), *arguments, "--json"],
            cwd=PRODUCT_ROOT,
            env=environment or clean_environment(),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return completed, json.loads(completed.stdout)

    def test_describe_uses_family_envelope(self) -> None:
        completed, response = self.run_manager("describe")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(response["product_id"], "beep")
        self.assertEqual(response["operation"], "describe")
        descriptor = response["details"]["beep"]["descriptor"]
        self.assertIn("kill", descriptor["operations"])

    def test_unattended_blocked_plan_returns_usage_status(self) -> None:
        environment = clean_environment()
        environment["BEEP_NONINTERACTIVE"] = "1"
        completed, response = self.run_manager(
            "install",
            "--dry-run",
            environment=environment,
        )
        self.assertEqual(completed.returncode, 64)
        self.assertEqual(response["status"], "blocked")
        self.assertIn(
            "chat_password_file",
            {item["name"] for item in response["required_inputs"]},
        )

    def test_installer_entrypoint_defaults_to_install(self) -> None:
        completed = subprocess.run(
            [
                str(INSTALLER),
                "--dry-run",
                "--json",
                "--non-interactive",
            ],
            cwd=PRODUCT_ROOT,
            env=clean_environment(),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 64, completed.stderr)
        response = json.loads(completed.stdout)
        self.assertEqual(response["operation"], "install")
        self.assertEqual(response["phase"], "plan")
        self.assertEqual(response["status"], "blocked")

    def test_kill_has_a_non_mutating_plan_surface(self) -> None:
        completed, response = self.run_manager("kill", "--dry-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(response["phase"], "plan")
        self.assertTrue(response["requires_confirmation"])
        self.assertTrue(any(step["id"] == "kill.execute" for step in response["steps"]))

    def test_raw_secret_environment_is_rejected_specifically(self) -> None:
        environment = clean_environment()
        environment["BEEP_API_KEY"] = "forbidden-inline-value"
        completed, response = self.run_manager(
            "describe",
            environment=environment,
        )
        self.assertEqual(completed.returncode, 65)
        self.assertEqual(response["errors"][0]["code"], "RAW_SECRET_REJECTED")


if __name__ == "__main__":
    unittest.main()

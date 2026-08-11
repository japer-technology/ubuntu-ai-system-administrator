from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[2]
MANAGE = PRODUCT_ROOT / "scripts/manage.sh"
REQUIRED_RESPONSE_FIELDS = {
    "schema_version",
    "product_id",
    "product_version",
    "instance_id",
    "operation",
    "phase",
    "correlation_id",
    "status",
    "changed",
    "plan_digest",
    "requires_confirmation",
    "required_inputs",
    "steps",
    "checks",
    "receipt",
    "errors",
    "recovery",
}


class ManagementIntegrationTests(unittest.TestCase):
    def run_manage(
        self, *arguments: str, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(environment or {})
        return subprocess.run(
            [str(MANAGE), *arguments],
            cwd=PRODUCT_ROOT,
            env=env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def response(self, completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
        value = json.loads(completed.stdout)
        self.assertTrue(REQUIRED_RESPONSE_FIELDS.issubset(value))
        self.assertEqual(value["schema_version"], 1)
        self.assertEqual(value["product_id"], "llama")
        return value

    def test_describe_returns_product_descriptor(self) -> None:
        completed = self.run_manage("describe", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = self.response(completed)
        self.assertEqual(response["operation"], "describe")
        descriptor = response["details"]["llama"]["descriptor"]
        self.assertEqual(descriptor["product_id"], "llama")
        self.assertEqual(descriptor["ports"][0]["address"], "127.0.0.1")

    def test_install_dry_run_is_stable_and_non_mutating(self) -> None:
        first = self.run_manage("install", "--dry-run", "--json")
        second = self.run_manage("install", "--dry-run", "--json")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        first_response = self.response(first)
        second_response = self.response(second)
        self.assertEqual(first_response["phase"], "plan")
        self.assertFalse(first_response["changed"])
        self.assertTrue(first_response["requires_confirmation"])
        self.assertEqual(
            first_response["plan_digest"], second_response["plan_digest"]
        )
        self.assertFalse(Path("/run/lock/llama.lock").exists())

    def test_purge_plan_requires_explicit_destructive_confirmation(self) -> None:
        completed = self.run_manage(
            "uninstall", "--purge", "--dry-run", "--json"
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = self.response(completed)
        self.assertEqual(
            response["required_inputs"],
            [{"name": "confirmation", "secret": False}],
        )

    def test_noninteractive_mutation_requires_yes_before_root_or_mutation(self) -> None:
        completed = self.run_manage(
            "install",
            "--non-interactive",
            "--json",
            environment={"LLAMA_NONINTERACTIVE": "1"},
        )
        self.assertEqual(completed.returncode, 64, completed.stderr)
        response = self.response(completed)
        self.assertEqual(response["errors"][0]["code"], "CONFIRMATION_REQUIRED")

    def test_unknown_product_environment_fails_closed(self) -> None:
        completed = self.run_manage(
            "describe",
            "--json",
            environment={"LLAMA_RAW_SECRET": "must-not-be-accepted"},
        )
        self.assertEqual(completed.returncode, 65, completed.stderr)
        response = self.response(completed)
        self.assertEqual(response["errors"][0]["code"], "UNKNOWN_ENVIRONMENT")
        self.assertNotIn("must-not-be-accepted", completed.stdout)
        self.assertNotIn("must-not-be-accepted", completed.stderr)

    def test_request_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = root / "request.json"
            request.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(request)
            completed = self.run_manage(
                "status", "--request-file", str(link), "--json"
            )
        self.assertEqual(completed.returncode, 73, completed.stderr)
        response = self.response(completed)
        self.assertEqual(response["errors"][0]["code"], "UNSAFE_REQUEST")

    def test_absent_status_is_a_successful_degraded_report(self) -> None:
        completed = self.run_manage("status", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = self.response(completed)
        self.assertEqual(response["status"], "degraded")
        self.assertEqual(
            response["details"]["llama"]["lifecycle"], "missing"
        )


if __name__ == "__main__":
    unittest.main()

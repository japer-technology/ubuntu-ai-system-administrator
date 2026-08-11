from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from forgejo.management import PRODUCT_ID


PRODUCT_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = PRODUCT_ROOT / "scripts/manage.sh"
INSTALLER = PRODUCT_ROOT / "scripts/install.sh"


class ManagementIntegrationTests(unittest.TestCase):
    def run_manager(
        self, *arguments: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["FORGEJO_SOURCE_ROOT"] = str(PRODUCT_ROOT)
        result = subprocess.run(
            [str(ENTRYPOINT), *arguments],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def test_describe_emits_common_response(self) -> None:
        value = json.loads(
            self.run_manager("describe", "--json").stdout
        )
        self.assertEqual(value["product_id"], PRODUCT_ID)
        self.assertEqual(value["operation"], "describe")
        self.assertEqual(value["phase"], "read")
        self.assertEqual(
            value["details"]["forgejo"]["descriptor"]["source_root"],
            "products/forgejo",
        )

    def test_install_dry_run_is_a_secret_free_plan(self) -> None:
        value = json.loads(
            self.run_manager(
                "install",
                "--dry-run",
                "--json",
                "--non-interactive",
            ).stdout
        )
        self.assertEqual(value["phase"], "plan")
        self.assertTrue(value["plan_digest"].startswith("sha256:"))
        self.assertNotIn("password", json.dumps(value).lower())
        self.assertEqual(
            value["details"]["forgejo"]["configuration"]["http_port"],
            3000,
        )

    def test_installer_entrypoint_defaults_to_install(self) -> None:
        environment = dict(os.environ)
        environment["FORGEJO_SOURCE_ROOT"] = str(PRODUCT_ROOT)
        result = subprocess.run(
            [
                str(INSTALLER),
                "--dry-run",
                "--json",
                "--non-interactive",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["operation"], "install")
        self.assertEqual(value["phase"], "plan")

    @unittest.skipUnless(
        os.geteuid() == 0, "root ownership is required for request files"
    )
    def test_strict_request_file_is_accepted(self) -> None:
        request = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "operation": "install",
            "correlation_id": str(uuid.uuid4()),
            "requested_by": "beep",
            "inputs": {"boot": "disabled"},
            "confirmation": None,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as handle:
            json.dump(request, handle)
            handle.write("\n")
            request_path = Path(handle.name)
        try:
            request_path.chmod(0o600)
            value = json.loads(
                self.run_manager(
                    "install",
                    "--request-file",
                    str(request_path),
                    "--dry-run",
                    "--json",
                ).stdout
            )
        finally:
            request_path.unlink()
        self.assertEqual(value["correlation_id"], request["correlation_id"])
        self.assertEqual(
            value["details"]["forgejo"]["configuration"]["boot"],
            "disabled",
        )

    def test_unknown_forgejo_environment_is_rejected(self) -> None:
        environment = dict(os.environ)
        environment["FORGEJO_UNKNOWN_INPUT"] = "unsafe"
        result = subprocess.run(
            [str(ENTRYPOINT), "describe", "--json"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(result.returncode, 65)
        value = json.loads(result.stdout)
        self.assertEqual(value["errors"][0]["code"], "UNKNOWN_ENVIRONMENT")


if __name__ == "__main__":
    unittest.main()

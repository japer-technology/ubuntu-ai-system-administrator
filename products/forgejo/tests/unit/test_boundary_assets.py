from __future__ import annotations

import json
import unittest
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[2]


class BoundaryAssetTests(unittest.TestCase):
    def test_service_is_loopback_hardened_and_product_owned(self) -> None:
        unit = (
            PRODUCT_ROOT / "payload/systemd/forgejo.service"
        ).read_text(encoding="utf-8")
        self.assertIn("User=git", unit)
        self.assertIn(
            "ExecStart=/usr/local/bin/forgejo web --config /etc/forgejo/app.ini",
            unit,
        )
        self.assertIn("NoNewPrivileges=true", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("ReadWritePaths=/var/lib/forgejo", unit)
        self.assertNotIn("/var/run/docker.sock", unit)

    def test_product_has_no_runtime_dependency(self) -> None:
        lock = (
            PRODUCT_ROOT / "payload/agent/requirements.lock"
        ).read_text(encoding="utf-8")
        dependencies = [
            line
            for line in lock.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(dependencies, [])

    def test_descriptor_does_not_claim_runner(self) -> None:
        descriptor = json.loads(
            (PRODUCT_ROOT / "PRODUCT.json").read_text(encoding="utf-8")
        )
        self.assertEqual(descriptor["units"], ["forgejo.service"])
        self.assertNotIn("forgejo-runner", json.dumps(descriptor))


if __name__ == "__main__":
    unittest.main()

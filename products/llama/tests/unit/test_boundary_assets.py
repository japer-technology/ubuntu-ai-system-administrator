from __future__ import annotations

import json
import unittest
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[2]


class BoundaryAssetTests(unittest.TestCase):
    def test_systemd_service_is_loopback_and_unprivileged(self) -> None:
        unit = (PRODUCT_ROOT / "payload/systemd/llama-server.service").read_text(
            encoding="utf-8"
        )
        self.assertIn("User=llama-cpp", unit)
        self.assertIn("Group=llama-cpp", unit)
        self.assertIn("NoNewPrivileges=true", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("InaccessiblePaths=-/opt/ai-zombie", unit)
        self.assertNotIn("0.0.0.0", unit)

    def test_catalogues_pin_digests_and_exact_revisions(self) -> None:
        builds = json.loads(
            (PRODUCT_ROOT / "payload/etc/llama-builds.json").read_text(
                encoding="utf-8"
            )
        )
        models = json.loads(
            (PRODUCT_ROOT / "payload/etc/llama-models.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(builds["commit"]), 40)
        for asset in builds["assets"].values():
            self.assertEqual(len(asset["sha256"]), 64)
            self.assertTrue(asset["url"].startswith("https://github.com/"))
        for model in models["models"]:
            self.assertEqual(len(model["sha256"]), 64)
            self.assertTrue(model["url"].startswith("https://huggingface.co/"))
            self.assertGreater(model["size_bytes"], 0)

    def test_product_has_no_ubuntu_zombie_runtime_import(self) -> None:
        management = (
            PRODUCT_ROOT / "payload/agent/llama/management.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("payload.agent", management)
        self.assertNotIn("/opt/ai-zombie", management)


if __name__ == "__main__":
    unittest.main()

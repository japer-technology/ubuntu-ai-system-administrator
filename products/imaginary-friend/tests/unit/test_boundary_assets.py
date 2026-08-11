from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[2]


class BoundaryAssetTests(unittest.TestCase):
    def test_policy_exposes_only_friend_capabilities(self) -> None:
        policy = json.loads(
            (PRODUCT_ROOT / "payload" / "etc" / "policy.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(policy["capabilities"]),
            {
                "conversation",
                "workspace.read",
                "workspace.change",
                "product.admin",
            },
        )
        self.assertEqual(
            set(policy["absent"]),
            {
                "account",
                "host-inspection",
                "network-tool",
                "package",
                "service",
                "shell",
                "sibling",
                "sudo",
            },
        )

    def test_service_asset_keeps_structural_denials(self) -> None:
        unit = (
            PRODUCT_ROOT
            / "payload"
            / "systemd"
            / "imaginary-friend-chat.service"
        ).read_text(encoding="utf-8")
        for required in (
            "User=friend",
            "SupplementaryGroups=friend-share",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ProtectHome=true",
            "CapabilityBoundingSet=",
            "IPAddressDeny=any",
            "IPAddressAllow=localhost",
            "InaccessiblePaths=/usr/bin/sudo",
            "InaccessiblePaths=/usr/bin/bash",
        ):
            self.assertIn(required, unit)
        self.assertIn("ReadWritePaths=/var/log/imaginary-friend\n", unit)
        self.assertNotIn(
            "ReadWritePaths=/var/log/imaginary-friend/audit.log", unit
        )
        self.assertNotIn("InaccessiblePaths=/opt/", unit)
        self.assertNotIn("ExecStart=/bin/", unit)

    def test_diagnostics_creates_an_exclusive_restricted_archive(self) -> None:
        diagnostics = PRODUCT_ROOT / "payload" / "bin" / "friend-diagnostics"
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [str(diagnostics), "--output-directory", directory],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            archive = Path(completed.stdout.strip())
            self.assertEqual(archive.parent, Path(directory))
            self.assertTrue(archive.is_file())
            self.assertFalse(archive.is_symlink())
            self.assertEqual(os.stat(archive).st_mode & 0o777, 0o600)

    def test_selected_workspace_file_is_disclosed_for_one_turn_only(self) -> None:
        interface = (
            PRODUCT_ROOT
            / "payload"
            / "agent"
            / "friend"
            / "static"
            / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("function clearSelectedFile()", interface)
        self.assertIn(
            "const disclosedFile = selectedFile;\n      clearSelectedFile();",
            interface,
        )
        self.assertIn(
            "selected_files: disclosedFile ? [disclosedFile] : []",
            interface,
        )
        self.assertIn("if (turnPending) return;", interface)
        self.assertGreaterEqual(interface.count("if (turnPending) return;"), 3)
        self.assertGreaterEqual(interface.count("clearSelectedFile();"), 3)


if __name__ == "__main__":
    unittest.main()

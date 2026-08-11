from __future__ import annotations

import io
import os
import stat
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from beep import management


PRODUCT_ROOT = Path(__file__).resolve().parents[2]


def temporary_paths(root: Path) -> management.Paths:
    return management.Paths(
        install_root=root / "opt" / "beep",
        configuration_root=root / "etc" / "beep",
        state_root=root / "var" / "lib" / "beep",
        log_root=root / "var" / "log" / "beep",
        chat_unit=root / "systemd" / "beep-chat.service",
        health_unit=root / "systemd" / "beep-health.service",
        health_timer=root / "systemd" / "beep-health.timer",
        logrotate=root / "logrotate" / "beep",
        sudoers=root / "sudoers" / "90-beep",
        entrypoint=root / "bin" / "beep-manage",
        lock=root / "run" / "beep.lock",
        rollback_root=root / "var" / "lib" / "beep" / "recovery",
    )


class ManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manager = management.Manager(PRODUCT_ROOT)
        self.manager.paths = temporary_paths(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_descriptor_exposes_terminal_kill_operation(self) -> None:
        self.assertIn("kill", management.OPERATIONS)
        self.assertEqual(self.manager.descriptor["operations"], list(management.OPERATIONS))

    def test_interactive_install_collects_validated_configuration(self) -> None:
        arguments = management.parser().parse_args(["install"])
        inputs: dict[str, object] = {}
        answers = [
            "80",
            "",
            "unknown",
            "openai",
            "",
            "",
            "0",
            "",
        ]
        with (
            mock.patch.object(
                management.sys.stdin,
                "isatty",
                return_value=True,
            ),
            mock.patch.object(
                self.manager,
                "_prompt",
                side_effect=answers,
            ),
        ):
            self.manager._prepare_interactive_install(
                arguments,
                inputs,
                request_supplied=False,
                non_interactive=False,
            )
        self.assertEqual(
            inputs,
            {
                "chat_port": 58989,
                "provider": "openai",
                "model": None,
                "model_base_url": None,
                "ttl_days": 7,
            },
        )

    def test_approved_install_skips_setup_questions(self) -> None:
        arguments = management.parser().parse_args(["install", "--yes"])
        with mock.patch.object(self.manager, "_prompt") as prompt:
            self.manager._prepare_interactive_install(
                arguments,
                {},
                request_supplied=False,
                non_interactive=False,
            )
        prompt.assert_not_called()

    def test_interactive_approval_displays_configuration_and_plan(self) -> None:
        invocation = management.Invocation(
            operation="install",
            correlation_id="047fd8bd-ed5f-49f9-8da5-07bfe4ebad14",
            actor="operator",
            inputs={
                "chat_port": 59000,
                "provider": None,
                "ttl_days": 14,
            },
            confirmation=None,
            retain_state=None,
            dry_run=False,
            json_output=False,
            non_interactive=False,
            assume_yes=False,
            supplied_plan_digest=None,
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                management.sys.stdin,
                "isatty",
                return_value=True,
            ),
            mock.patch.object(self.manager, "_prompt", return_value="no"),
            mock.patch("sys.stdout", output),
        ):
            with self.assertRaises(management.ManagementError) as raised:
                self.manager.run(invocation)
        self.assertEqual(raised.exception.code, "CONFIRMATION_REQUIRED")
        self.assertIn("Chat URL:", output.getvalue())
        self.assertIn("http://127.0.0.1:59000/", output.getvalue())
        self.assertIn("Time to live:", output.getvalue())
        self.assertIn("14 days", output.getvalue())
        self.assertIn("Converge Beep-only credentials", output.getvalue())
        self.assertFalse(self.manager.paths.lock.exists())

    def test_interactive_provider_credential_retries_invalid_input(self) -> None:
        with (
            mock.patch.object(
                management.sys.stdin,
                "isatty",
                return_value=True,
            ),
            mock.patch.object(
                management.getpass,
                "getpass",
                side_effect=["", "provider-secret"],
            ) as prompt,
        ):
            value = self.manager._interactive_provider_credential("openai")
        self.assertEqual(value, "provider-secret")
        self.assertEqual(prompt.call_count, 2)

    def test_atomic_write_rejects_non_regular_destination(self) -> None:
        destination = self.root / "destination"
        destination.mkdir()
        with self.assertRaises(management.ManagementError) as raised:
            management.atomic_write(destination, b"value", mode=0o600)
        self.assertEqual(raised.exception.code, "UNSAFE_PATH")

    def test_collision_preflight_detects_independent_group(self) -> None:
        with (
            mock.patch.object(self.manager, "_load_retained", return_value=None),
            mock.patch.object(management.pwd, "getpwnam", side_effect=KeyError),
            mock.patch.object(
                management.grp,
                "getgrnam",
                return_value=types.SimpleNamespace(gr_gid=123),
            ),
        ):
            with self.assertRaises(management.ManagementError) as raised:
                self.manager._collision_preflight(None)
        self.assertEqual(raised.exception.code, "OWNERSHIP_COLLISION")
        self.assertIn("group:beep", raised.exception.message)

    def test_directory_convergence_rejects_regular_file(self) -> None:
        self.manager.paths.install_root.parent.mkdir(parents=True)
        self.manager.paths.install_root.write_text("collision", encoding="utf-8")
        with mock.patch.object(management.os, "chown"):
            with self.assertRaises(management.ManagementError) as raised:
                self.manager._ensure_directories(1000, 1000, [])
        self.assertEqual(raised.exception.code, "UNSAFE_PATH")

    def test_runtime_deployment_preserves_executable_modes(self) -> None:
        node = self.manager.paths.node_root / "bin" / "node"
        node.parent.mkdir(parents=True)
        node.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(node, 0o755)
        self.manager.paths.runtime.mkdir(parents=True)
        configuration = management.Configuration(
            agent_user="beep",
            chat_port=58989,
            provider=None,
            model=None,
            model_base_url=None,
            ttl_days=7,
        )
        with (
            mock.patch.object(self.manager, "_deploy_product_source"),
            mock.patch.object(self.manager, "_deploy_pi_models"),
            mock.patch.object(management.os, "chown"),
        ):
            self.manager._deploy_runtime(configuration, 1000, 1000, [])
        self.assertEqual(stat.S_IMODE(node.stat().st_mode), 0o755)
        self.assertEqual(
            stat.S_IMODE(
                (self.manager.paths.install_root / "bin" / "beep-chat").stat().st_mode
            ),
            0o755,
        )
        self.assertEqual(
            stat.S_IMODE(
                (self.manager.paths.install_root / "agent" / "server.py").stat().st_mode
            ),
            0o644,
        )

    def test_failed_existing_convergence_restores_recovery_snapshot(self) -> None:
        marker = {
            "instance_id": "12d515dc-92f6-44d8-adf1-2ca812197307",
            "version": self.manager.version,
        }
        invocation = management.Invocation(
            operation="update",
            correlation_id="047fd8bd-ed5f-49f9-8da5-07bfe4ebad14",
            actor="operator",
            inputs={},
            confirmation=None,
            retain_state=None,
            dry_run=False,
            json_output=True,
            non_interactive=True,
            assume_yes=True,
            supplied_plan_digest=None,
        )
        configuration = management.Configuration(
            agent_user="beep",
            chat_port=58989,
            provider=None,
            model=None,
            model_base_url=None,
            ttl_days=7,
        )
        failure = management.ManagementError(
            1,
            "DEPLOYMENT_FAILED",
            "deployment failed",
        )
        with (
            mock.patch.object(self.manager, "load_marker", return_value=marker),
            mock.patch.object(self.manager, "_platform_preflight"),
            mock.patch.object(self.manager, "_collision_preflight"),
            mock.patch.object(self.manager, "_port_preflight"),
            mock.patch.object(self.manager, "_prepare_interactive_secrets"),
            mock.patch.object(self.manager, "_stop_services"),
            mock.patch.object(self.manager, "_create_recovery_snapshot"),
            mock.patch.object(
                self.manager,
                "_converge_resources",
                side_effect=failure,
            ),
            mock.patch.object(self.manager, "_execute_rollback") as rollback,
        ):
            with self.assertRaises(management.ManagementError) as raised:
                self.manager._execute_converge(invocation, configuration)
        self.assertIs(raised.exception, failure)
        rollback.assert_called_once_with()
        self.assertIn("restored automatically", failure.recovery[-1])


if __name__ == "__main__":
    unittest.main()

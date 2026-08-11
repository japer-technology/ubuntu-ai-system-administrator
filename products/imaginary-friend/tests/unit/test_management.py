from __future__ import annotations

import argparse
import io
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from friend.auth import hash_password
from friend.database import Database
from friend.management import (
    Invocation,
    ManagementError,
    Manager,
    Paths,
    read_secret_file,
)

SOURCE_ROOT = Path(__file__).resolve().parents[2]


class FakeDatabase:
    def __init__(self, *, suspended: bool = False) -> None:
        self.suspended = suspended

    def settings(self) -> dict[str, bool]:
        return {"suspended": self.suspended}

    def set_suspended(self, _suspended: bool) -> None:
        self.suspended = _suspended


class ManagementUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.paths = Paths(
            install_root=root / "opt" / "imaginary-friend",
            configuration_root=root / "etc" / "imaginary-friend",
            state_root=root / "var" / "lib" / "imaginary-friend",
            log_root=root / "var" / "log" / "imaginary-friend",
            workspace_parent=root / "srv" / "imaginary-friend",
            unit=root / "etc" / "systemd" / "imaginary-friend-chat.service",
            logrotate=root / "etc" / "logrotate.d" / "imaginary-friend",
            entrypoint=root / "usr" / "local" / "sbin" / "friend-manage",
            diagnostics=root / "usr" / "local" / "bin" / "friend-diagnostics",
            lock=root / "run" / "lock" / "imaginary-friend.lock",
            rollback_root=root / "opt" / ".imaginary-friend-rollback",
        )
        self.manager = Manager(SOURCE_ROOT)
        self.manager.paths = self.paths
        self.instance_id = str(uuid.uuid4())
        self.marker = {
            "schema_version": 1,
            "product_id": "imaginary-friend",
            "instance_id": self.instance_id,
            "version": self.manager.version,
            "source_revision": "source-tree-sha256:" + "0" * 64,
            "installed_at": "2026-08-08T00:00:00Z",
            "install_root": str(self.paths.install_root),
            "lifecycle_entrypoint": str(self.paths.entrypoint),
            "artifact_sha256": None,
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invocation(self, operation: str = "install") -> Invocation:
        return Invocation(
            operation,
            str(uuid.uuid4()),
            "operator",
            {
                "owner_user": "owner",
                "model_base_url": "http://127.0.0.1:8080/v1",
                "model": "fixture-friend",
                "history_retention_days": 30,
                "audit_retention_days": 90,
            },
            None,
            None,
            False,
            True,
            True,
            True,
            None,
            None,
            None,
            [Path("/srv/imaginary-friend/workspace")],
        )

    def test_clean_install_boundary_check_accepts_valid_transaction(self) -> None:
        missing = ManagementError(
            66, "INSTALLATION_MISSING", "Imaginary Friend is not installed."
        )
        with mock.patch.object(self.manager, "load_marker", side_effect=missing):
            with mock.patch.object(
                self.manager, "_transaction_instance", return_value=self.instance_id
            ):
                checks = self.manager.verify_checks(
                    probe_runtime=False, allow_transaction=True
                )
        self.assertEqual(checks[0]["id"], "installation_transaction")
        self.assertEqual(checks[0]["status"], "pass")

    def test_clean_install_writes_marker_only_after_boundary_checks(self) -> None:
        events: list[str] = []

        def verify(**options: bool) -> list[dict[str, str]]:
            self.assertTrue(options["allow_transaction"])
            self.assertNotIn("marker", events)
            events.append("verify")
            return [self.manager.check("boundaries", True, "Boundaries passed.")]

        def write_marker(*_args: object, **_kwargs: object) -> None:
            events.append("marker")

        names = {
            "_platform_preflight": mock.DEFAULT,
            "_validate_owner": mock.DEFAULT,
            "_collision_preflight": mock.DEFAULT,
            "_workspace_preflight": mock.DEFAULT,
            "_probe_model": mock.DEFAULT,
            "_ensure_transaction": mock.DEFAULT,
            "_ensure_accounts": mock.DEFAULT,
            "_ensure_paths": mock.DEFAULT,
            "_stage_runtime": mock.DEFAULT,
            "_deploy_configuration": mock.DEFAULT,
            "_initialize_database": mock.DEFAULT,
            "_deploy_unit": mock.DEFAULT,
            "_validate_runtime_as_friend": mock.DEFAULT,
            "_start_service": mock.DEFAULT,
            "_service_health": mock.DEFAULT,
            "verify_checks": mock.DEFAULT,
            "_write_marker": mock.DEFAULT,
            "_restore_failed_switch": mock.DEFAULT,
        }
        with mock.patch.multiple(self.manager, **names) as patched, mock.patch.object(
            self.manager, "load_marker", side_effect=[None, self.marker]
        ), mock.patch("friend.management.grp.getgrnam") as group:
            patched["_ensure_transaction"].return_value = self.instance_id
            patched["_ensure_accounts"].return_value = (100, 200)
            patched["_stage_runtime"].return_value = None
            patched["_initialize_database"].return_value = FakeDatabase()
            patched["_service_health"].return_value = True
            patched["verify_checks"].side_effect = verify
            patched["_write_marker"].side_effect = write_marker
            group.return_value.gr_gid = 100
            self.manager._execute_install(self.invocation())
        self.assertEqual(events, ["verify", "marker"])
        patched["_restore_failed_switch"].assert_not_called()

    def test_deployment_failure_requests_runtime_restore(self) -> None:
        names = {
            "_platform_preflight": mock.DEFAULT,
            "_validate_owner": mock.DEFAULT,
            "_collision_preflight": mock.DEFAULT,
            "_workspace_preflight": mock.DEFAULT,
            "_probe_model": mock.DEFAULT,
            "_snapshot_state": mock.DEFAULT,
            "_ensure_transaction": mock.DEFAULT,
            "_ensure_accounts": mock.DEFAULT,
            "_ensure_paths": mock.DEFAULT,
            "_stage_runtime": mock.DEFAULT,
            "_deploy_configuration": mock.DEFAULT,
            "_restore_failed_switch": mock.DEFAULT,
        }
        with mock.patch.multiple(self.manager, **names) as patched, mock.patch.object(
            self.manager, "load_marker", return_value=self.marker
        ), mock.patch("friend.management.grp.getgrnam") as group:
            patched["_ensure_transaction"].return_value = self.instance_id
            patched["_ensure_accounts"].return_value = (100, 200)
            patched["_stage_runtime"].return_value = self.manager.version
            patched["_deploy_configuration"].side_effect = OSError(
                "simulated deployment failure"
            )
            group.return_value.gr_gid = 100
            with self.assertRaises(OSError):
                self.manager._execute_install(self.invocation())
        patched["_restore_failed_switch"].assert_called_once_with(
            runtime_switched=True,
            recovery_source=self.paths.operation_recovery,
        )

    def test_reinstall_preserves_suspension_and_keeps_service_stopped(self) -> None:
        names = {
            "_platform_preflight": mock.DEFAULT,
            "_validate_owner": mock.DEFAULT,
            "_collision_preflight": mock.DEFAULT,
            "_workspace_preflight": mock.DEFAULT,
            "_probe_model": mock.DEFAULT,
            "_snapshot_state": mock.DEFAULT,
            "_ensure_transaction": mock.DEFAULT,
            "_ensure_accounts": mock.DEFAULT,
            "_ensure_paths": mock.DEFAULT,
            "_stage_runtime": mock.DEFAULT,
            "_deploy_configuration": mock.DEFAULT,
            "_initialize_database": mock.DEFAULT,
            "_deploy_unit": mock.DEFAULT,
            "_validate_runtime_as_friend": mock.DEFAULT,
            "_start_service": mock.DEFAULT,
            "_stop_service": mock.DEFAULT,
            "verify_checks": mock.DEFAULT,
            "_write_marker": mock.DEFAULT,
            "_restore_failed_switch": mock.DEFAULT,
        }
        with mock.patch.multiple(self.manager, **names) as patched, mock.patch.object(
            self.manager, "load_marker", return_value=self.marker
        ), mock.patch("friend.management.grp.getgrnam") as group:
            patched["_ensure_transaction"].return_value = self.instance_id
            patched["_ensure_accounts"].return_value = (100, 200)
            patched["_stage_runtime"].return_value = self.manager.version
            patched["_initialize_database"].return_value = FakeDatabase(
                suspended=True
            )
            patched["verify_checks"].return_value = [
                self.manager.check("boundaries", True, "Boundaries passed.")
            ]
            group.return_value.gr_gid = 100
            self.manager._execute_install(self.invocation())
        patched["_start_service"].assert_not_called()
        patched["_stop_service"].assert_called_once_with(disable=False)
        patched["verify_checks"].assert_called_once_with(
            probe_runtime=False,
            allow_transaction=False,
        )

    def test_service_identity_rejects_unexpected_supplementary_group(self) -> None:
        account = SimpleNamespace(
            pw_gid=100,
            pw_shell="/usr/sbin/nologin",
            pw_dir=str(self.paths.state_root),
        )
        groups = [
            SimpleNamespace(gr_name="friend", gr_gid=100, gr_mem=[]),
            SimpleNamespace(gr_name="friend-share", gr_gid=200, gr_mem=["friend"]),
            SimpleNamespace(gr_name="unexpected", gr_gid=300, gr_mem=["friend"]),
        ]

        def group_by_name(name: str) -> SimpleNamespace:
            return {
                "friend": groups[0],
                "friend-share": groups[1],
            }[name]

        with mock.patch("friend.management.pwd.getpwnam", return_value=account):
            with mock.patch(
                "friend.management.grp.getgrnam", side_effect=group_by_name
            ):
                with mock.patch("friend.management.grp.getgrall", return_value=groups):
                    with self.assertRaises(ManagementError) as raised:
                        self.manager._ensure_accounts("owner")
        self.assertEqual(raised.exception.code, "UNSAFE_COLLISION")

    def test_resume_request_rejects_configuration_inputs(self) -> None:
        request = {
            "schema_version": 1,
            "product_id": "imaginary-friend",
            "operation": "resume",
            "correlation_id": str(uuid.uuid4()),
            "requested_by": "operator",
            "inputs": {"history_retention_days": 60},
            "confirmation": None,
        }
        with mock.patch("friend.management.check_secure_file"):
            with mock.patch("friend.management.read_json", return_value=request):
                with self.assertRaises(ManagementError) as raised:
                    self.manager._request(Path("/request.json"), "resume")
        self.assertEqual(raised.exception.code, "UNKNOWN_INPUT")

    def test_unexpected_failure_keeps_correlation_and_is_audited(self) -> None:
        invocation = self.invocation("suspend")
        failure = OSError("simulated failure")
        with mock.patch("friend.management.Manager") as manager_type:
            manager = manager_type.return_value
            manager.version = self.manager.version
            manager.invocation.return_value = invocation
            manager.run.side_effect = failure
            manager.instance_id.return_value = self.instance_id
            manager.steps_for.return_value = []
            with mock.patch("friend.management._print_result") as output:
                exit_code = __import__(
                    "friend.management", fromlist=["main"]
                ).main(["suspend", "--json"])
        self.assertEqual(exit_code, 1)
        result = output.call_args.args[0]
        self.assertEqual(result.correlation_id, invocation.correlation_id)
        self.assertEqual(result.instance_id, self.instance_id)
        manager.audit_failure.assert_called_once_with(invocation, failure)

    def test_read_failure_audit_uses_read_phase(self) -> None:
        self.paths.audit.parent.mkdir(parents=True)
        self.paths.audit.touch()
        invocation = self.invocation("status")
        with mock.patch.object(
            self.manager, "_append_lifecycle_audit"
        ) as append_audit:
            self.manager.audit_failure(invocation, OSError("simulated failure"))
        self.assertEqual(append_audit.call_args.kwargs["phase"], "read")
        self.assertEqual(append_audit.call_args.kwargs["failure_type"], "OSError")

    def test_resume_prepares_installed_model_configuration(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        self.paths.configuration_root.mkdir(parents=True)
        database = Database(self.paths.database)
        database.initialize(
            password_hash=hash_password("initial owner password"),
            model_base_url="http://127.0.0.1:8080/v1",
            model="fixture-friend",
            history_retention_days=30,
            audit_retention_days=90,
        )
        (self.paths.configuration_root / "config.json").write_text(
            '{"owner_user":"owner"}', encoding="utf-8"
        )
        arguments = argparse.Namespace(
            operation="resume",
            request_file=None,
            correlation_id=None,
            dry_run=True,
            json=True,
            non_interactive=False,
            yes=False,
            plan_digest=None,
        )
        with mock.patch.dict(
            os.environ, {"FRIEND_NONINTERACTIVE": "1"}, clear=True
        ):
            invocation = self.manager.invocation(arguments)
        self.assertEqual(
            invocation.inputs["model_base_url"], "http://127.0.0.1:8080/v1"
        )
        self.assertEqual(invocation.inputs["model"], "fixture-friend")

    def test_unattended_reinstall_uses_existing_credentials_and_settings(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        self.paths.configuration_root.mkdir(parents=True)
        Database(self.paths.database).initialize(
            password_hash=hash_password("initial owner password"),
            model_base_url="http://127.0.0.1:8080/v1",
            model="fixture-friend",
            history_retention_days=30,
            audit_retention_days=90,
        )
        (self.paths.configuration_root / "config.json").write_text(
            '{"owner_user":"owner"}', encoding="utf-8"
        )
        arguments = argparse.Namespace(
            operation="install",
            request_file=None,
            correlation_id=None,
            dry_run=True,
            json=True,
            non_interactive=False,
            yes=False,
            plan_digest=None,
        )
        with mock.patch.dict(
            os.environ, {"FRIEND_NONINTERACTIVE": "1"}, clear=True
        ):
            invocation = self.manager.invocation(arguments)
        self.assertIsNone(invocation.password)
        self.assertEqual(invocation.inputs["owner_user"], "owner")
        self.assertEqual(invocation.inputs["model"], "fixture-friend")

    def test_interactive_install_reprompts_for_short_owner_password(self) -> None:
        invocation = self.invocation()
        invocation.non_interactive = False
        invocation.assume_yes = False
        with (
            mock.patch("friend.management.sys.stdin.isatty", return_value=True),
            mock.patch(
                "friend.management.getpass.getpass",
                side_effect=[
                    "short",
                    "short",
                    "valid owner password",
                    "valid owner password",
                ],
            ),
            mock.patch("friend.management.print"),
        ):
            self.manager._prepare_configuration_inputs(invocation)
        self.assertEqual(invocation.password, "valid owner password")

    def test_interactive_install_collects_validated_configuration(self) -> None:
        invocation = Invocation(
            operation="install",
            correlation_id=str(uuid.uuid4()),
            actor="operator",
            inputs={},
            confirmation=None,
            retain_state=None,
            dry_run=False,
            json_output=False,
            non_interactive=False,
            assume_yes=False,
            supplied_plan_digest=None,
        )
        with (
            mock.patch("friend.management.sys.stdin.isatty", return_value=True),
            mock.patch.object(
                self.manager,
                "_prompt",
                side_effect=["owner", "", "fixture-friend", "", ""],
            ),
            mock.patch.object(self.manager, "_prompt_secret", return_value=""),
            mock.patch.object(self.manager, "_validate_owner"),
            mock.patch("friend.management.print"),
        ):
            self.manager._prepare_configuration_inputs(invocation)
        self.assertEqual(invocation.inputs["owner_user"], "owner")
        self.assertEqual(
            invocation.inputs["model_base_url"],
            "http://127.0.0.1:8080/v1",
        )
        self.assertEqual(invocation.inputs["model"], "fixture-friend")
        self.assertEqual(invocation.inputs["history_retention_days"], 30)
        self.assertEqual(invocation.inputs["audit_retention_days"], 90)
        self.assertIsNotNone(invocation.generated_password)

    def test_request_install_does_not_require_an_interactive_terminal(self) -> None:
        invocation = self.invocation()
        invocation.non_interactive = False
        invocation.request_supplied = True
        invocation.inputs["owner_password_file"] = "/secure/password"
        with (
            mock.patch(
                "friend.management.read_secret_file",
                return_value="valid owner password",
            ),
            mock.patch.object(self.manager, "_prompt") as prompt,
            mock.patch.object(self.manager, "_prompt_secret") as prompt_secret,
        ):
            self.manager._prepare_configuration_inputs(invocation)
        prompt.assert_not_called()
        prompt_secret.assert_not_called()
        self.assertEqual(invocation.password, "valid owner password")

    def test_interactive_approval_displays_configuration_and_plan(self) -> None:
        invocation = self.invocation()
        invocation.non_interactive = False
        invocation.assume_yes = False
        invocation.json_output = False
        output = io.StringIO()
        with (
            mock.patch.object(self.manager, "_prompt", return_value="no"),
            mock.patch("friend.management.os.geteuid", return_value=0),
            mock.patch("sys.stdout", output),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager.run(invocation)
        self.assertEqual(raised.exception.code, "PLAN_NOT_APPROVED")
        self.assertIn("Human owner:", output.getvalue())
        self.assertIn("Model endpoint:", output.getvalue())
        self.assertIn("fixture-friend", output.getvalue())
        self.assertIn("Validate platform, model, inputs", output.getvalue())
        self.assertFalse(self.paths.lock.exists())

    def test_repair_preserves_restricted_workspace_without_new_file(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        workspace = Path(self.temporary.name) / "workspace"
        workspace.mkdir()
        details = workspace.stat()
        database = Database(self.paths.database)
        database.initialize(
            password_hash=hash_password("initial owner password"),
            model_base_url="http://127.0.0.1:8080/v1",
            model="fixture-friend",
            history_retention_days=30,
            audit_retention_days=90,
        )
        workspace_id = database.register_workspace(
            canonical_root=str(workspace),
            root_device=details.st_dev,
            root_inode=details.st_ino,
            enabled=False,
        )
        invocation = self.invocation("repair")
        self.manager._initialize_database(
            invocation,
            friend_uid=os.getuid(),
            friend_gid=os.getgid(),
            workspaces=[workspace],
        )
        self.assertFalse(
            Database(self.paths.database).workspace(
                workspace_id, require_enabled=False
            )["enabled"]
        )

    def test_existing_workspace_requires_setgid_group_inheritance(self) -> None:
        parent = Path(self.temporary.name) / "workspaces"
        default = parent / "workspace"
        additional = parent / "projects"
        default.mkdir(parents=True)
        additional.mkdir()
        default.chmod(0o2770)
        additional.chmod(0o0770)
        group = SimpleNamespace(gr_gid=os.getgid())

        with mock.patch("friend.management.DEFAULT_WORKSPACE", default):
            with mock.patch("friend.management.grp.getgrnam", return_value=group):
                with self.assertRaises(ManagementError) as raised:
                    self.manager._workspace_preflight([default, additional])
                self.assertEqual(raised.exception.code, "UNSAFE_WORKSPACE")

                additional.chmod(0o2770)
                self.manager._workspace_preflight([default, additional])

    def test_dry_run_preflight_reports_missing_installation(self) -> None:
        invocation = self.invocation("suspend")
        invocation.dry_run = True
        checks = self.manager.preflight_checks(invocation, network=False)
        self.assertEqual(checks[0]["id"], "ownership_marker")
        self.assertEqual(checks[0]["status"], "fail")

    def test_backup_dry_run_requires_existing_destination(self) -> None:
        missing = Path(self.temporary.name) / "missing-backup"
        with self.assertRaises(ManagementError) as raised:
            self.manager._validate_backup_destination(missing, dry_run=True)
        self.assertEqual(raised.exception.exit_code, 66)

    def test_lifecycle_retention_rejects_fractional_values(self) -> None:
        with self.assertRaises(ManagementError) as raised:
            self.manager._bounded_integer(
                30.5, "history_retention_days", 1, 365
            )
        self.assertEqual(raised.exception.code, "INVALID_INPUT")

    def test_same_version_switch_preserves_previous_rollback(self) -> None:
        self.paths.install_root.mkdir(parents=True)
        (self.paths.install_root / "VERSION").write_text(
            self.manager.version, encoding="utf-8"
        )
        self.paths.rollback_root.mkdir()
        previous_version = "2026.08.07.00.00.00"
        (self.paths.rollback_root / "VERSION").write_text(
            previous_version, encoding="utf-8"
        )
        stage = self.paths.install_root.parent / ".stage"
        stage.mkdir()
        (stage / "VERSION").write_text(self.manager.version, encoding="utf-8")
        (stage / "replacement").write_text("new runtime", encoding="utf-8")

        switched_from = self.manager._switch_staged_runtime(
            stage, preserve_rollback=True
        )

        self.assertEqual(switched_from, self.manager.version)
        self.assertTrue((self.paths.install_root / "replacement").is_file())
        self.assertEqual(
            (self.paths.rollback_root / "VERSION").read_text(encoding="utf-8"),
            previous_version,
        )
        self.manager._commit_runtime_switch()
        self.assertEqual(
            (self.paths.rollback_root / "VERSION").read_text(encoding="utf-8"),
            previous_version,
        )

    def test_failed_same_version_switch_restores_current_runtime(self) -> None:
        self.paths.install_root.mkdir(parents=True)
        (self.paths.install_root / "VERSION").write_text(
            self.manager.version, encoding="utf-8"
        )
        (self.paths.install_root / "current").write_text(
            "current runtime", encoding="utf-8"
        )
        self.paths.rollback_root.mkdir()
        previous_version = "2026.08.07.00.00.00"
        (self.paths.rollback_root / "VERSION").write_text(
            previous_version, encoding="utf-8"
        )
        stage = self.paths.install_root.parent / ".stage"
        stage.mkdir()
        (stage / "VERSION").write_text(self.manager.version, encoding="utf-8")

        self.manager._switch_staged_runtime(stage, preserve_rollback=True)
        with mock.patch.object(self.manager, "_stop_service"):
            self.manager._restore_failed_switch(
                runtime_switched=True,
                recovery_source=self.paths.operation_recovery,
            )

        self.assertTrue((self.paths.install_root / "current").is_file())
        self.assertEqual(
            (self.paths.rollback_root / "VERSION").read_text(encoding="utf-8"),
            previous_version,
        )

    def test_password_file_must_be_one_bounded_utf8_line(self) -> None:
        password_file = Path(self.temporary.name) / "password"
        for value in ("long enough\nsecond line", "x" * 1025):
            password_file.write_text(value, encoding="utf-8")
            details = password_file.stat()
            with mock.patch(
                "friend.management.check_secure_file",
                return_value=details,
            ):
                with self.assertRaises(ManagementError) as raised:
                    read_secret_file(password_file)
            self.assertEqual(raised.exception.code, "INVALID_SECRET")


if __name__ == "__main__":
    unittest.main()

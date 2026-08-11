from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from llama.management import (
    Configuration,
    Invocation,
    LEGACY_UNIT_SHA256,
    ManagementError,
    Manager,
    Paths,
)


SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.paths = Paths(
            install_root=root / "opt/llama.cpp",
            configuration_root=root / "etc/llama.cpp",
            state_root=root / "var/lib/llama.cpp",
            log_root=root / "var/log/llama.cpp",
            cache_root=root / "var/cache/llama.cpp",
            unit=root / "etc/systemd/system/llama-server.service",
            logrotate=root / "etc/logrotate.d/llama",
            entrypoint=root / "usr/local/sbin/llama-manage",
            manager=root / "usr/local/bin/llama-manager",
            lock=root / "run/lock/llama.lock",
            backup_root=root / "var/backups/llama.cpp",
        )
        self.manager = Manager(SOURCE_ROOT)
        self.manager.paths = self.paths

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invocation(
        self,
        operation: str = "install",
        *,
        inputs: dict[str, object] | None = None,
        dry_run: bool = False,
    ) -> Invocation:
        return Invocation(
            operation=operation,
            correlation_id=str(uuid.uuid4()),
            actor="operator",
            inputs=inputs or {},
            confirmation=None,
            retain_state=True if operation == "uninstall" else None,
            dry_run=dry_run,
            json_output=True,
            non_interactive=True,
            assume_yes=True,
            supplied_plan_digest=None,
        )

    def test_descriptor_preserves_existing_host_namespace(self) -> None:
        descriptor = self.manager.descriptor
        self.assertEqual(descriptor["install_root"], "/opt/llama.cpp")
        self.assertEqual(descriptor["state_root"], "/var/lib/llama.cpp")
        self.assertEqual(descriptor["accounts"][0]["name"], "llama-cpp")
        self.assertEqual(descriptor["ports"][0]["address"], "127.0.0.1")
        self.assertEqual(descriptor["ports"][0]["port"], 8080)

    def test_default_configuration_uses_pinned_catalogues(self) -> None:
        configuration = self.manager.configuration(self.invocation())
        self.assertEqual(configuration.model_id, "smollm2-360m-instruct-q4_k_m")
        self.assertEqual(configuration.context_size, 2048)
        self.assertEqual(configuration.runtime_release, "b10054")
        self.assertEqual(
            configuration.object()["runtime_dir"], str(self.paths.current)
        )
        self.assertTrue(
            str(configuration.model_path).startswith(str(self.paths.models))
        )

    def test_configuration_rejects_unapproved_model_and_oversized_context(self) -> None:
        with self.assertRaises(ManagementError) as raised:
            self.manager.configuration(
                self.invocation(inputs={"model_id": "unapproved"})
            )
        self.assertEqual(raised.exception.code, "MODEL_NOT_APPROVED")
        with self.assertRaises(ManagementError) as raised:
            self.manager.configuration(
                self.invocation(inputs={"context_size": 4096})
            )
        self.assertEqual(raised.exception.code, "INVALID_CONFIGURATION")

    def test_fixed_port_cannot_be_overridden(self) -> None:
        with mock.patch.dict(os.environ, {"LLAMA_PORT": "8081"}):
            with self.assertRaises(ManagementError) as raised:
                self.manager.configuration(self.invocation())
        self.assertEqual(raised.exception.code, "INVALID_CONFIGURATION")

    def test_dry_run_does_not_create_lock_or_product_paths(self) -> None:
        invocation = self.invocation(dry_run=True)
        result, exit_code = self.manager.run(invocation)
        self.assertEqual(exit_code, 0)
        self.assertEqual(result.phase, "plan")
        self.assertFalse(result.changed)
        self.assertTrue(result.plan_digest.startswith("sha256:"))
        self.assertFalse(self.paths.lock.exists())
        self.assertFalse(self.paths.install_root.exists())

    def test_archive_member_rejects_traversal_and_escaping_link(self) -> None:
        traversal = tarfile.TarInfo("../escape")
        escaping_link = tarfile.TarInfo("root/link")
        escaping_link.type = tarfile.SYMTYPE
        escaping_link.linkname = "../../escape"
        safe = tarfile.TarInfo("root/llama-server")
        self.assertFalse(self.manager._safe_archive_member(traversal))
        self.assertFalse(self.manager._safe_archive_member(escaping_link))
        self.assertTrue(self.manager._safe_archive_member(safe))

    def test_clean_install_writes_marker_only_after_boundary_checks(self) -> None:
        configuration = Configuration(
            "smollm2-360m-instruct-q4_k_m",
            2048,
            2,
            "disabled",
            "b10054",
            self.paths.versions / "b10054-amd64",
            self.paths.models / "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        )
        events: list[str] = []
        names = {
            "_platform_preflight": mock.DEFAULT,
            "_collision_preflight": mock.DEFAULT,
            "_port_preflight": mock.DEFAULT,
            "_ensure_directory": mock.DEFAULT,
            "_ensure_transaction": mock.DEFAULT,
            "_ensure_log_ownership": mock.DEFAULT,
            "_ensure_account": mock.DEFAULT,
            "_deploy_product": mock.DEFAULT,
            "_install_runtime": mock.DEFAULT,
            "_install_model": mock.DEFAULT,
            "_deploy_configuration": mock.DEFAULT,
            "_apply_service_state": mock.DEFAULT,
            "_post_install_checks": mock.DEFAULT,
            "_write_marker": mock.DEFAULT,
        }
        with mock.patch.multiple(self.manager, **names) as patched:
            patched["_collision_preflight"].return_value = (
                None,
                "bfe451ff-ae20-4a45-872f-85a4566dc590",
            )
            patched["_ensure_account"].return_value = (100, 100)
            patched["_post_install_checks"].side_effect = lambda *_args, **_kwargs: (
                events.append("checks") or []
            )
            patched["_write_marker"].side_effect = lambda *_args, **_kwargs: (
                events.append("marker")
            )
            self.manager._execute_install(
                self.invocation(), configuration, snapshot_on_change=True
            )
        self.assertEqual(events, ["checks", "marker"])
        patched["_ensure_directory"].assert_any_call(
            self.paths.log_root, 0o750, 0, 100, mock.ANY
        )

    def test_failed_boundary_check_never_writes_marker(self) -> None:
        configuration = Configuration(
            "smollm2-360m-instruct-q4_k_m",
            2048,
            2,
            "disabled",
            "b10054",
            self.paths.versions / "b10054-amd64",
            self.paths.models / "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        )
        names = {
            "_platform_preflight": mock.DEFAULT,
            "_collision_preflight": mock.DEFAULT,
            "_port_preflight": mock.DEFAULT,
            "_ensure_directory": mock.DEFAULT,
            "_ensure_transaction": mock.DEFAULT,
            "_ensure_log_ownership": mock.DEFAULT,
            "_ensure_account": mock.DEFAULT,
            "_deploy_product": mock.DEFAULT,
            "_install_runtime": mock.DEFAULT,
            "_install_model": mock.DEFAULT,
            "_deploy_configuration": mock.DEFAULT,
            "_apply_service_state": mock.DEFAULT,
            "_post_install_checks": mock.DEFAULT,
            "_write_marker": mock.DEFAULT,
        }
        with mock.patch.multiple(self.manager, **names) as patched:
            patched["_collision_preflight"].return_value = (
                None,
                "bfe451ff-ae20-4a45-872f-85a4566dc590",
            )
            patched["_ensure_account"].return_value = (100, 100)
            patched["_post_install_checks"].return_value = [
                self.manager.check(
                    "health", False, "Health failed.", "Inspect the service."
                )
            ]
            with self.assertRaises(ManagementError):
                self.manager._execute_install(
                    self.invocation(), configuration, snapshot_on_change=True
                )
        patched["_write_marker"].assert_not_called()

    def test_backup_destination_cannot_be_inside_product_state(self) -> None:
        invocation = self.invocation(
            "backup",
            inputs={"backup_destination": str(self.paths.state_root / "backup")},
        )
        with self.assertRaises(ManagementError) as raised:
            self.manager._backup_destination(invocation)
        self.assertEqual(raised.exception.code, "INVALID_BACKUP_DESTINATION")

    def test_backup_destination_cannot_resolve_inside_product_state(self) -> None:
        root = self.paths.install_root.parents[1]
        alias = root / "backup-alias"
        alias.symlink_to(self.paths.state_root, target_is_directory=True)
        invocation = self.invocation(
            "backup",
            inputs={"backup_destination": str(alias / "backup")},
        )
        with self.assertRaises(ManagementError) as raised:
            self.manager._backup_destination(invocation)
        self.assertEqual(raised.exception.code, "INVALID_BACKUP_DESTINATION")

    def test_configuration_rejects_model_path_that_resolves_outside_models(
        self,
    ) -> None:
        configuration = self.manager.configuration(self.invocation())
        value = configuration.object()
        value["model_path"] = str(
            self.paths.models
            / ".."
            / "outside"
            / configuration.model_path.name
        )
        self.assertFalse(self.manager._configuration_paths_valid(value))

    def test_unknown_operation_input_is_rejected(self) -> None:
        args = mock.Mock(
            operation="resume",
            request_file=None,
            correlation_id=None,
            confirmation=None,
            purge=False,
            non_interactive=False,
            dry_run=False,
            json=True,
            yes=False,
            plan_digest=None,
        )
        request = {
            "schema_version": 1,
            "product_id": "llama",
            "operation": "resume",
            "correlation_id": str(uuid.uuid4()),
            "requested_by": "operator",
            "inputs": {"context_size": 1024},
            "confirmation": None,
        }
        with mock.patch.object(self.manager, "_request", return_value=request):
            args.request_file = Path("/request.json")
            with self.assertRaises(ManagementError) as raised:
                self.manager.invocation(args)
        self.assertEqual(raised.exception.code, "UNKNOWN_INPUT")

    def test_live_configuration_change_restarts_active_service(self) -> None:
        configuration = Configuration(
            "smollm2-360m-instruct-q4_k_m",
            2048,
            2,
            "enabled",
            "b10054",
            self.paths.versions / "b10054-amd64",
            self.paths.models / "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        )
        changed = [str(self.paths.config)]
        with (
            mock.patch.object(self.manager, "_service_enabled", return_value="enabled"),
            mock.patch.object(self.manager, "_service_active", return_value=True),
            mock.patch.object(self.manager, "_health", return_value=True),
            mock.patch.object(self.manager, "_run") as run,
        ):
            self.manager._apply_service_state(
                configuration,
                changed,
                verify_health=True,
                restart_required=True,
            )
        run.assert_any_call(["systemctl", "restart", "llama-server.service"])
        self.assertIn("llama-server.service:restarted", changed)

    def test_disabled_boot_stops_and_disables_service(self) -> None:
        configuration = Configuration(
            "smollm2-360m-instruct-q4_k_m",
            2048,
            2,
            "disabled",
            "b10054",
            self.paths.versions / "b10054-amd64",
            self.paths.models / "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        )
        changed: list[str] = []
        with (
            mock.patch.object(self.manager, "_run"),
            mock.patch.object(
                self.manager, "_stop_service", return_value=True
            ) as stop_service,
        ):
            self.manager._apply_service_state(
                configuration,
                changed,
                verify_health=False,
                restart_required=False,
            )
        stop_service.assert_called_once_with(disable=True)
        self.assertEqual(changed, ["llama-server.service:disabled-stopped"])

    def test_suspended_install_preserves_service_enablement(self) -> None:
        configuration = Configuration(
            "smollm2-360m-instruct-q4_k_m",
            2048,
            2,
            "disabled",
            "b10054",
            self.paths.versions / "b10054-amd64",
            self.paths.models / "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        )
        self.paths.suspended.parent.mkdir(parents=True)
        self.paths.suspended.write_text("{}\n", encoding="utf-8")
        with (
            mock.patch.object(self.manager, "_run"),
            mock.patch.object(
                self.manager, "_stop_service", return_value=False
            ) as stop_service,
        ):
            self.manager._apply_service_state(
                configuration,
                [],
                verify_health=False,
                restart_required=False,
            )
        stop_service.assert_called_once_with(disable=False)

    def test_stop_service_verifies_disabled_post_condition(self) -> None:
        with (
            mock.patch.object(
                self.manager, "_service_active", side_effect=[True, False]
            ),
            mock.patch.object(
                self.manager,
                "_service_enabled",
                side_effect=["enabled", "disabled"],
            ),
            mock.patch.object(self.manager, "_run") as run,
        ):
            changed = self.manager._stop_service(disable=True)
        self.assertTrue(changed)
        run.assert_called_once_with(
            ["systemctl", "disable", "--now", "llama-server.service"],
            check=False,
        )

    def test_stop_service_fails_when_service_remains_active(self) -> None:
        with (
            mock.patch.object(
                self.manager, "_service_active", side_effect=[True, True]
            ),
            mock.patch.object(
                self.manager,
                "_service_enabled",
                side_effect=["enabled", "disabled"],
            ),
            mock.patch.object(self.manager, "_run"),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._stop_service(disable=True)
        self.assertEqual(raised.exception.code, "SERVICE_STOP_FAILED")

    def test_stop_service_fails_when_service_remains_enabled(self) -> None:
        with (
            mock.patch.object(
                self.manager, "_service_active", side_effect=[True, False]
            ),
            mock.patch.object(
                self.manager,
                "_service_enabled",
                side_effect=["enabled", "enabled"],
            ),
            mock.patch.object(self.manager, "_run"),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._stop_service(disable=True)
        self.assertEqual(raised.exception.code, "SERVICE_STOP_FAILED")

    def test_resume_is_unchanged_when_service_is_already_active(self) -> None:
        marker = {"version": self.manager.version}
        config = {
            "runtime_release": "b10054",
        }
        with (
            mock.patch.object(self.manager, "load_marker", return_value=marker),
            mock.patch.object(self.manager, "verify_checks", return_value=[]),
            mock.patch.object(self.manager, "_existing_config", return_value=config),
            mock.patch.object(self.manager, "_service_active", return_value=True),
            mock.patch.object(self.manager, "_health", return_value=True),
            mock.patch.object(self.manager, "_run") as run,
        ):
            changed, _version = self.manager._execute_resume()
        self.assertEqual(changed, [])
        run.assert_not_called()

    def test_blocked_audit_event_is_denied(self) -> None:
        with mock.patch("llama.management.os.fchown"):
            self.manager._append_audit(
                self.invocation(),
                event_id=str(uuid.uuid4()),
                result_status="blocked",
                changed=False,
                receipt_digest=None,
                instance_id=None,
            )
        event = json.loads(self.paths.audit.read_text(encoding="utf-8"))
        self.assertEqual(event["decision"], "denied")
        self.assertEqual(event["result"], "blocked")

    def test_legacy_validation_checks_model_digest_and_unit_asset(self) -> None:
        model_path = self.paths.models / "legacy.gguf"
        model_path.parent.mkdir(parents=True)
        model_path.write_bytes(b"approved model")
        self.paths.versions.mkdir(parents=True)
        self.paths.current.symlink_to(self.paths.versions / "b10054-amd64")
        self.paths.configuration_root.mkdir(parents=True)
        config = {
            "schema_version": 1,
            "port": 8080,
            "model_id": "legacy-model",
            "model_path": str(model_path),
            "context_size": 512,
            "threads": 1,
            "runtime_release": "b10054",
            "runtime_dir": str(self.paths.current),
        }
        self.paths.config.write_text(json.dumps(config), encoding="utf-8")
        self.manager.model_catalog = {
            "schema_version": 1,
            "models": [
                {
                    "id": "legacy-model",
                    "name": "Legacy",
                    "filename": "legacy.gguf",
                    "url": "https://huggingface.co/example/legacy.gguf",
                    "sha256": hashlib.sha256(b"approved model").hexdigest(),
                    "size_bytes": len(b"approved model"),
                    "license": "Apache-2.0",
                    "context_size": 512,
                }
            ],
        }

        def fixture_digest(path: Path) -> str:
            if path == self.paths.unit:
                return LEGACY_UNIT_SHA256
            return hashlib.sha256(path.read_bytes()).hexdigest()

        with (
            mock.patch.object(self.manager, "_legacy_marker", return_value=True),
            mock.patch.object(self.manager, "_account_valid", return_value=True),
            mock.patch.object(
                self.manager, "_legacy_directories_valid", return_value=True
            ),
            mock.patch.object(self.manager, "_root_file", return_value=True),
            mock.patch.object(self.manager, "_runtime_valid", return_value=True),
            mock.patch.object(self.manager, "_file_matches", return_value=True) as matches,
            mock.patch(
                "llama.management.sha256_file", side_effect=fixture_digest
            ) as digest,
        ):
            self.assertTrue(self.manager._legacy_installation_valid())
            model_path.write_bytes(b"tampered model")
            self.assertFalse(self.manager._legacy_installation_valid())
        digest.assert_any_call(self.paths.unit)
        self.assertGreaterEqual(matches.call_count, 2)

    def test_legacy_uninstall_adopts_before_retaining_state(self) -> None:
        self.paths.state_root.mkdir(parents=True)
        marker = {"version": self.manager.version}
        with (
            mock.patch.object(self.manager, "load_marker", side_effect=[None, marker]),
            mock.patch.object(
                self.manager, "_legacy_installation_valid", return_value=True
            ),
            mock.patch.object(self.manager, "_write_marker") as write_marker,
            mock.patch.object(self.manager, "_run"),
            mock.patch("llama.management.os.fchown"),
            mock.patch("llama.management.os.chown"),
        ):
            changed, version = self.manager._execute_uninstall(
                self.invocation("uninstall")
            )
        write_marker.assert_called_once()
        self.assertEqual(version, self.manager.version)
        self.assertTrue(self.paths.retained.exists())
        self.assertIn(str(self.paths.retained), changed)

    def test_protected_audit_log_does_not_block_clean_reinstall(self) -> None:
        self.paths.log_root.mkdir(parents=True)
        with (
            mock.patch.object(self.manager, "load_marker", return_value=None),
            mock.patch.object(self.manager, "_transaction_instance", return_value=None),
            mock.patch.object(
                self.manager, "_legacy_installation_valid", return_value=False
            ),
            mock.patch.object(self.manager, "_log_ownership_valid", return_value=True),
            mock.patch("llama.management.pwd.getpwnam", side_effect=KeyError),
        ):
            marker, pending = self.manager._collision_preflight()
        self.assertIsNone(marker)
        self.assertEqual(str(uuid.UUID(pending)), pending)

    def test_unmarked_audit_log_blocks_clean_reinstall(self) -> None:
        self.paths.log_root.mkdir(parents=True)
        with (
            mock.patch.object(self.manager, "load_marker", return_value=None),
            mock.patch.object(self.manager, "_transaction_instance", return_value=None),
            mock.patch.object(
                self.manager, "_legacy_installation_valid", return_value=False
            ),
            mock.patch.object(self.manager, "_log_ownership_valid", return_value=False),
            mock.patch("llama.management.pwd.getpwnam", side_effect=KeyError),
        ):
            with self.assertRaises(ManagementError) as raised:
                self.manager._collision_preflight()
        self.assertEqual(raised.exception.code, "UNSAFE_COLLISION")


if __name__ == "__main__":
    unittest.main()
